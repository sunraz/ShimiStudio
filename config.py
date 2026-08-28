"""
ShimiStudio v2.0 — Configuration
קובץ ההגדרות המרכזי. כל המודולים משתמשים בו.
"""

import os
import json
from pathlib import Path

# ============================================================
# Paths
# ============================================================

# בסיס הפרויקט
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = BASE_DIR / "temp"
LOG_DIR = BASE_DIR / "logs"

# ComfyUI
COMFYUI_DIR = Path(os.environ.get("COMFYUI_DIR", str(Path.home() / "ComfyUI")))
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188")
COMFYUI_OUTPUT_DIR = COMFYUI_DIR / "output"

# מודלים
MODELS_DIR = COMFYUI_DIR / "models"
CHECKPOINTS_DIR = MODELS_DIR / "checkpoints"
VAE_DIR = MODELS_DIR / "vae"
LORA_DIR = MODELS_DIR / "loras"
CONTROLNET_DIR = MODELS_DIR / "controlnet"
IPADAPTER_DIR = MODELS_DIR / "ipadapter"
INSIGHTFACE_DIR = MODELS_DIR / "insightface"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"

# יצירת תיקיות אם לא קיימות
for d in [OUTPUT_DIR, TEMP_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ============================================================
# Base44 — תור העבודות
# ============================================================

BASE44_APP_ID = os.environ.get("BASE44_APP_ID", "6a901f55a4d9a9b76a095a77")
BASE44_API_URL = os.environ.get("BASE44_API_URL", "https://api.base44.com")
BASE44_ENTITY = "RenderJob"
BASE44_TOKEN = os.environ.get("BASE44_TOKEN", "")  # אם יש טוקן, אחרת נשתמש ב-backend function

# Worker
WORKER_ID = os.environ.get("WORKER_ID", "worker-001")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))  # שניות בין תחקורים

# ============================================================
# API Keys (ממשתני סביבה)
# ============================================================

API_KEYS = {
    "lucydream": os.environ.get("LUCYDREAM_API_KEY", ""),
    "huggingface": os.environ.get("HF_TOKEN", ""),
    "deepai": os.environ.get("DEEPAI_API_KEY", ""),
    "replicate": os.environ.get("REPLICATE_API_TOKEN", ""),
    "openai": os.environ.get("OPENAI_API_KEY", ""),
    "elevenlabs": os.environ.get("ELEVENLABS_API_KEY", ""),
    "civitai": os.environ.get("CIVITAI_TOKEN", ""),
}

# ============================================================
# Engine Selection
# ============================================================

# איזה מנוע להשתמש: "comfyui" (מקומי) או "free_api" (חינמי) או "auto" (ComfyUI → free API fallback)
ENGINE_MODE = os.environ.get("ENGINE_MODE", "auto")

# ============================================================
# Default Settings
# ============================================================

DEFAULTS = {
    "image_model": "flux",
    "image_model_nsfw": "flux-uncensored",  # Heartsync/Flux-NSFW-uncensored
    "image_model_pony": "pony_v6_xl",  # Pony Diffusion V6 XL (uncensored SDXL)
    "video_model": "wan22_i2v",
    "image_width": 1024,
    "image_height": 1024,
    "video_duration": 5,
    "video_fps": 24,
    "video_aspect": "16:9",
    "face_id_weight": 1.0,
    "negative_prompt": "low quality, blurry, deformed, ugly, bad anatomy, watermark, text",
    "steps": 25,
    "cfg_scale": 7.5,
    "sampler": "euler",
    "scheduler": "normal",
}

# ============================================================
# Logging
# ============================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "shimistudio.log"

import logging

def setup_logger(name: str = "shimistudio") -> logging.Logger:
    """מגדיר logger מרכזי"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(console)
    
    # File
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(file_handler)
    
    return logger

# ============================================================
# Health Check
# ============================================================

def print_config():
    """מדפיס את ההגדרות הנוכחיות"""
    print("=" * 60)
    print("  ShimiStudio v2.0 — Configuration")
    print("=" * 60)
    print(f"  Base Dir:        {BASE_DIR}")
    print(f"  ComfyUI Dir:     {COMFYUI_DIR}")
    print(f"  ComfyUI URL:     {COMFYUI_URL}")
    print(f"  Output Dir:      {OUTPUT_DIR}")
    print(f"  Engine Mode:     {ENGINE_MODE}")
    print(f"  Worker ID:       {WORKER_ID}")
    print(f"  Poll Interval:   {POLL_INTERVAL}s")
    print(f"  Base44 App:      {BASE44_APP_ID}")
    print(f"  Base44 Entity:   {BASE44_ENTITY}")
    print(f"  API Keys:")
    for name, key in API_KEYS.items():
        status = "✅" if key else "❌"
        print(f"    {name:15s} {status}")
    print("=" * 60)

if __name__ == "__main__":
    print_config()
