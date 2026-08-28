"""
ShimiStudio v2.0 — ComfyUI Client Module
Complete ComfyUI REST API client and file output management.
"""

import os
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import requests

try:
    from config import COMFYUI_URL, OUTPUT_DIR
except ImportError:
    COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
    OUTPUT_DIR = Path(__file__).resolve().parent / "output"

logger = logging.getLogger("ShimiStudio.ComfyUIClient")


class ComfyUIClient:
    """
    Complete ComfyUI API Client.
    Connects to a ComfyUI backend over HTTP.
    """

    def __init__(self, base_url: str = 'http://127.0.0.1:8188'):
        url = base_url if base_url else COMFYUI_URL
        self.base_url = url.rstrip('/')

    def get_system_stats(self) -> dict:
        """GET /system_stats — Returns system and GPU hardware stats."""
        url = f"{self.base_url}/system_stats"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_queue(self) -> dict:
        """GET /queue — Returns running and pending queue tasks."""
        url = f"{self.base_url}/queue"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def queue_prompt(self, workflow: dict, client_id: Optional[str] = None) -> dict:
        """
        POST /prompt — Queues a prompt workflow dict for execution.
        Payload format: {'prompt': workflow, 'client_id': client_id}
        """
        url = f"{self.base_url}/prompt"
        cid = client_id if client_id else str(uuid.uuid4())
        payload = {
            "prompt": workflow,
            "client_id": cid
        }
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_history(self, prompt_id: str) -> dict:
        """GET /history/{prompt_id} — Returns history record for a prompt ID."""
        url = f"{self.base_url}/history/{prompt_id}"
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_image(self, filename: str, subfolder: str = '', folder_type: str = 'output') -> bytes:
        """
        GET /view?filename=X&subfolder=Y&type=Z — Returns raw image/video binary content.
        """
        url = f"{self.base_url}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        return resp.content

    def upload_image(self, filepath: str) -> dict:
        """
        POST /upload/image — Uploads an image or media file via multipart form.
        """
        path = Path(filepath)
        if not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        url = f"{self.base_url}/upload/image"
        with open(path, "rb") as f:
            files = {"image": (path.name, f)}
            data = {"overwrite": "true"}
            resp = requests.post(url, files=files, data=data, timeout=60)
            resp.raise_for_status()
            return resp.json()

    def wait_for_completion(self, prompt_id: str, timeout: int = 300, poll_interval: float = 2.0) -> dict:
        """
        Polls GET /history/{prompt_id} until the job completes or times out.
        Returns the prompt history dict for prompt_id.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                history_data = self.get_history(prompt_id)
                if prompt_id in history_data:
                    prompt_history = history_data[prompt_id]
                    status_info = prompt_history.get("status", {})

                    if status_info.get("completed", False) or status_info.get("status_str") == "success":
                        return prompt_history

                    if status_info.get("status_str") == "error":
                        messages = status_info.get("messages", [])
                        raise RuntimeError(f"ComfyUI prompt execution failed: {messages}")

                    if "outputs" in prompt_history and prompt_history["outputs"]:
                        return prompt_history
            except requests.RequestException:
                pass  # Ignore network glitches while polling

            time.sleep(poll_interval)

        raise TimeoutError(f"Prompt {prompt_id} execution timed out after {timeout} seconds")

    def interrupt(self) -> dict:
        """POST /interrupt — Cancels current execution in ComfyUI."""
        url = f"{self.base_url}/interrupt"
        resp = requests.post(url, timeout=10)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status": "interrupted"}

    def is_running(self) -> bool:
        """Checks if ComfyUI instance is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/system_stats", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False


# ============================================================
# Helper Functions
# ============================================================

def save_image_from_comfyui(
    client: ComfyUIClient,
    filename: str,
    subfolder: str = '',
    output_dir: Optional[Union[str, Path]] = None
) -> str:
    """
    Downloads image from ComfyUI and saves it to output_dir.
    Returns string filepath.
    """
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    img_bytes = client.get_image(filename=filename, subfolder=subfolder, folder_type='output')
    file_path = out_dir / filename
    with open(file_path, "wb") as f:
        f.write(img_bytes)
    return str(file_path.resolve())


def save_video_from_comfyui(
    client: ComfyUIClient,
    filename: str,
    subfolder: str = '',
    output_dir: Optional[Union[str, Path]] = None
) -> str:
    """
    Downloads video from ComfyUI and saves it to output_dir.
    Returns string filepath.
    """
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    vid_bytes = client.get_image(filename=filename, subfolder=subfolder, folder_type='output')
    file_path = out_dir / filename
    with open(file_path, "wb") as f:
        f.write(vid_bytes)
    return str(file_path.resolve())


def submit_and_wait(
    client: Union[ComfyUIClient, str],
    workflow: dict,
    output_dir: Optional[Union[str, Path]] = None,
    timeout: int = 600
) -> dict:
    """
    Submits workflow, waits for completion, saves outputs, and returns dict:
    {'success': bool, 'outputs': [filepaths], 'prompt_id': prompt_id}
    """
    if isinstance(client, str):
        client_inst = ComfyUIClient(client)
    else:
        client_inst = client

    prompt_id = None
    try:
        response = client_inst.queue_prompt(workflow)
        prompt_id = response.get("prompt_id")
        if not prompt_id:
            return {
                "success": False,
                "outputs": [],
                "error": f"No prompt_id returned in queue response: {response}",
                "prompt_id": None
            }

        history = client_inst.wait_for_completion(prompt_id, timeout=timeout)
        output_paths = []
        outputs_dict = history.get("outputs", {})

        for node_id, node_output in outputs_dict.items():
            if not isinstance(node_output, dict):
                continue
            for key, items in node_output.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and "filename" in item:
                            fn = item["filename"]
                            sub = item.get("subfolder", "")
                            ext = Path(fn).suffix.lower()
                            if ext in [".mp4", ".webm", ".avi", ".mov", ".mkv", ".gif", ".webp"]:
                                saved_path = save_video_from_comfyui(client_inst, fn, sub, output_dir)
                            else:
                                saved_path = save_image_from_comfyui(client_inst, fn, sub, output_dir)
                            if saved_path not in output_paths:
                                output_paths.append(saved_path)

        return {
            "success": True,
            "outputs": output_paths,
            "prompt_id": prompt_id
        }
    except Exception as e:
        logger.error(f"Error executing prompt {prompt_id}: {e}")
        return {
            "success": False,
            "outputs": [],
            "error": str(e),
            "prompt_id": prompt_id
        }


if __name__ == "__main__":
    c = ComfyUIClient()
    print("=" * 60)
    print("  ShimiStudio ComfyUI Client Test")
    print("=" * 60)
    running = c.is_running()
    print(f"ComfyUI server running: {'✅ Yes' if running else '❌ No (http://127.0.0.1:8188)'}")
    if running:
        try:
            stats = c.get_system_stats()
            print("System stats fetched successfully.")
            queue = c.get_queue()
            print("Queue status fetched successfully.")
        except Exception as err:
            print("Error during API query:", err)
    print("=" * 60)
