import requests, time, json, os, sys, subprocess, random, base64, traceback, re, shutil

cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
with open(cfg_path, encoding="utf-8-sig") as f:
    cfg = json.load(f)

TOKEN = cfg["token"]
NAME = cfg["name"]
SERVER = cfg.get("server", "")
API = cfg["apiBase"].rstrip("/")
COMFYUI_URL = cfg.get("comfyui_url", "http://127.0.0.1:8188")
COMFYUI_PATH = cfg.get("comfyui_path", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ComfyUI"))
WAN = cfg.get("wan") or {}
WAN_MODEL = WAN.get("model", "Wan2.2-TI2V-5B-Q4_K_M.gguf")
WAN_ENCODER = WAN.get("text_encoder", "umt5_xxl_fp8_e4m3fn_scaled.safetensors")
WAN_VAE = WAN.get("vae", "Wan2.2_VAE.safetensors")
DEFAULT_ENGINE = (cfg.get("default_engine") or "").lower()

def _mm_dir(sub):
    return os.path.join(COMFYUI_PATH, "models", sub)

def wan22_ready():
    """מנוע Wan 2.2 זמין: קבצי המודל קיימים והצומת UnetLoaderGGUF נטענה."""
    checks = [
        os.path.join(_mm_dir("diffusion_models"), WAN_MODEL),
        os.path.join(_mm_dir("text_encoders"), WAN_ENCODER),
        os.path.join(_mm_dir("vae"), WAN_VAE),
    ]
    missing = [os.path.basename(c) for c in checks if not (os.path.exists(c) and os.path.getsize(c) > 1e6)]
    if missing:
        return False, "missing models: " + ", ".join(missing)
    if 'UnetLoaderGGUF' not in AVAILABLE_NODES:
        return False, "UnetLoaderGGUF node not loaded (ComfyUI-GGUF not installed)"
    if 'VHS_VideoCombine' not in AVAILABLE_NODES:
        return False, "VHS_VideoCombine not loaded"
    return True, "ok"
IS_MAC = sys.platform == "darwin"
VENV_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
AVAILABLE_NODES = set()

def save_image(url, path):
    if url.startswith('data:image'):
        header, data = url.split(',', 1)
        img_data = base64.b64decode(data)
        with open(path, 'wb') as f:
            f.write(img_data)
    else:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)

def post(fn, data, timeout=120):
    try:
        r = requests.post(f"{API}/functions/{fn}", json=data, timeout=timeout)
        if r.status_code >= 400:
            try:
                err = r.json()
                return {"error": err.get("error", f"HTTP {r.status_code}")}
            except:
                return {"error": f"HTTP {r.status_code}"}
        return r.json()
    except Exception as e:
        print(f"  err: {e}")
        return {"error": str(e)}

def comfyui_ready():
    try:
        r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return r.status_code == 200
    except:
        return False

def fetch_available_nodes():
    global AVAILABLE_NODES
    try:
        r = requests.get(f"{COMFYUI_URL}/object_info", timeout=15)
        if r.status_code == 200:
            AVAILABLE_NODES = set(r.json().keys())
            print(f"  ComfyUI nodes: {len(AVAILABLE_NODES)} | IPAdapter={('IPAdapterApply' in AVAILABLE_NODES)} ReActor={('ReActorFaceSwap' in AVAILABLE_NODES)} AnimateDiff={('ADE_AnimateDiffLoaderGen1' in AVAILABLE_NODES)} VHS={('VHS_VideoCombine' in AVAILABLE_NODES)}")
        else:
            print(f"  /object_info HTTP {r.status_code} — custom-node workflows disabled")
    except Exception as e:
        print(f"  /object_info failed: {e} — custom-node workflows disabled")

def start_comfyui():
    if comfyui_ready():
        print("  ComfyUI already running")
        return True
    main_py = os.path.join(COMFYUI_PATH, "main.py")
    if not os.path.exists(main_py):
        print(f"  ComfyUI not found at {COMFYUI_PATH}")
        return False
    # Check for checkpoint
    ckpt_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    has_ckpt = False
    if os.path.isdir(ckpt_dir):
        for f in os.listdir(ckpt_dir):
            if f.lower().endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
                has_ckpt = True; break
    if not has_ckpt:
        print("  WARNING: No checkpoint found in models/checkpoints/")
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comfyui.log")

    def try_start(extra_args=None):
        args = [VENV_PY, main_py, "--listen", "127.0.0.1", "--port", "8188"]
        if extra_args:
            args.extend(extra_args)
        # Detect CUDA — if not available, run ComfyUI in CPU mode
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            if not has_cuda and not has_mps:
                print("  No GPU backend (CUDA/MPS) — starting ComfyUI in CPU mode (slower)")
                args.append("--cpu")
            elif has_mps and not has_cuda:
                print("  Apple Silicon MPS detected — ComfyUI will use Metal acceleration")
                args.append("--force-fp16")
        except ImportError:
            print("  PyTorch not importable — starting ComfyUI in CPU mode")
            args.append("--cpu")
        log_file = open(log_path, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(args, cwd=COMFYUI_PATH, stdout=log_file, stderr=subprocess.STDOUT)
        for i in range(90):
            time.sleep(2)
            if comfyui_ready():
                return True
            if proc.poll() is not None:
                log_file.flush()
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        print("  --- Last 30 lines of comfyui.log ---")
                        for line in lines[-30:]:
                            print(f"  {line.rstrip()}")
                        print("  --- End of log ---")
                except: pass
                return False
            if i % 15 == 0 and i > 0:
                log_file.flush()
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        if lines:
                            print(f"  Waiting for ComfyUI... ({i*2}s) - {lines[-1].rstrip()[:80]}")
                        else:
                            print(f"  Waiting for ComfyUI... ({i*2}s) - no output yet")
                except: pass
        log_file.flush()
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                print("  --- Last 30 lines of comfyui.log ---")
                for line in lines[-30:]:
                    print(f"  {line.rstrip()}")
                print("  --- End of log ---")
        except: pass
        return False

    print("  Starting ComfyUI (with custom nodes)...")
    if try_start():
        print("  ComfyUI started")
        return True
    print("  ComfyUI failed with custom nodes. Retrying with --disable-all-custom-nodes...")
    if try_start(["--disable-all-custom-nodes"]):
        print("  ComfyUI started (custom nodes disabled - IP-Adapter/ReActor unavailable)")
        return True
    print("  ComfyUI failed to start after retries")
    return False

def queue_prompt(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow, "client_id": "shimi"}, timeout=30)
    if r.status_code >= 400:
        err_details = ""
        try:
            err_data = r.json()
            print("  ComfyUI error details:")
            if "error" in err_data:
                err_details = json.dumps(err_data['error'])[:400]
                print(f"    error: {json.dumps(err_data['error'], indent=2)[:600]}")
            if "node_errors" in err_data:
                node_errs = []
                for nid, nerr in err_data["node_errors"].items():
                    cls = nerr.get("class_type", "?")
                    errs = nerr.get("errors", nerr)
                    ne_str = f"Node {nid} ({cls}): {json.dumps(errs)[:300]}"
                    node_errs.append(ne_str)
                    print(f"    {ne_str}")
                if node_errs:
                    err_details = (err_details + " | " if err_details else "") + " ; ".join(node_errs)
        except:
            err_details = r.text[:400]
            print(f"  ComfyUI error: {r.text[:600]}")
        raise RuntimeError(f"ComfyUI {r.status_code}: {err_details}")
    return r.json()["prompt_id"]

