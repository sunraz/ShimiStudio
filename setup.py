#!/usr/bin/env python3
"""
ShimiStudio PC Setup Script
Complete installation script for ShimiStudio PC Video Generation System.
Checks Python version, detects GPU, creates virtual environment,
installs ComfyUI + custom nodes, installs python requirements, and downloads required AI models.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Step 0: Ensure minimum Python version (3.10+)
REQUIRED_PYTHON = (3, 10)
if sys.version_info < REQUIRED_PYTHON:
    print(f"❌ Error: Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ is required.")
    print(f"   Current version: {sys.version.split()[0]}")
    sys.exit(1)

# Ensure base helper packages (requests, tqdm) exist in runner python for model downloading
def ensure_bootstrap_packages():
    try:
        import requests
        import tqdm
    except ImportError:
        print("📦 Installing installer bootstrap packages (requests, tqdm)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests", "tqdm"])

ensure_bootstrap_packages()

import requests
from tqdm import tqdm

# Base paths
ROOT_DIR = Path(__file__).resolve().parent
VENV_DIR = ROOT_DIR / ".venv"
COMFYUI_DIR = ROOT_DIR / "ComfyUI"
OUTPUT_DIR = ROOT_DIR / "output"

def get_venv_paths():
    if sys.platform == "win32":
        python_exe = VENV_DIR / "Scripts" / "python.exe"
        pip_exe = VENV_DIR / "Scripts" / "pip.exe"
    else:
        python_exe = VENV_DIR / "bin" / "python"
        pip_exe = VENV_DIR / "bin" / "pip"
    return python_exe, pip_exe

def check_gpu() -> bool:
    """Detect if NVIDIA CUDA GPU is available via nvidia-smi or torch."""
    print("🔍 Checking hardware environment...")
    # Try nvidia-smi
    has_nvidia_smi = False
    try:
        res = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            has_nvidia_smi = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        has_nvidia_smi = False

    # Try torch if installed
    has_torch_cuda = False
    try:
        import torch
        if torch.cuda.is_available():
            has_torch_cuda = True
    except ImportError:
        pass

    if has_nvidia_smi or has_torch_cuda:
        print("🎮 NVIDIA GPU (CUDA) detected! High-performance generation enabled.")
        return True
    else:
        print("💻 No NVIDIA GPU detected. Running in CPU-only mode (generation will be slower).")
        return False

def setup_venv():
    """Create virtual environment if it does not exist."""
    venv_python, venv_pip = get_venv_paths()
    if not venv_python.exists():
        print(f"⚙️ Creating virtual environment at {VENV_DIR}...")
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])
            print("✅ Virtual environment created successfully.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            sys.exit(1)
    else:
        print("ℹ️ Virtual environment already exists.")
    
    # Upgrade pip inside venv
    try:
        subprocess.check_call([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])
    except subprocess.CalledProcessError:
        pass

    return venv_python, venv_pip

def install_requirements(venv_python: Path, has_cuda: bool):
    """Install required Python packages and PyTorch."""
    print("📦 Installing package dependencies...")
    
    req_file = ROOT_DIR / "requirements.txt"
    if req_file.exists():
        try:
            subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(req_file)])
            print("✅ Core requirements installed.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install requirements.txt: {e}")
            sys.exit(1)

    # Install PyTorch
    print("📦 Installing PyTorch...")
    try:
        if has_cuda:
            torch_cmd = [
                str(venv_python), "-m", "pip", "install",
                "torch", "torchvision", "torchaudio",
                "--extra-index-url", "https://download.pytorch.org/whl/cu121"
            ]
        else:
            torch_cmd = [
                str(venv_python), "-m", "pip", "install",
                "torch", "torchvision", "torchaudio"
            ]
        subprocess.check_call(torch_cmd)
        print("✅ PyTorch installation completed.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyTorch: {e}")
        sys.exit(1)

def install_comfyui(venv_python: Path):
    """Clone ComfyUI and install its dependencies and custom nodes."""
    print("🚀 Setting up ComfyUI...")
    
    if not COMFYUI_DIR.exists():
        print("📥 Cloning ComfyUI from GitHub...")
        try:
            subprocess.check_call([
                "git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(COMFYUI_DIR)
            ])
            print("✅ ComfyUI cloned.")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to clone ComfyUI repository: {e}")
            sys.exit(1)
    else:
        print("ℹ️ ComfyUI directory already exists.")

    # Install ComfyUI requirements
    comfy_reqs = COMFYUI_DIR / "requirements.txt"
    if comfy_reqs.exists():
        print("📦 Installing ComfyUI python dependencies...")
        try:
            subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(comfy_reqs)])
            print("✅ ComfyUI dependencies installed.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Warning: Some ComfyUI dependencies failed to install: {e}")

    # Custom nodes
    custom_nodes_dir = COMFYUI_DIR / "custom_nodes"
    custom_nodes_dir.mkdir(parents=True, exist_ok=True)

    nodes = [
        {
            "name": "ComfyUI-VideoHelperSuite",
            "repo": "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
        },
        {
            "name": "ComfyUI-AnimateDiff-Evolved",
            "repo": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git"
        }
    ]

    for node in nodes:
        node_path = custom_nodes_dir / node["name"]
        if not node_path.exists():
            print(f"📥 Cloning custom node: {node['name']}...")
            try:
                subprocess.check_call(["git", "clone", node["repo"], str(node_path)])
                print(f"✅ {node['name']} installed.")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Warning: Failed to clone node {node['name']}: {e}")
        else:
            print(f"ℹ️ Custom node {node['name']} already exists.")

        # Install custom node dependencies if present
        node_reqs = node_path / "requirements.txt"
        if node_reqs.exists():
            try:
                subprocess.check_call([str(venv_python), "-m", "pip", "install", "-r", str(node_reqs)])
            except subprocess.CalledProcessError:
                pass

def download_file(url: str, dest_path: Path):
    """Download a file with tqdm progress bar and error handling."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(dest_path.suffix + ".downloading")

    # If file exists and size is reasonably non-zero, skip
    if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
        size_mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"⏩ {dest_path.name} already downloaded ({size_mb:.1f} MB). Skipping.")
        return

    print(f"📥 Downloading {dest_path.name}...")
    headers = {"User-Agent": "ShimiStudio-Installer/1.0"}
    
    try:
        response = requests.get(url, stream=True, headers=headers, timeout=30)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))

        with open(temp_path, "wb") as f, tqdm(
            desc=dest_path.name,
            total=total_size,
            unit="iB",
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    bar.update(len(chunk))

        temp_path.rename(dest_path)
        print(f"✅ Downloaded {dest_path.name} successfully.")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        print(f"❌ Error downloading {dest_path.name} from {url}: {e}")
        raise

def download_models():
    """Download required AI models into appropriate ComfyUI subdirectories."""
    print("🎨 Downloading AI models for Wan 2.1 and LTX-Video...")

    models = [
        {
            "name": "Wan 2.1 1.3B Diffusion Model",
            "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/wan_t2v_1.3B_bf16.safetensors",
            "dest": COMFYUI_DIR / "models" / "diffusion_models" / "wan_t2v_1.3B_bf16.safetensors"
        },
        {
            "name": "Wan 2.1 VAE",
            "url": "https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B/resolve/main/files/wan_2.1_vae.safetensors",
            "dest": COMFYUI_DIR / "models" / "vae" / "wan_2.1_vae.safetensors"
        },
        {
            "name": "umt5-xxl Text Encoder (quantized fp8)",
            "url": "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_text_encoder_models/resolve/main/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
            "dest": COMFYUI_DIR / "models" / "text_encoders" / "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
        },
        {
            "name": "LTX-Video 2B Model",
            "url": "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.safetensors",
            "dest": COMFYUI_DIR / "models" / "checkpoints" / "ltx-video-2b-v0.9.safetensors"
        },
        {
            "name": "LTX Text Encoder",
            "url": "https://huggingface.co/Comfy-Org/LTX-Video_ComfyUI/resolve/main/text_encoder/model.safetensors",
            "dest": COMFYUI_DIR / "models" / "text_encoders" / "ltx_text_encoder.safetensors"
        }
    ]

    for model in models:
        try:
            download_file(model["url"], model["dest"])
        except Exception as e:
            print(f"❌ Failed to setup model {model['name']}: {e}")
            print("   You can re-run setup.py later to resume downloads.")

def main():
    print("==================================================")
    print("🚀 ShimiStudio PC System Setup")
    print("==================================================")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    has_cuda = check_gpu()
    venv_python, venv_pip = setup_venv()
    install_requirements(venv_python, has_cuda)
    install_comfyui(venv_python)
    download_models()

    print("\n==================================================")
    print("🎉 ShimiStudio setup completed successfully!")
    print("To start the worker daemon, run:")
    print("  Windows: start.bat")
    print("  Linux/Mac: ./start.sh")
    print("==================================================")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected setup error: {e}")
        sys.exit(1)
