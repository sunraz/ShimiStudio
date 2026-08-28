#!/usr/bin/env python3
"""
ShimiStudio Worker v2
---------------------
Production-quality Python daemon for ShimiStudio video and image generation worker.
Runs on a PC with NVIDIA GPU. Event-driven worker that uses long-poll + webhook push (NOT 10-second polling).
Claims jobs from Base44 'shimiStudioAPI',
executes them via local/remote ComfyUI, uploads output to 0x0.st / catbox.moe,
and reports status/progress back to Base44.

Supported job types:
- text_to_image (Flux.1)
- image_to_video (Wan 2.2 I2V)
- text_to_video (Wan 2.2 T2V or LTX-Video)
- face_id (IP-Adapter FaceID)
- face_swap (ReActor Face Swap)
- tts_lipsync (TTS + Lip Sync)
- camera_capture (Phone camera frame processing)
- full_pipeline (Face ID -> Gen -> Video -> Face Swap)
"""

import os
import sys
import time
import json
import socket
import random
import logging
import argparse
import base64
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import requests

# ==========================================
# CONFIGURATION
# ==========================================
COMFYUI_URL = 'http://localhost:8188'
BASE44_API_URL = 'https://solas-6a095a77.base44.app/functions/shimiStudioAPI'
WORKER_ID = f"worker-{socket.gethostname()}-{int(time.time())}"
WAIT_SECONDS = 25  # Long-poll: hold connection up to 25s waiting for new jobs
UPLOAD_TIMEOUT = 120

# Directory paths
ROOT_DIR = Path(__file__).resolve().parent
WORKFLOWS_DIR = ROOT_DIR / "workflows"
OUTPUT_DIR = ROOT_DIR / "output"
TEMP_DIR = ROOT_DIR / "temp"

# Ensure directories exist
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("ShimiStudioWorker")


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging to console."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "[%(asctime)s] [%(levelname)s] %(message)s"
    logging.basicConfig(level=log_level, format=log_format, datefmt="%Y-%m-%d %H:%M:%S")


