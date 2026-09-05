#!/usr/bin/env python3
"""
ShimiStudio — One-Click Installer v2.0
מתקין: ComfyUI + מודלים + LoRAs + Worker + חיבור ל-Base44
עם GitHub token ו-CivitAI API key מוטמעים
"""
import os, sys, json, subprocess, urllib.request, requests, time, platform

# === הגדרות מוטמעות ===
import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
CIVITAI_KEY = os.environ.get("CIVITAI_API_KEY", "")
BASE_DIR = os.path.join(os.path.expanduser("~"), "ShimiStudio")
COMFYUI_DIR = os.path.join(BASE_DIR, "ComfyUI")
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
WORKER_URL = "https://base44.app/api/apps/6a901f55a4d9a9b76a095a77/files/mp/public/6a901f55a4d9a9b76a095a77/32648d33d_worker_v3.py"
LORA_REPORTER_URL = "https://base44.app/api/apps/6a901f55a4d9a9b76a095a77/files/mp/public/6a901f55a4d9a9b76a095a77/2bf31794c_report_models.py"

# === Shimi Studio Manager API ===
STUDIO_APP_ID = "6a9206e9f29b8d9f70a77b47"
API_BASE = f"https://preview-sandbox--{STUDIO_APP_ID}.base44.app/api/apps/{STUDIO_APP_ID}"
WORKER_TOKEN = "36492b03a2324c5da2c87b11"
WORKER_NAME = "Worker-Windows"

# === מודלים להורדה ===
MODELS = [
    ("cyberrealistic_final.safetensors", "https://civitai.com/api/download/models/2682196", "CyberRealistic Final (SD 1.5, NSFW, 2GB)"),
]

# === LoRAs להורדה ===
LORAS = [
    ("add_detail.safetensors", "https://civitai.com/api/download/models/62833", "Detail Tweaker (578K dl)"),
    ("more_details.safetensors", "https://civitai.com/api/download/models/87153", "Add More Details (407K dl)"),
    ("epi_noiseoffset2.safetensors", "https://civitai.com/api/download/models/16576", "epi_noiseoffset (228K dl)"),
    ("PSCowgirl.safetensors", "https://civitai.com/api/download/models/10490", "POV Squatting Cowgirl (206K dl)"),
    ("nudify_xl_lite.safetensors", "https://civitai.com/api/download/models/177674", "Nudify XL Better Bodies (362K dl)"),
    ("innievag.safetensors", "https://civitai.com/api/download/models/12873", "Innies Better vulva (204K dl)"),
    ("ClothingAdjuster3.safetensors", "https://civitai.com/api/download/models/117151", "LEOSAM Clothing Adjuster (140K dl)"),
    ("AfterSexMS.safetensors", "https://civitai.com/api/download/models/21538", "After Sex Lying (131K dl)"),
    ("mix4.safetensors", "https://civitai.com/api/download/models/16677", "Cute girl mix4 (229K dl)"),
    ("edgBondDollLikenessv1.safetensors", "https://civitai.com/api/download/models/530857", "Doll Likeness (260K dl)"),
]

def log(msg, level="  "):
    print(f"{level}{msg}")