def wait_for_result(prompt_id, jid):
    start = time.time()
    while True:
        # Check if user cancelled the job
        try:
            st = post("jobApi", {"action": "get", "job_id": jid})
            if st.get("job", {}).get("status") == "cancelled":
                print("  Job cancelled by user — interrupting ComfyUI")
                try:
                    requests.post(f"{COMFYUI_URL}/interrupt", json={}, timeout=5)
                except: pass
                return None
        except: pass
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            data = r.json()
            if prompt_id in data:
                return data[prompt_id].get("outputs", {})
        except:
            pass
        elapsed = int((time.time() - start) / 60)
        if elapsed > 45:
            try:
                requests.post(f"{COMFYUI_URL}/interrupt", json={}, timeout=5)
            except: pass
            raise TimeoutError("Render exceeded 45 minutes — aborted")
        post("jobApi", {"action": "progress", "job_id": jid, "progress": min(80, 50 + elapsed * 5)})
        time.sleep(3)

def get_output(outputs):
    for nid, out in outputs.items():
        if "gifs" in out and out["gifs"]:
            item = out["gifs"][0]
            fname = item.get("filename", "")
            if fname.lower().endswith(('.mp4', '.webm', '.avi', '.mov')):
                return item, "video"
            return item, "image"
        if "videos" in out and out["videos"]:
            return out["videos"][0], "video"
        if "images" in out and out["images"]:
            return out["images"][0], "image"
    return None, None

def download_file(item):
    params = {"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")}
    r = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=300)
    return r.content