def download_file(url_or_data: str, dest_dir: Path, filename_prefix: str = "input") -> Path:
    """
    Download a file from an HTTP/HTTPS URL or decode a base64 data URI to a local file.
    Returns path to local file.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)
    if not url_or_data or not isinstance(url_or_data, str):
        raise ValueError("Invalid file URL or data provided for download.")

    url_str = url_or_data.strip()

    # Base64 Data URI handling
    if url_str.startswith("data:"):
        header, encoded = url_str.split(",", 1) if "," in url_str else ("", url_str)
        ext = "png"
        if "image/jpeg" in header or "image/jpg" in header:
            ext = "jpg"
        elif "video/mp4" in header:
            ext = "mp4"
        out_path = dest_dir / f"{filename_prefix}_{int(time.time()*1000)}.{ext}"
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(encoded))
        logger.debug(f"Decoded base64 data to {out_path.name}")
        return out_path

    # HTTP/HTTPS Download
    if url_str.startswith("http://") or url_str.startswith("https://"):
        ext = url_str.split("?")[0].split(".")[-1].lower()
        if len(ext) > 5 or "/" in ext:
            ext = "png"
        out_path = dest_dir / f"{filename_prefix}_{int(time.time()*1000)}.{ext}"
        logger.debug(f"Downloading from {url_str[:60]}... to {out_path.name}")
        resp = requests.get(url_str, timeout=60, stream=True)
        resp.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        return out_path

    # If already a local file path
    local_p = Path(url_str)
    if local_p.exists():
        return local_p

    raise ValueError(f"Unable to process input source: {url_str[:80]}")


def upload_file_to_comfyui(comfyui_url: str, file_path: Path) -> str:
    """
    Upload a local image or video file to ComfyUI input directory via POST /upload/image.
    Returns filename as registered inside ComfyUI.
    """
    url = f"{comfyui_url.rstrip('/')}/upload/image"
    logger.debug(f"Uploading {file_path.name} to ComfyUI input folder at {url}...")
    with open(file_path, "rb") as f:
        files = {"image": (file_path.name, f)}
        data = {"overwrite": "true"}
        resp = requests.post(url, files=files, data=data, timeout=30)
        resp.raise_for_status()
        res = resp.json()
        filename = res.get("name", file_path.name)
        logger.debug(f"ComfyUI uploaded input image name: {filename}")
        return filename


def upload_to_0x0(file_path: Path, timeout: int = 120) -> str:
    """Upload output file to 0x0.st primary storage."""
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f)}
        headers = {"User-Agent": "ShimiStudio-Worker/2.0"}
        resp = requests.post("https://0x0.st", files=files, headers=headers, timeout=timeout)
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            return url
        raise RuntimeError(f"Invalid URL response from 0x0.st: {url}")


def upload_to_catbox(file_path: Path, timeout: int = 120) -> str:
    """Upload output file to catbox.moe fallback storage."""
    with open(file_path, "rb") as f:
        files = {
            "reqType": (None, "fileupload"),
            "fileToUpload": (file_path.name, f)
        }
        resp = requests.post("https://catbox.moe/user/api.php", files=files, timeout=timeout)
        resp.raise_for_status()
        url = resp.text.strip()
        if url.startswith("http"):
            return url
        raise RuntimeError(f"Invalid URL response from catbox.moe: {url}")


def upload_output_file(file_path: Path, timeout: int = 120) -> str:
    """
    Upload output video/image file with 0x0.st as primary, catbox.moe as fallback.
    Retries each service once on failure.
    """
    logger.info(f"📤 Uploading result file {file_path.name} ({file_path.stat().st_size / 1024 / 1024:.2f} MB)...")

    # Primary: 0x0.st (2 attempts = 1 retry)
    for attempt in range(1, 3):
        try:
            logger.debug(f"Attempting upload to 0x0.st (attempt {attempt}/2)...")
            url = upload_to_0x0(file_path, timeout=timeout)
            logger.info(f"✅ Successfully uploaded to 0x0.st: {url}")
            return url
        except Exception as e:
            logger.warning(f"⚠️ 0x0.st upload attempt {attempt} failed: {e}")
            time.sleep(2)

    # Fallback: catbox.moe (2 attempts = 1 retry)
    logger.info("📦 Falling back to catbox.moe...")
    for attempt in range(1, 3):
        try:
            logger.debug(f"Attempting upload to catbox.moe (attempt {attempt}/2)...")
            url = upload_to_catbox(file_path, timeout=timeout)
            logger.info(f"✅ Successfully uploaded to catbox.moe: {url}")
            return url
        except Exception as e:
            logger.warning(f"⚠️ catbox.moe upload attempt {attempt} failed: {e}")
            time.sleep(2)

    raise RuntimeError("Failed to upload output file after all retries on 0x0.st and catbox.moe")


def claim_job(base44_url: str, worker_id: str, wait_seconds: int = 25) -> Optional[Dict[str, Any]]:
    """
    Long-poll Base44 backend for the next pending render job.
    Holds the connection open for up to 'wait_seconds' seconds.
    Returns instantly when a job appears — no 10-second polling.
    """
    payload = {
        "action": "claim",
        "worker_id": worker_id,
        "wait_seconds": wait_seconds
    }
    try:
        # Timeout = wait_seconds + 5s buffer for network overhead
        resp = requests.post(base44_url, json=payload, timeout=wait_seconds + 10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Error in long-poll claim: {e}")
        return None


def update_job(
    base44_url: str,
    job_id: str,
    status: str,
    progress: Optional[int] = None,
    output_url: Optional[str] = None,
    error_message: Optional[str] = None,
    result_type: Optional[str] = None
) -> None:
    """Update job status and progress on Base44 backend."""
    payload: Dict[str, Any] = {
        "action": "update",
        "job_id": job_id,
        "status": status
    }
    if progress is not None:
        payload["progress"] = progress
    if output_url is not None:
        payload["output_url"] = output_url
    if error_message is not None:
        payload["error_message"] = error_message
    if result_type is not None:
        payload["result_type"] = result_type

    try:
        resp = requests.post(base44_url, json=payload, timeout=20)
        resp.raise_for_status()
        logger.debug(f"Updated job [{job_id}] on Base44: status={status}, progress={progress}")
    except Exception as e:
        logger.error(f"Failed to update job [{job_id}] status on Base44: {e}")


def load_workflow_template(job_type: str, custom_workflow_id: str = "") -> str:
    """Load JSON workflow template string for given job_type or custom_workflow_id."""
    candidates = []
    if custom_workflow_id:
        candidates.append(f"{custom_workflow_id}.json" if not custom_workflow_id.endswith(".json") else custom_workflow_id)

    # Job type mapping
    mapping = {
        "text_to_image": ["text_to_image.json", "flux1_t2i.json"],
        "image_to_video": ["image_to_video.json", "wan22_i2v.json"],
        "text_to_video": ["text_to_video.json", "wan22_t2v.json", "ltx_t2v.json"],
        "face_id": ["face_id.json"],
        "face_swap": ["face_swap.json"],
        "tts_lipsync": ["tts_lipsync.json"],
        "camera_capture": ["camera_capture.json"],
        "full_pipeline": ["full_pipeline.json"],
    }

    if job_type in mapping:
        candidates.extend(mapping[job_type])
    else:
        candidates.append(f"{job_type}.json")

    for filename in candidates:
        filepath = WORKFLOWS_DIR / filename
        if filepath.exists():
            logger.info(f"Loaded workflow template: {filepath.name}")
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

    raise FileNotFoundError(f"No workflow template found for job_type '{job_type}' in {WORKFLOWS_DIR}")


def build_workflow_json(
    template_str: str,
    replacements: Dict[str, Any]
) -> Dict[str, Any]:
    """Substitute placeholders into JSON workflow template and return dict."""
    formatted_str = template_str

    for key, val in replacements.items():
        placeholder = f"__{key.upper()}__"
        if isinstance(val, (int, float, bool)):
            # Replace double-quoted placeholder for native JSON numbers
            formatted_str = formatted_str.replace(f'"{placeholder}"', str(val))
            formatted_str = formatted_str.replace(placeholder, str(val))
        else:
            escaped_str = json.dumps(str(val))[1:-1]
            formatted_str = formatted_str.replace(placeholder, escaped_str)

    # Parse JSON
    try:
        wf_dict = json.loads(formatted_str)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse formatted workflow JSON: {e}")
        raise

    # Convert numeric string inputs inside nodes if needed
    for node_id, node_data in wf_dict.items():
        if isinstance(node_data, dict) and "inputs" in node_data:
            inputs = node_data["inputs"]
            for ik, iv in list(inputs.items()):
                if ik in ["width", "height", "steps", "seed", "frames", "length", "fps", "batch_size"]:
                    try:
                        if isinstance(iv, str) and iv.isdigit():
                            inputs[ik] = int(iv)
                    except Exception:
                        pass
                elif ik in ["cfg", "denoise", "weight"]:
                    try:
                        if isinstance(iv, str):
                            inputs[ik] = float(iv)
                    except Exception:
                        pass

    return wf_dict


def submit_workflow_to_comfyui(comfyui_url: str, workflow_dict: Dict[str, Any], client_id: str = "") -> str:
    """Submit prompt workflow JSON to ComfyUI POST /prompt endpoint."""
    url = f"{comfyui_url.rstrip('/')}/prompt"
    payload = {"prompt": workflow_dict}
    if client_id:
        payload["client_id"] = client_id

    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise ValueError(f"ComfyUI response missing prompt_id: {data}")
    logger.info(f"🚀 Submitted job to ComfyUI (prompt_id: {prompt_id})")
    return prompt_id


def poll_comfyui_history(
    comfyui_url: str,
    prompt_id: str,
    job_id: str,
    base44_url: str,
    max_wait_seconds: int = 1200
) -> Dict[str, Any]:
    """
    Poll ComfyUI GET /history/{prompt_id} until execution is complete.
    Updates progress to Base44 periodically during rendering.
    """
    history_url = f"{comfyui_url.rstrip('/')}/history/{prompt_id}"
    start_time = time.time()
    last_progress_update = 0

    logger.info(f"⏳ Waiting for ComfyUI render completion (prompt_id: {prompt_id})...")

    while time.time() - start_time < max_wait_seconds:
        elapsed = int(time.time() - start_time)

        # Update progress percentage on Base44 during long renders
        current_progress = min(85, 35 + int((elapsed / max_wait_seconds) * 50))
        if current_progress - last_progress_update >= 10:
            update_job(base44_url, job_id, status="processing", progress=current_progress)
            last_progress_update = current_progress

        try:
            resp = requests.get(history_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if prompt_id in data:
                    prompt_history = data[prompt_id]
                    logger.info(f"✅ ComfyUI render finished in {elapsed}s.")
                    return prompt_history
        except requests.RequestException:
            pass

        time.sleep(3)

    raise TimeoutError(f"Render timed out after {max_wait_seconds} seconds.")


def download_comfyui_output(
    comfyui_url: str,
    history_data: Dict[str, Any],
    job_id: str
) -> Path:
    """Download resulting image or video file from ComfyUI GET /view endpoint."""
    outputs = history_data.get("outputs", {})
    output_file_info = None

    # Search outputs for video, gif, or image files
    for node_id, node_out in outputs.items():
        if not isinstance(node_out, dict):
            continue
        for key in ["gifs", "videos", "images"]:
            if key in node_out and isinstance(node_out[key], list) and len(node_out[key]) > 0:
                output_file_info = node_out[key][0]
                break
        if output_file_info:
            break

    if not output_file_info:
        raise RuntimeError(f"No output media files found in ComfyUI history: {outputs}")

    filename = output_file_info.get("filename")
    subfolder = output_file_info.get("subfolder", "")
    file_type = output_file_info.get("type", "output")

    view_url = f"{comfyui_url.rstrip('/')}/view"
    params = {"filename": filename, "subfolder": subfolder, "type": file_type}

    logger.debug(f"Downloading output file '{filename}' from ComfyUI view endpoint...")
    resp = requests.get(view_url, params=params, timeout=60, stream=True)
    resp.raise_for_status()

    local_path = OUTPUT_DIR / f"{job_id}_{filename}"
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)

    logger.info(f"💾 Downloaded output file to {local_path.name} ({local_path.stat().st_size / 1024 / 1024:.2f} MB)")
    return local_path


def process_job(
    job: Dict[str, Any],
    comfyui_url: str,
    base44_url: str,
    upload_timeout: int = 120
) -> None:
    """
    Main job processing pipeline:
    1. Update status to 'processing'
    2. Download input assets & upload to ComfyUI
    3. Load workflow JSON & substitute parameters
    4. Submit prompt to ComfyUI & poll /history
    5. Download output media & upload to 0x0.st / catbox.moe
    6. Update status to 'completed' with output_url
    """
    job_id = job.get("id")
    job_type = job.get("job_type", "text_to_video")
    prompt = job.get("prompt", "")
    negative_prompt = job.get("negative_prompt", "")
    parameters = job.get("parameters") or {}
    workflow_id = job.get("workflow_id", "")
    client_id = job.get("client_id", "")

    logger.info(f"==================================================")
    logger.info(f"🎬 Starting Job [{job_id}] — Type: {job_type}")
    logger.info(f"   Prompt: {prompt[:100]}...")
    logger.info(f"==================================================")

    # 1. Update status on Base44
    update_job(base44_url, job_id, status="processing", progress=10)

    downloaded_files: List[Path] = []
    output_file_path: Optional[Path] = None

    try:
        # 2. Handle input media according to job_type
        replacements: Dict[str, Any] = {
            "prompt": prompt,
            "negative_prompt": negative_prompt or "blurry, low quality, distorted, watermark",
            "seed": int(parameters.get("seed") or job.get("seed") or random.randint(1, 2147483647)),
            "width": int(parameters.get("width") or job.get("width") or 832),
            "height": int(parameters.get("height") or job.get("height") or 480),
            "steps": int(parameters.get("steps") or job.get("steps") or 20),
            "cfg": float(parameters.get("cfg") or job.get("cfg") or 3.5),
            "fps": float(parameters.get("fps") or job.get("fps") or 16),
            "frames": int(parameters.get("frames") or parameters.get("length") or job.get("frames") or 81),
            "voice_text": job.get("voice_text", ""),
        }

        # Face ID inputs
        face_images = job.get("face_images") or []
        if isinstance(face_images, str):
            face_images = [face_images]
        face_input = face_images[0] if len(face_images) > 0 else job.get("reference_image")

        if face_input and (job_type in ["face_id", "face_swap", "full_pipeline"]):
            logger.info("Downloading face input image...")
            f_path = download_file(face_input, TEMP_DIR, filename_prefix="face")
            downloaded_files.append(f_path)
            face_comfy_name = upload_file_to_comfyui(comfyui_url, f_path)
            replacements["face_image"] = face_comfy_name

        # Target image for face_swap
        face_swap_target = job.get("face_swap_target")
        if face_swap_target and (job_type in ["face_swap", "full_pipeline"]):
            logger.info("Downloading face swap target image/video...")
            t_path = download_file(face_swap_target, TEMP_DIR, filename_prefix="target")
            downloaded_files.append(t_path)
            target_comfy_name = upload_file_to_comfyui(comfyui_url, t_path)
            replacements["target_image"] = target_comfy_name

        # Reference image for image_to_video / tts_lipsync
        reference_image = job.get("reference_image")
        if reference_image and (job_type in ["image_to_video", "tts_lipsync"]):
            logger.info("Downloading reference image...")
            r_path = download_file(reference_image, TEMP_DIR, filename_prefix="ref")
            downloaded_files.append(r_path)
            ref_comfy_name = upload_file_to_comfyui(comfyui_url, r_path)
            replacements["reference_image"] = ref_comfy_name

        # Camera frames
        camera_frames = job.get("camera_frames")
        if camera_frames and job_type == "camera_capture":
            logger.info("Downloading camera frame...")
            c_input = camera_frames[0] if isinstance(camera_frames, list) else camera_frames
            c_path = download_file(c_input, TEMP_DIR, filename_prefix="camera")
            downloaded_files.append(c_path)
            cam_comfy_name = upload_file_to_comfyui(comfyui_url, c_path)
            replacements["camera_frame"] = cam_comfy_name

        update_job(base44_url, job_id, status="processing", progress=25)

        # 3. Load workflow template & construct JSON
        template_str = load_workflow_template(job_type, custom_workflow_id=workflow_id)
        workflow_dict = build_workflow_json(template_str, replacements)

        # 4. Submit to ComfyUI & poll history
        update_job(base44_url, job_id, status="processing", progress=35)
        prompt_id = submit_workflow_to_comfyui(comfyui_url, workflow_dict, client_id=client_id)
        history_data = poll_comfyui_history(comfyui_url, prompt_id, job_id, base44_url)

        # 5. Download output file from ComfyUI
        update_job(base44_url, job_id, status="processing", progress=88)
        output_file_path = download_comfyui_output(comfyui_url, history_data, job_id)

        # 6. Upload output file to public storage
        update_job(base44_url, job_id, status="processing", progress=92)
        output_url = upload_output_file(output_file_path, timeout=upload_timeout)

        # Determine result_type (video or image)
        ext = output_file_path.suffix.lower()
        result_type = "video" if ext in [".mp4", ".webm", ".avi", ".mov"] else "image"

        # 7. Update status to completed on Base44
        update_job(
            base44_url,
            job_id,
            status="completed",
            progress=100,
            output_url=output_url,
            result_type=result_type
        )
        logger.info(f"🎉 Job [{job_id}] successfully completed -> {output_url}")

    except Exception as e:
        err_msg = str(e)
        logger.error(f"❌ Job [{job_id}] failed: {err_msg}")
        logger.error(traceback.format_exc())
        update_job(base44_url, job_id, status="failed", error_message=err_msg)

    finally:
        # Cleanup temporary downloaded/generated files
        for f_path in downloaded_files:
            try:
                if f_path.exists():
                    f_path.unlink()
            except Exception:
                pass

        if output_file_path and output_file_path.exists():
            try:
                output_file_path.unlink()
                logger.debug(f"Cleaned up output file {output_file_path.name}")
            except Exception:
                pass




# ==========================================
# WEBHOOK PUSH NOTIFICATION SERVER
# ==========================================
# Instead of polling every 10 seconds, the worker runs a tiny HTTP server.
# When Base44 creates a new job, it POSTs to this server → worker wakes instantly.
# The long-poll is the fallback — webhook is the fast path.

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class WebhookHandler(BaseHTTPRequestHandler):
    """Receives push notifications from Base44 when new jobs are created."""
    job_available = threading.Event()
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length else '{}'
        try:
            data = json.loads(body)
            event = data.get('event', 'unknown')
            if event == 'new_job':
                logger.info(f"🔔 PUSH: New job notification received — {data.get('job_type', '?')}")
                WebhookHandler.job_available.set()
            elif event == 'manual_notify':
                logger.info(f"🔔 PUSH: Manual notification — {data.get('message', '?')}")
                WebhookHandler.job_available.set()
        except Exception:
            pass
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')
    
    def log_message(self, format, *args):
        pass  # Suppress default HTTP logging

def start_webhook_server(port: int):
    """Start the webhook push notification server in a background thread."""
    server = HTTPServer(('0.0.0.0', port), WebhookHandler)
    logger.info(f"🔔 Webhook push server listening on port {port}")
    server.serve_forever()

def register_worker_webhook(base44_url: str, worker_id: str, port: int):
    """Register this worker's webhook URL with Base44 for push notifications."""
    # Get public IP (the PC's local IP on the network)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "localhost"
    
    webhook_url = f"http://{local_ip}:{port}"
    payload = {
        "action": "register_worker",
        "webhook_url": webhook_url,
        "worker_id": worker_id
    }
    try:
        resp = requests.post(base44_url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info(f"✅ Registered webhook with Base44: {webhook_url}")
        else:
            logger.warning(f"⚠️ Webhook registration returned {resp.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ Could not register webhook: {e}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="ShimiStudio Worker v2 — PC NVIDIA GPU Rendering Worker"
    )
    parser.add_argument(
        "--comfyui-url",
        type=str,
        default=COMFYUI_URL,
        help=f"ComfyUI API URL (default: {COMFYUI_URL})"
    )
    parser.add_argument(
        "--base44-url",
        type=str,
        default=BASE44_API_URL,
        help=f"Base44 backend function URL (default: {BASE44_API_URL})"
    )
    parser.add_argument(
        "--worker-id",
        type=str,
        default=WORKER_ID,
        help=f"Custom Worker ID (default: {WORKER_ID})"
    )
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=WAIT_SECONDS,
        help=f"Long-poll wait time in seconds (default: {WAIT_SECONDS})"
    )
    parser.add_argument(
        "--webhook-port",
        type=int,
        default=WEBHOOK_PORT,
        help=f"Webhook push server port (default: {WEBHOOK_PORT})"
    )
    parser.add_argument(
        "--upload-timeout",
        type=int,
        default=UPLOAD_TIMEOUT,
        help=f"Upload timeout in seconds (default: {UPLOAD_TIMEOUT})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output"
    )
    return parser.parse_args()