def download_file(url, dest, desc="", use_civitai=True):
    if os.path.exists(dest) and os.path.getsize(dest) > 10000:
        log(f"[SKIP] {os.path.basename(dest)} exists ({os.path.getsize(dest)//1024//1024}MB)")
        return True
    
    log(f"[DOWN] {os.path.basename(dest)} — {desc}")
    headers = {}
    if use_civitai:
        headers["Authorization"] = f"Bearer {CIVITAI_KEY}"
    
    try:
        r = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=600)
        if r.status_code != 200:
            log(f"[FAIL] HTTP {r.status_code}")
            return False
        
        total = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
        
        log(f"[OK]   {os.path.basename(dest)} — {total/1024/1024:.1f}MB")
        return True
    except Exception as e:
        log(f"[FAIL] {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False

def setup_dirs():
    dirs = [
        BASE_DIR,
        os.path.join(COMFYUI_DIR, "models", "checkpoints"),
        os.path.join(COMFYUI_DIR, "models", "loras"),
        os.path.join(COMFYUI_DIR, "input"),
        os.path.join(COMFYUI_DIR, "output"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    log(f"Directories ready: {BASE_DIR}")

def setup_config():
    config = {
        "apiBase": API_BASE,
        "comfyui_path": COMFYUI_DIR,
        "server": f"https://preview-sandbox--{STUDIO_APP_ID}.base44.app",
        "name": WORKER_NAME,
        "token": WORKER_TOKEN
    }
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    log(f"Config written: {config_path}")

def download_worker():
    worker_path = os.path.join(BASE_DIR, "worker_v3.py")
    log(f"[DOWN] worker_v3.py")
    try:
        r = requests.get(WORKER_URL, timeout=30)
        with open(worker_path, "wb") as f:
            f.write(r.content)
        log(f"[OK]   worker_v3.py — {len(r.content)//1024}KB")
    except Exception as e:
        log(f"[FAIL] worker: {e}")

def download_reporter():
    reporter_path = os.path.join(BASE_DIR, "report_models.py")
    try:
        r = requests.get(LORA_REPORTER_URL, timeout=30)
        with open(reporter_path, "wb") as f:
            f.write(r.content)
        log(f"[OK]   report_models.py")
    except:
        pass

def create_env_file():
    """יוצר קובץ .env עם הטוקנים"""
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "w") as f:
        f.write(f"GITHUB_TOKEN={GITHUB_TOKEN}\n")
        f.write(f"CIVITAI_API_KEY={CIVITAI_KEY}\n")
    log(f"Tokens saved: {env_path}")

def create_run_scripts():
    """יוצר סקריפטי הפעלה"""
    # start_worker.bat
    bat = os.path.join(BASE_DIR, "start_worker.bat")
    with open(bat, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'cd /d "{BASE_DIR}"\n')
        f.write(f'"{VENV_PYTHON}" worker_v3.py\n')
        f.write(f'pause\n')
    log(f"start_worker.bat created")
    
    # start_comfyui.bat
    bat2 = os.path.join(BASE_DIR, "start_comfyui.bat")
    with open(bat2, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'cd /d "{COMFYUI_DIR}"\n')
        f.write(f'"{VENV_PYTHON}" main.py --listen 127.0.0.1 --port 8188\n')
        f.write(f'pause\n')
    log(f"start_comfyui.bat created")
    
    # download_loras.bat
    bat3 = os.path.join(BASE_DIR, "download_loras.bat")
    with open(bat3, "w") as f:
        f.write(f'@echo off\n')
        f.write(f'cd /d "{BASE_DIR}"\n')
        f.write(f'"{VENV_PYTHON}" download_loras.py\n')
        f.write(f'pause\n')
    log(f"download_loras.bat created")

def report_models_to_base44():
    """מדווח על המודלים וה-LoRAs ל-Base44"""
    try:
        models = [f for f in os.listdir(os.path.join(COMFYUI_DIR, "models", "checkpoints")) if f.endswith(".safetensors")]
        loras = [f for f in os.listdir(os.path.join(COMFYUI_DIR, "models", "loras")) if f.endswith(".safetensors")]
        
        studio_api = "https://solas-6a095a77.base44.app/functions/shimiStudioAPI"
        r = requests.post(studio_api, json={
            "action": "report_models",
            "worker_id": WORKER_NAME,
            "models": models,
            "loras": loras,
            "vram": 5120
        }, timeout=15)
        d = r.json()
        if d.get("success"):
            log(f"Models reported to Base44: {len(models)} checkpoints, {len(loras)} LoRAs")
        else:
            log(f"Report failed: {d.get('error')}")
    except Exception as e:
        log(f"Report error: {e}")

# === MAIN ===
print("=" * 55)
print("  ShimiStudio Installer v2.0")
print("  One-click setup with models, LoRAs, and worker")
print("=" * 55)
print()

# 1. Directories
log("Step 1: Setting up directories...")
setup_dirs()
print()

# 2. Models
log("Step 2: Downloading models...")
ckpt_dir = os.path.join(COMFYUI_DIR, "models", "checkpoints")
for fname, url, desc in MODELS:
    download_file(url, os.path.join(ckpt_dir, fname), desc)
print()

# 3. LoRAs
log("Step 3: Downloading LoRAs...")
lora_dir = os.path.join(COMFYUI_DIR, "models", "loras")
for i, (fname, url, desc) in enumerate(LORAS, 1):
    log(f"  [{i}/{len(LORAS)}]")
    download_file(url, os.path.join(lora_dir, fname), desc)
    time.sleep(0.5)
print()

# 4. Config
log("Step 4: Writing configuration...")
setup_config()
print()

# 5. Tokens
log("Step 5: Saving tokens (GitHub + CivitAI)...")
create_env_file()
print()

# 6. Worker
log("Step 6: Downloading worker script...")
download_worker()
download_reporter()
print()

# 7. Run scripts
log("Step 7: Creating run scripts...")
create_run_scripts()
print()

# 8. Report to Base44
log("Step 8: Reporting models to Base44...")
report_models_to_base44()
print()

# Summary
print("=" * 55)
print("  INSTALLATION COMPLETE!")
print("=" * 55)
print(f"  Location: {BASE_DIR}")
print()
print("  To start rendering:")
print("    1. Run: start_comfyui.bat  (starts ComfyUI)")
print("    2. Run: start_worker.bat   (starts the worker)")
print()
print("  To download more LoRAs:")
print("    Run: download_loras.bat")
print()
print("  Models and LoRAs are reported to the Studio UI.")
print("=" * 55)