def build_t2i(prompt, negative, lora=None, model=None, w=512, h=512):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["3"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    return wf

def download_lora(url):
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    if not os.path.isdir(lora_dir):
        os.makedirs(lora_dir, exist_ok=True)
    fname = url.split("/")[-1].split("?")[0] or "imported.safetensors"
    if not fname.endswith(('.safetensors', '.pt', '.ckpt', '.gguf')):
        fname += ".safetensors"
    fp = os.path.join(lora_dir, fname)
    if os.path.exists(fp):
        print(f"  LoRA exists: {fname}")
        return f"loras/{fname}"
    print(f"  Downloading LoRA: {fname}")
    try:
        r = requests.get(url, timeout=600, stream=True)
        r.raise_for_status()
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
        print(f"  LoRA downloaded: {fname}")
        return f"loras/{fname}"
    except Exception as e:
        print(f"  LoRA download failed: {e}")
        return None

def build_t2i_ipadapter(prompt, negative, ref_image, model=None, w=512, h=512):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "13": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["10", 0], "clip_vision": ["12", 0]}},
        "14": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["11", 0], "clip_vision": ["13", 0], "image": ["10", 0], "weight": 0.8, "model": ["4", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["14", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    return wf

def build_img2img(prompt, negative, source_image, lora=None, model=None, w=512, h=512, denoise=0.6):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": source_image}},
        "10a": {"class_type": "ImageScale", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10a", 0], "vae": ["4", 2]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["11", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    if lora:
        wf["12"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["3"]["inputs"]["model"] = ["12", 0]
        wf["6"]["inputs"]["clip"] = ["12", 1]
        wf["7"]["inputs"]["clip"] = ["12", 1]
    return wf

def build_face_swap(input_image, face_image):
    wf = {
        "10": {"class_type": "LoadImage", "inputs": {"image": input_image}},
        "11": {"class_type": "LoadImage", "inputs": {"image": face_image}},
        "12": {"class_type": "ReActorFaceSwap", "inputs": {
            "input_image": ["10", 0],
            "source_image": ["11", 0],
            "face_id": 0,
            "index": 0,
            "facedetection": "retinaface",
            "face_restore": "codeformer",
            "face_restore_weight": 0.5,
            "weight": 0.85,
        }},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi_swap", "images": ["12", 0]}},
    }
    return wf

def build_body_swap(input_image, ref_image, lora=None, model=None, denoise=0.6):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": input_image}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}},
        "20": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "21": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "22": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "23": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["20", 0], "clip_vision": ["22", 0]}},
        "24": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["21", 0], "clip_vision": ["23", 0], "image": ["20", 0], "weight": 0.8, "model": ["4", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "full body, high quality, detailed, same pose as input", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry, distorted, deformed, extra limbs", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["24", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["11", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi_body", "images": ["8", 0]}},
    }
    if lora:
        wf["25"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["24"]["inputs"]["model"] = ["25", 0]
        wf["6"]["inputs"]["clip"] = ["25", 1]
        wf["7"]["inputs"]["clip"] = ["25", 1]
    return wf

def is_sdxl_model(model_name):
    n = (model_name or "").lower()
    return "xl" in n or "sdxl" in n

# Motion modules can live in either the standard ComfyUI dir or the AnimateDiff-Evolved custom node dir
def mm_dirs():
    return [
        os.path.join(COMFYUI_PATH, "models", "animatediff_models"),
        os.path.join(COMFYUI_PATH, "custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models"),
    ]

def list_motion_modules():
    files = []
    for d in mm_dirs():
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith(('.ckpt', '.safetensors', '.pt')):
                files.append(f)
    return files

def video_supported(model=None):
    sdxl = is_sdxl_model(model)
    for f in list_motion_modules():
        if sdxl and ('sdxl' in f.lower() or 'xl' in f.lower()):
            return True
        if not sdxl and 'sdxl' not in f.lower() and 'xl' not in f.lower():
            return True
    return False

def find_motion_module(model=None):
    sdxl = is_sdxl_model(model)
    sdxl_mm = []
    sd15_mm = []
    for f in list_motion_modules():
        fl = f.lower()
        if 'sdxl' in fl or 'xl' in fl:
            sdxl_mm.append(f)
        else:
            sd15_mm.append(f)
    if sdxl and sdxl_mm:
        return sdxl_mm[0]
    if sdxl and not sdxl_mm and sd15_mm:
        print("  WARNING: No SDXL motion module found — using SD 1.5 module (may produce errors with SDXL)")
        return sd15_mm[0]
    if not sdxl and sd15_mm:
        return sd15_mm[0]
    if sdxl_mm:
        return sdxl_mm[0]
    if sd15_mm:
        return sd15_mm[0]
    return "mm_sdxl_v10_beta.ckpt" if sdxl else "mm_sd_v15_v2.ckpt"

def build_t2v_wan22(prompt, negative, w=832, h=480, frames=81, frame_rate=16, seed=None, lora=None, lora_strength=0.8, start_image=None, clip_vision=None, shift=3.0):
    """Wan 2.2 TI2V (GGUF) — מנוע הוידאו הראשי. API format ל-ComfyUI."""
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    wf = {
        "1": {"class_type": "UnetLoaderGGUF", "inputs": {"unet_name": WAN_MODEL}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": WAN_ENCODER, "type": "wan"}},
        "3": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 3.0}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["2", 0]}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "EmptyHunyuanLatentVideo", "inputs": {"width": w, "height": h, "length": frames, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 20, "cfg": 5.0, "sampler_name": "euler", "scheduler": "simple",
            "denoise": 1.0, "model": ["3", 0], "positive": ["5", 0], "negative": ["4", 0], "latent_image": ["6", 0]}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": WAN_VAE}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["8", 0]}},
        "10": {"class_type": "VHS_VideoCombine", "inputs": {
            "frame_rate": frame_rate, "loop_count": 0, "pingpong": False, "format": "video/h264-mp4",
            "filename_prefix": "wan22", "save_output": True, "images": ["9", 0]}},
    }
    model_out = ["1", 0]
    if lora:
        wf["1L"] = {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": lora, "strength_model": lora_strength, "model": ["1", 0]}}
        model_out = ["1L", 0]
    wf["3"]["inputs"]["model"] = model_out
    if start_image:
        # I2V: פריים ראשון מוזרק — שרשור שוטים לדמות עקבית (TI2V: start_image לבד מספיק, CLIP Vision אופציונלי)
        wf["12"] = {"class_type": "LoadImage", "inputs": {"image": start_image}}
        w2v = {"positive": ["5", 0], "negative": ["4", 0], "vae": ["8", 0],
               "width": w, "height": h, "length": frames, "batch_size": 1, "start_image": ["12", 0]}
        if clip_vision:
            wf["11"] = {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": clip_vision}}
            wf["13"] = {"class_type": "CLIPVisionEncode", "inputs": {"clip_vision": ["11", 0], "image": ["12", 0]}}
            w2v["clip_vision_output"] = ["13", 0]
        wf["14"] = {"class_type": "WanImageToVideo", "inputs": w2v}
        wf["3"]["inputs"]["shift"] = max(shift, 8.0)
        wf["7"]["inputs"]["positive"] = ["14", 0]
        wf["7"]["inputs"]["negative"] = ["14", 1]
        wf["7"]["inputs"]["latent_image"] = ["14", 2]
    return wf


def save_start_image_from_video(video_path, tag):
    """חילוץ הפריים האחרון של קטע → קובץ בתיקיית input של ComfyUI (לשרשור I2V)."""
    try:
        ff = get_ffmpeg_exe()
        base = os.path.dirname(os.path.abspath(__file__))
        inp_dir = os.path.join(COMFYUI_PATH, "input")
        os.makedirs(inp_dir, exist_ok=True)
        name = f"chain_{tag}.png"
        out = os.path.join(inp_dir, name)
        r = subprocess.run([ff, "-y", "-sseof", "-0.1", "-i", video_path, "-frames:v", "1", out],
                           capture_output=True, timeout=120)
        if r.returncode == 0 and os.path.exists(out):
            return name
    except Exception as e:
        print(f"  chain frame extract failed: {e}")
    return None


def get_output_cfg(key, default):
    return cfg.get(key, default)

def build_t2i_video(prompt, negative, lora=None, model=None, w=512, h=512, frames=16, frame_rate=8):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": frames}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model": ["4", 0], "model_name": mm, "beta_schedule": "sqrt_linear"}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["15", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["15"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    return wf

def build_t2i_video_ipadapter(prompt, negative, ref_image, model=None, w=512, h=512, frames=16, frame_rate=8):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": frames}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "13": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["10", 0], "clip_vision": ["12", 0]}},
        "14": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["11", 0], "clip_vision": ["13", 0], "image": ["10", 0], "weight": 0.8, "model": ["4", 0]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model": ["14", 0], "model_name": mm, "beta_schedule": "sqrt_linear"}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["15", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    return wf

def build_img2vid(prompt, negative, source_image, lora=None, model=None, w=512, h=512, frames=16, frame_rate=8, denoise=0.5):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": source_image}},
        "10a": {"class_type": "ImageScale", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10a", 0], "vae": ["4", 2]}},
        "12": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": max(1, frames - 1)}},
        "13": {"class_type": "LatentBatch", "inputs": {"samples1": ["11", 0], "samples2": ["12", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model": ["4", 0], "model_name": mm, "beta_schedule": "sqrt_linear"}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["15", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["13", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    if lora:
        wf["14"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["15"]["inputs"]["model"] = ["14", 0]
        wf["6"]["inputs"]["clip"] = ["14", 1]
        wf["7"]["inputs"]["clip"] = ["14", 1]
    return wf

def process_training_job(job):
    jid = job["id"]
    name = job.get("name", "character")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name)[:30] or "char"
    trigger = job.get("trigger_token", "") or safe_name
    dataset_urls = job.get("dataset_urls", [])
    steps = job.get("steps", 1500)
    resolution = job.get("resolution", 512)
    print(f"  Training: {name} ({len(dataset_urls)} images, {steps} steps, {resolution}px)")
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "busy", "current_job_type": "training", "current_job_progress": 0, "current_job_prompt": f"Training {name}"})
    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": 5})

    # Download dataset
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets", safe_name)
    if os.path.exists(dataset_dir):
        shutil.rmtree(dataset_dir)
    os.makedirs(dataset_dir, exist_ok=True)
    for i, url in enumerate(dataset_urls):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(os.path.join(dataset_dir, f"image_{i:03d}.png"), "wb") as f:
                f.write(r.content)
            with open(os.path.join(dataset_dir, f"image_{i:03d}.txt"), "w", encoding="utf-8") as f:
                f.write(trigger)
        except Exception as e:
            print(f"  Download failed: {e}")
    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": 15})

    sd_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sd-scripts")
    train_script = os.path.join(sd_scripts, "sd_train_network.py")
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    os.makedirs(lora_dir, exist_ok=True)
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_output")
    os.makedirs(output_dir, exist_ok=True)

    trained = False
    if os.path.exists(train_script):
        print("  sd-scripts found — running Kohya_ss training (SD 1.5)...")
        ckpt_path = os.path.join(COMFYUI_PATH, "models", "checkpoints", "v1-5-pruned-emaonly.safetensors")
        # Use accelerate CLI directly (python -m accelerate has no __main__)
        accelerate_exe = os.path.join(os.path.dirname(VENV_PY), "accelerate.exe")
        if os.path.exists(accelerate_exe):
            cmd = [accelerate_exe, "launch", "--num_cpu_threads_per_proc", "2", train_script,
                   "--pretrained_model_name_or_path", ckpt_path,
                   "--train_data_dir", dataset_dir,
                   "--output_dir", output_dir,
                   "--output_name", safe_name,
                   "--resolution", str(resolution),
                   "--learning_rate", "1e-4",
                   "--max_train_steps", str(steps),
                   "--network_module", "networks.lora",
                   "--network_dim", "32",
                   "--network_alpha", "16",
                   "--enable_bucket",
                   "--mixed_precision", "fp16",
                   "--save_precision", "fp16",
                   "--gradient_checkpointing",
                   "--cache_latents",
                   "--cache_text_encoder_outputs",
            ]
        else:
            # Fallback: python -m accelerate (may fail on some versions)
            cmd = [VENV_PY, "-m", "accelerate", "launch", "--num_cpu_threads_per_proc", "2", train_script,
            "--pretrained_model_name_or_path", ckpt_path,
            "--train_data_dir", dataset_dir,
            "--output_dir", output_dir,
            "--output_name", safe_name,
            "--resolution", str(resolution),
            "--learning_rate", "1e-4",
            "--max_train_steps", str(steps),
            "--network_module", "networks.lora",
            "--network_dim", "32",
            "--network_alpha", "16",
            "--enable_bucket",
            "--mixed_precision", "fp16",
            "--save_precision", "fp16",
            "--gradient_checkpointing",
            "--cache_latents",
            "--cache_text_encoder_outputs",
        ]
        try:
            proc = subprocess.Popen(cmd, cwd=sd_scripts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    print(f"  {line}")
                m = re.search(r'(\d+)/(\d+)', line)
                if m and ("it/s" in line or "s/it" in line):
                    cur, tot = int(m.group(1)), int(m.group(2))
                    pct = min(90, 15 + int(75 * cur / max(tot, 1)))
                    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": pct})
            proc.wait()
            if proc.returncode == 0:
                lora_file = os.path.join(output_dir, f"{safe_name}.safetensors")
                if os.path.exists(lora_file):
                    shutil.copy(lora_file, os.path.join(lora_dir, f"{safe_name}.safetensors"))
                    lora_path = f"loras/{safe_name}.safetensors"
                    post("shimiStudioAPI", {"action": "training_complete", "job_id": jid, "lora_path": lora_path})
                    print(f"  Training complete: {lora_path}")
                    trained = True
                else:
                    print("  Training finished but no LoRA file found")
            else:
                print(f"  Training failed (exit {proc.returncode})")
        except Exception as e:
            print(f"  Training error: {e}")
            traceback.print_exc()

    if not trained:
        # Fallback: IP-Adapter reference (no LoRA, but character consistency via reference image)
        print("  Falling back to IP-Adapter reference (no LoRA training)")
        first_image = dataset_urls[0] if dataset_urls else (job.get("face_image_url") or job.get("thumbnail_url"))
        post("shimiStudioAPI", {"action": "training_complete", "job_id": jid, "face_image_url": first_image, "fallback": True})
        print("  Character marked as completed (IP-Adapter reference mode)")

    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})

def parse_shots(prompt):
    """מפרק פרומפט ארוך לרשימת צילומים. פורמטים: שורת '---' בין צילומים, או 'SHOT N:' בתחילת כל צילום."""
    if not isinstance(prompt, str) or not prompt.strip():
        return []
    marks = list(re.finditer(r'(?im)^\s*[>*\-#\s]*\s*shot\s*\d+\s*[:.\-]\s*(.*)$', prompt))
    if len(marks) >= 2:
        shots = []
        for i, m in enumerate(marks):
            end = marks[i+1].start() if i+1 < len(marks) else len(prompt)
            first_line = (m.group(1) or "").strip()
            rest = prompt[m.end():end].strip()
            text = (first_line + "\n" + rest).strip() if rest else first_line
            if text:
                shots.append(text)
        return shots[:20]
    parts = re.split(r'(?m)^\s*[-*=~]{3,}\s*$', prompt)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts[:20]
    return []

def get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def concat_videos(paths, jid):
    ff = get_ffmpeg_exe()
    base = os.path.dirname(os.path.abspath(__file__))
    lst = os.path.join(base, f"concat_{jid[:8]}.txt")
    with open(lst, "w") as f:
        for p in paths:
            f.write("file '" + os.path.abspath(p).replace("'", "'\''") + "'\n")
    out = os.path.join(base, f"seq_{jid[:8]}.mp4")
    r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], capture_output=True, timeout=600)
    if r.returncode != 0:
        r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", out], capture_output=True, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError("concat failed: " + r.stderr.decode(errors="replace")[-300:])
    return out

def polish_video(src, tw=None, th=None, fps=24):
    """האפסקייל lanczos + החלקת פריימים ל-fps רציף. נכשל → מחזיר את המקור."""
    try:
        ff = get_ffmpeg_exe()
        out = src.replace(".mp4", "_final.mp4")
        vf = []
        if tw and th:
            vf.append(f"scale={tw}:{th}:flags=lanczos")
        if fps:
            mi = cfg.get("interp_mode", "mci")
            if mi == "mci":
                vf.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
            else:
                vf.append(f"minterpolate=fps={fps}:mi_mode=blend")
        if not vf:
            return src
        cmd = [ff, "-y", "-i", src, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", out]
        r = subprocess.run(cmd, capture_output=True, timeout=3600)
        if r.returncode == 0 and os.path.getsize(out) > 0:
            return out
        return src
    except Exception:
        return src

def process_video_sequence(job, jid, seq, model, lora, negative, vw, vh, fr, duration, ref_image_name, src_image_name):
    """רינדור רצף צילומים קצרים → הדבקה → האפסקייל → השלמה. מחזיר True אם הג'וב טופל עד סופו."""
    print(f"  Sequence mode: {len(seq)} shots @ {fr}fps | {vw}x{vh}")
    frames_per_shot = min(24, max(16, int(duration * 8)))
    base = os.path.dirname(os.path.abspath(__file__))
    seg_paths = []
    for si, sp in enumerate(seq):
        try:
            post("jobApi", {"action": "progress", "job_id": jid, "progress": int(10 + 70 * si / len(seq))})
            if src_image_name and si == 0:
                wf = build_img2vid(sp, negative, src_image_name, lora, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            elif ref_image_name:
                wf = build_t2i_video_ipadapter(sp, negative, ref_image_name, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            else:
                wf = build_t2i_video(sp, negative, lora, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            pid = queue_prompt(wf)
            outs = wait_for_result(pid, jid)
            if outs is None:
                return True  # cancelled
            item, otype = get_output(outs)
            if not item:
                raise RuntimeError(f"no output from shot {si+1}")
            data = download_file(item)
            seg = os.path.join(base, f"seq_{jid[:8]}_{si:02d}.mp4")
            with open(seg, "wb") as f:
                f.write(data)
            seg_paths.append(seg)
            print(f"  Shot {si+1}/{len(seq)} done")
        except Exception as e:
            print(f"  Shot {si+1}/{len(seq)} failed: {e}")
    if not seg_paths:
        post("jobApi", {"action": "fail", "job_id": jid, "error": "All shots failed"})
        return True
    post("jobApi", {"action": "progress", "job_id": jid, "progress": 85})
    try:
        final = seg_paths[0] if len(seg_paths) == 1 else concat_videos(seg_paths, jid)
        # האפסקייל ליעד: אנכי → x1.875, אחרת x2
        tw, th = int(vw * 1.875) // 2 * 2, int(vh * 1.875) // 2 * 2
        final = polish_video(final, tw, th, fps=24)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 92})
        with open(final, "rb") as f:
            file_data = f.read()
        result = post("jobApi", {"action": "complete", "job_id": jid, "file_base64": base64.b64encode(file_data).decode("utf-8"), "file_type": "video/mp4"}, timeout=1200)
        if result.get("error"):
            post("jobApi", {"action": "fail", "job_id": jid, "error": result["error"]})
        else:
            print(f"  Sequence completed: {jid} ({len(seg_paths)} shots)")
    except Exception as e:
        print(f"  Sequence stitch failed: {e}")
        traceback.print_exc()
        post("jobApi", {"action": "fail", "job_id": jid, "error": f"stitch failed: {e}"})
    # ניקוי קטעים זמניים
    for p in seg_paths:
        try: os.remove(p)
        except: pass
    return True

def process_wan_sequence(job, jid, seq, vw, vh, duration):
    """רצף שוטים ב-Wan 2.2 — כל שוט 16fps, הדבקה, האפסקייל. מחזיר True אם הג'וב טופל עד סופו."""
    print(f"  Wan sequence mode: {len(seq)} shots | {vw}x{vh}")
    n = max(1, len(seq))
    frames_per_shot = min(81, max(33, int(duration * 16 / n)))
    base = os.path.dirname(os.path.abspath(__file__))
    seg_paths = []
    chain = cfg.get("chain_shots", True)
    cv_model = cfg.get("wan", {}).get("clip_vision", "clip_vision_h.safetensors")
    lora_name = cfg.get("wan", {}).get("lora") or None
    lora_strength = float(cfg.get("wan", {}).get("lora_strength", 0.8))
    start_img = None
    for si, sp in enumerate(seq):
        try:
            post("jobApi", {"action": "progress", "job_id": jid, "progress": int(10 + 70 * si / len(seq))})
            wf = build_t2v_wan22(sp, negative=job.get("negative_prompt", ""), w=vw, h=vh, frames=frames_per_shot, frame_rate=16,
                                 lora=lora_name, lora_strength=lora_strength,
                                 start_image=(start_img if chain else None), clip_vision=(cv_model if chain and start_img else None))
            pid = queue_prompt(wf)
            outs = wait_for_result(pid, jid)
            if outs is None:
                return True  # cancelled
            item, otype = get_output(outs)
            if not item:
                raise RuntimeError(f"no output from shot {si+1}")
            data = download_file(item)
            seg = os.path.join(base, f"wseq_{jid[:8]}_{si:02d}.mp4")
            with open(seg, "wb") as f:
                f.write(data)
            seg_paths.append(seg)
            print(f"  Wan shot {si+1}/{len(seq)} done")
            if chain and si + 1 < len(seq):
                nxt = save_start_image_from_video(seg, f"{jid[:8]}_{si:02d}")
                if nxt:
                    start_img = nxt
                    print(f"  chained: next shot starts from last frame ({nxt})")
                else:
                    start_img = None
        except Exception as e:
            print(f"  Wan shot {si+1}/{len(seq)} failed: {e}")
    if not seg_paths:
        post("jobApi", {"action": "fail", "job_id": jid, "error": "All Wan shots failed"})
        return True
    post("jobApi", {"action": "progress", "job_id": jid, "progress": 85})
    try:
        final = seg_paths[0] if len(seg_paths) == 1 else concat_videos(seg_paths, jid)
        # יעד גימור מה-config — ברירת מחדל: אנכי 1080x1600 @30fps (סטנדרט לנה)
        ow, oh = cfg.get("output_size", [1080, 1600] if vh > vw else [1920, 1080])
        ofps = int(cfg.get("output_fps", 30))
        final = polish_video(final, int(ow) // 2 * 2, int(oh) // 2 * 2, fps=ofps)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 92})
        with open(final, "rb") as f:
            file_data = f.read()
        result = post("jobApi", {"action": "complete", "job_id": jid, "file_base64": base64.b64encode(file_data).decode("utf-8"), "file_type": "video/mp4"}, timeout=1800)
        if result.get("error"):
            post("jobApi", {"action": "fail", "job_id": jid, "error": result["error"]})
        else:
            print(f"  Wan sequence completed: {jid} ({len(seg_paths)} shots)")
    except Exception as e:
        print(f"  Wan stitch failed: {e}")
        traceback.print_exc()
        post("jobApi", {"action": "fail", "job_id": jid, "error": "sequence stitch failed: " + str(e)})
    return True

def process_job(job, character, scene, lora_cfg=None):
    jid = job["id"]
    jtype = job.get("type", "image")
    prompt = job.get("prompt", "")
    negative = job.get("negative_prompt", "")
    model = job.get("model") or "v1-5-pruned-emaonly.safetensors"
    lora = (lora_cfg or {}).get("lora_path") or (character.get("lora_path") if character else None)
    lora_url = (lora_cfg or {}).get("lora_url") or (character.get("lora_url") if character else None)
    trigger_token = (lora_cfg or {}).get("trigger_token") or (character.get("trigger_token") if character else None)
    if not lora and lora_url:
        lora = download_lora(lora_url)
    # Prepend trigger token to prompt so the LoRA concept activates
    if lora and trigger_token:
        prompt = f"{trigger_token}, {prompt}"
    source_imgs = job.get("source_images") or ([job.get("source_image")] if job.get("source_image") else []) or ([scene.get("source_image")] if scene and scene.get("source_image") else [])
    source_img = source_imgs[0] if source_imgs else None
    face_image = (character.get("face_image_url") if character else None) or (lora_cfg or {}).get("face_image_url")
    use_ipadapter = False
    ref_image_name = None
    if not lora and face_image:
        if 'IPAdapterApply' not in AVAILABLE_NODES:
            print("  IP-Adapter skipped — node not loaded (custom nodes disabled) — using style prompt only")
        else:
            ipadapter_model = os.path.join(COMFYUI_PATH, "models", "ipadapter", "ip-adapter-plus_sd15.safetensors")
            clip_vision_model = os.path.join(COMFYUI_PATH, "models", "clip_vision", "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
            if os.path.exists(ipadapter_model) and os.path.exists(clip_vision_model):
                try:
                    ref_image_name = f"ref_{jid[:8]}.png"
                    ref_path = os.path.join(COMFYUI_PATH, "input", ref_image_name)
                    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
                    save_image(face_image, ref_path)
                    use_ipadapter = True
                except Exception as e:
                    print(f"  Ref image download failed: {e}")
            else:
                missing = []
                if not os.path.exists(ipadapter_model): missing.append("ip-adapter-plus_sd15.safetensors")
                if not os.path.exists(clip_vision_model): missing.append("CLIP-ViT-H model")
                print(f"  IP-Adapter skipped — missing: {', '.join(missing)} — using style prompt only")
    # Download source images if present (for img2img / img2vid)
    src_image_name = None
    if source_imgs:
        for i, surl in enumerate(source_imgs):
            try:
                sname = f"src_{jid[:8]}_{i}.png"
                spath = os.path.join(COMFYUI_PATH, "input", sname)
                os.makedirs(os.path.dirname(spath), exist_ok=True)
                save_image(surl, spath)
                if i == 0:
                    src_image_name = sname
            except Exception as e:
                print(f"  Source image {i} download failed: {e}")
    print(f"  Processing: type={jtype} lora={lora} ipadapter={use_ipadapter} source_img={'yes' if source_img else 'no'}")
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "busy", "current_job_type": jtype, "current_job_progress": 0, "current_job_prompt": prompt[:80]})
    post("jobApi", {"action": "progress", "job_id": jid, "progress": 10})
    try:
        if jtype == "realtime_avatar":
            face_url = job.get("frame_url")
            face_name = None
            if face_url:
                try:
                    face_name = f"face_{jid[:8]}.png"
                    face_path = os.path.join(COMFYUI_PATH, "input", face_name)
                    os.makedirs(os.path.dirname(face_path), exist_ok=True)
                    save_image(face_url, face_path)
                except Exception as e:
                    print(f"  Face image download failed: {e}")
            if not src_image_name or not face_name:
                post("jobApi", {"action": "fail", "job_id": jid, "error": "Missing input frame or character face"})
                return
            swap_mode = job.get("swap_mode", "face")
            if swap_mode == "body":
                if 'IPAdapterApply' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "IP-Adapter node not loaded (custom nodes disabled) — body swap unavailable. Restart worker."})
                    return
                wf = build_body_swap(src_image_name, face_name, lora, model)
                print(f"  Body swap mode (IP-Adapter img2img)")
            else:
                if 'ReActorFaceSwap' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "ReActor node not loaded (custom nodes disabled) — face swap unavailable. Restart worker."})
                    return
                wf = build_face_swap(src_image_name, face_name)
                print(f"  Face swap mode (ReActor)")
        elif jtype == "video":
            engine = (str(job.get("engine") or DEFAULT_ENGINE or "").lower())
            duration = job.get("duration", 6)
            seq = parse_shots(prompt)
            if engine == "ltx":
                print("  engine ltx -> wan22 (LTX models not installed yet)")
                engine = "wan22"
            if engine == "wan22":
                ready, why = wan22_ready()
                if ready:
                    ar = str(job.get("aspect_ratio") or "").lower().replace(" ", "")
                    if ar in ("9:16", "vertical", "portrait", "story", "reels", "1080x1920"):
                        vw, vh = 480, 832
                    elif ar in ("2:3", "3:4", "1080x1600", "1080x1440"):
                        vw, vh = 512, 768
                    elif ar in ("1:1", "square"):
                        vw, vh = 640, 640
                    else:
                        vw, vh = 832, 480
                    if len(seq) >= 2:
                        handled = process_wan_sequence(job, jid, seq, vw, vh, duration)
                        if handled:
                            post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})
                            return
                    wframes = min(121, max(33, int(duration * 16)))
                    wf = build_t2v_wan22(prompt, negative, w=vw, h=vh, frames=wframes, frame_rate=16)
                    print(f"  Wan2.2 T2V: {vw}x{vh} {wframes} frames (~{wframes/16:.1f}s) model={WAN_MODEL}")
                else:
                    print(f"  Wan2.2 not ready ({why}) — falling back to AnimateDiff (ad15)")
                    engine = ""
            if engine != "wan22":
                if 'ADE_AnimateDiffLoaderGen1' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "AnimateDiff node not loaded (custom nodes disabled) — cannot generate video locally. Restart worker or use cloud mode."})
                    return
                if 'VHS_VideoCombine' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "VideoHelperSuite not installed — cannot encode video. Reinstall worker."})
                    return
                if not video_supported(model):
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "AnimateDiff motion module not installed — cannot generate video locally. Reinstall worker or use cloud mode."})
                    return
                sdxl = is_sdxl_model(model)
                # פורמט מסך: אנכי (9:16/2:3) או ריבוע
                ar = str(job.get("aspect_ratio") or "").lower().replace(" ", "")
                if ar in ("9:16", "vertical", "portrait", "story", "reels", "1080x1920"):
                    vw, vh = (576, 1024) if not sdxl else (1024, 1024)
                elif ar in ("2:3", "3:4", "1080x1600", "1080x1440"):
                    vw, vh = (512, 768) if not sdxl else (1024, 1024)
                else:
                    vw, vh = (1024, 1024) if sdxl else (512, 512)
                duration = job.get("duration", 6)
                # רצף צילומים — פרומפט מרובה שוטים → רינדור כל שוט והדבקה
                seq = parse_shots(prompt)
                if len(seq) >= 2:
                    handled = process_video_sequence(job, jid, seq, model, lora, negative, vw, vh, fr=8, duration=duration, ref_image_name=(ref_image_name if use_ipadapter else None), src_image_name=src_image_name)
                    if handled:
                        post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})
                        return
                frames = min(48, max(16, int(duration * 8)))
                fr = max(1, round(frames / duration))
                if src_image_name:
                    wf = build_img2vid(prompt, negative, src_image_name, lora, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                    print(f"  Img2Vid: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}] source={src_image_name}")
                elif use_ipadapter:
                    wf = build_t2i_video_ipadapter(prompt, negative, ref_image_name, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                    print(f"  Video: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}] ipadapter")
                else:
                    wf = build_t2i_video(prompt, negative, lora, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                    print(f"  Video: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}]")
        elif src_image_name:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_img2img(prompt, negative, src_image_name, lora, model, w=iw, h=ih)
            print(f"  Img2Img [{'SDXL' if sdxl else 'SD1.5'}]")
        elif use_ipadapter:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_t2i_ipadapter(prompt, negative, ref_image_name, model, w=iw, h=ih)
            print(f"  T2I+IPAdapter [{'SDXL' if sdxl else 'SD1.5'}]")
        else:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_t2i(prompt, negative, lora, model, w=iw, h=ih)
            print(f"  T2I [{'SDXL' if sdxl else 'SD1.5'}]")
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 30})
        prompt_id = queue_prompt(wf)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 50})
        outputs = wait_for_result(prompt_id, jid)
        if outputs is None:
            print(f"  Job cancelled: {jid}")
            return
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 85})
        item, out_type = get_output(outputs)
        if not item:
            post("jobApi", {"action": "fail", "job_id": jid, "error": "No output from ComfyUI"})
            return
        file_data = download_file(item)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 90})
        file_b64 = base64.b64encode(file_data).decode("utf-8")
        ftype = "video/mp4" if out_type == "video" else "image/png"
        result = post("jobApi", {"action": "complete", "job_id": jid, "file_base64": file_b64, "file_type": ftype}, timeout=600)
        if result.get("error"):
            print(f"  Upload failed: {result['error']}")
            post("jobApi", {"action": "fail", "job_id": jid, "error": result["error"]})
        else:
            print(f"  Job completed: {jid}")
    except Exception as e:
        print(f"  Job failed: {e}")
        traceback.print_exc()
        post("jobApi", {"action": "fail", "job_id": jid, "error": str(e)})
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})