def main() -> None:
    """Main worker entry point."""
    args = parse_args()
    setup_logging(verbose=args.verbose)

    comfyui_url = args.comfyui_url
    base44_url = args.base44_url
    worker_id = args.worker_id
    wait_seconds = args.wait_seconds
    upload_timeout = args.upload_timeout
    webhook_port = args.webhook_port

    # Start webhook push server in background thread
    webhook_thread = threading.Thread(
        target=start_webhook_server,
        args=(webhook_port,),
        daemon=True
    )
    webhook_thread.start()
    time.sleep(0.5)  # Let server start

    # Register webhook URL with Base44 for instant push notifications
    register_worker_webhook(base44_url, worker_id, webhook_port)

    logger.info("==================================================")
    logger.info("🎬 ShimiStudio Worker v2 Started (Long-Poll + Push)")
    logger.info(f"   Worker ID     : {worker_id}")
    logger.info(f"   ComfyUI URL   : {comfyui_url}")
    logger.info(f"   Base44 API    : {base44_url}")
    logger.info(f"   Long-Poll Wait: {wait_seconds}s (no 10s polling!)")
    logger.info(f"   Webhook Port  : {webhook_port} (push notifications)")
    logger.info("==================================================")

    while True:
        try:
            # Clear the push notification flag before long-polling
            WebhookHandler.job_available.clear()

            # Long-poll: holds connection up to 'wait_seconds' seconds.
            # Returns instantly when a job appears.
            # If webhook push arrives during long-poll, we still wait for
            # the response (job will be in the response).
            job_data = claim_job(base44_url, worker_id, wait_seconds)

            if job_data and job_data.get("status") == "claimed" and "job" in job_data:
                job = job_data["job"]
                process_job(
                    job=job,
                    comfyui_url=comfyui_url,
                    base44_url=base44_url,
                    upload_timeout=upload_timeout
                )
            elif job_data and job_data.get("status") == "no_jobs":
                logger.debug(f"No jobs — long-poll timed out after {job_data.get('waited_seconds', '?')}s")
                # Check if a webhook push arrived during the long-poll
                if WebhookHandler.job_available.is_set():
                    logger.info("🔔 Webhook push received — re-checking for jobs immediately")
                    continue  # Skip sleep, immediately long-poll again
            else:
                logger.debug("Unexpected response from claim endpoint")
        except KeyboardInterrupt:
            logger.info("\n🛑 Worker shutdown requested. Exiting gracefully.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error in worker loop: {e}")
            logger.error(traceback.format_exc())
            time.sleep(5)  # Brief pause on error before retrying

        # No sleep here! The long-poll itself handles the waiting.
        # If we get here, we immediately start another long-poll.
        # The only "polling" is the long-poll — no 10-second sleep loop.


if __name__ == "__main__":
    main()