def scan_loras():
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    if not os.path.isdir(lora_dir):
        print(f"  LoRA dir not found: {lora_dir}")
        return
    loras = []
    for f in os.listdir(lora_dir):
        if f.lower().endswith(('.safetensors', '.pt', '.ckpt', '.gguf')):
            fp = os.path.join(lora_dir, f)
            size_mb = round(os.path.getsize(fp) / (1024*1024), 1)
            name = os.path.splitext(f)[0]
            loras.append({"name": name, "path": f"loras/{f}", "size_mb": size_mb})
    print(f"  Found {len(loras)} LoRA files")
    r = post("workerApi", {"action":"report_loras","token":TOKEN,"loras":loras})
    print(f"  LoRAs imported: {r.get('imported',0)}, skipped: {r.get('skipped',0)}")

def scan_checkpoints():
    ckpt_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    if not os.path.isdir(ckpt_dir):
        print(f"  Checkpoint dir not found: {ckpt_dir}")
        return
    checkpoints = []
    for f in os.listdir(ckpt_dir):
        if f.lower().endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
            checkpoints.append(f)
    print(f"  Found {len(checkpoints)} checkpoint models")
    post("workerApi", {"action":"report_checkpoints","token":TOKEN,"checkpoints":checkpoints})

def download_pending_models():
    r = post("shimiStudioAPI", {"action": "list_pending_downloads", "token": TOKEN})
    downloads = r.get("downloads", [])
    for dl in downloads:
        download_model(dl)

def download_model(dl):
    mid = dl["id"]
    mtype = dl["type"]
    url = dl["url"]
    mname = dl["name"]
    if mtype == "checkpoint":
        target_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    elif mtype == "lora":
        target_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    elif mtype == "motion_module":
        target_dir = os.path.join(COMFYUI_PATH, "models", "animatediff_models")
    else:
        print(f"  Unknown model type: {mtype}")
        return
    os.makedirs(target_dir, exist_ok=True)
    fname = url.split("/")[-1].split("?")[0] or f"{mname}.safetensors"
    if not fname.endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
        fname += ".safetensors"
    fp = os.path.join(target_dir, fname)
    if os.path.exists(fp):
        print(f"  Model already exists: {fname}")
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "completed", "file_path": f"{os.path.basename(target_dir)}/{fname}"})
        return
    print(f"  Downloading model: {mname} ({mtype})")
    post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "downloading", "worker_id": TOKEN})
    try:
        r = requests.get(url, timeout=600, stream=True)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded % (5*1024*1024) < 1024*1024:
                    post("workerApi", {"action":"heartbeat","token":TOKEN,"status":"busy","current_job_type":"downloading","current_job_progress":min(95, int(100*downloaded/max(total,1))),"current_job_prompt":f"Downloading {mname}"})
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "completed", "file_path": f"{os.path.basename(target_dir)}/{fname}"})
        print(f"  Model downloaded: {fname}")
        if mtype == "checkpoint":
            scan_checkpoints()
        elif mtype == "lora":
            scan_loras()
    except Exception as e:
        print(f"  Model download failed: {e}")
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "failed", "error": str(e)})

print("========================================")
print("  ShimiStudio Worker v4.4 - Running (engines: wan22 + ad15)")
print("========================================")
print(f"  Server: {SERVER}")
print(f"  Name:   {NAME}")
print(f"  Token:  {TOKEN[:8]}...")
print()

# ── Startup (each step wrapped to prevent crash before main loop) ──
try:
    post("workerApi", {"action":"register","token":TOKEN,"name":NAME,"os_type": ("mac" if sys.platform == "darwin" else ("windows" if os.name == "nt" else "linux")),"gpu_model":"auto","vram_total":0})
    print("  Registered with server")
except Exception as e:
    print(f"  Registration failed: {e}")

try:
    scan_loras()
except Exception as e:
    print(f"  LoRA scan failed: {e}")

try:
    scan_checkpoints()
except Exception as e:
    print(f"  Checkpoint scan failed: {e}")

try:
    if start_comfyui():
        fetch_available_nodes()
        if 'ADE_AnimateDiffLoaderGen1' not in AVAILABLE_NODES:
            print("  ! AnimateDiff node not loaded — VIDEO GENERATION WILL FAIL. Reinstall worker or check ComfyUI-AnimateDiff-Evolved in custom_nodes/")
        if 'IPAdapterApply' not in AVAILABLE_NODES:
            print("  ! IP-Adapter node not loaded — character reference will use style prompt only.")
    else:
        print("  WARNING: ComfyUI not available - jobs will fail until ComfyUI is running")
except Exception as e:
    print(f"  ComfyUI startup error: {e}")
    print("  Worker continues without ComfyUI — jobs will fail until ComfyUI is running")

while True:
    try:
        post("workerApi", {"action":"heartbeat","token":TOKEN,"status":"online","gpu_util":0,"vram_used":0,"ping_ms":10})
        # Check for training jobs first (priority)
        tr = post("shimiStudioAPI", {"action": "claim_training", "token": TOKEN})
        tr_job = tr.get("job")
        if tr_job:
            print(f"  Training job claimed: {tr_job.get('name')}")
            process_training_job(tr_job)
            continue
        # Then check for render jobs
        r = post("jobApi", {"action":"claim","token":TOKEN})
        job = r.get("job")
        if job:
            character = r.get("character")
            scene = r.get("scene")
            lora_cfg = r.get("lora") or {}
            print(f"  Job claimed: {job.get('id')} type={job.get('type')} lora={lora_cfg.get('lora_path') or 'none'}")
            process_job(job, character, scene, lora_cfg)
        # Check for pending model downloads (lowest priority)
        download_pending_models()
    except Exception as e:
        print(f"  Loop error: {e}")
        traceback.print_exc()
    time.sleep(5)  # Poll interval — without this the loop spins infinitely and crashes
