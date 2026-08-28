#!/usr/bin/env python3
"""
ShimiStudio Pro Pipeline Upgrade Script
----------------------------------------
Installs all Pro pipeline components for ShimiStudio on a PC:
1. ComfyUI Custom Nodes (git clone into ComfyUI/custom_nodes/):
   - ComfyUI-ReActor (face swap)
   - ComfyUI-PuLID-Flux (face consistency)
   - ComfyUI-XTTS (voice cloning)
   - ComfyUI-LatentSyncWrapper (lip sync)
   - ComfyUI-wav2lip (lip sync)
   - ComfyUI-DWPose (pose detection)
   - ComfyUI-ControlNet-Aux
   - ComfyUI-LivePortrait

2. Models (downloaded to target ComfyUI directories):
   - PuLID model -> ComfyUI/models/pulid/
   - ReActor inswapper -> ComfyUI/models/insightface/
   - InsightFace buffalo_l -> ComfyUI/models/insightface/ (unzipped)
   - GFPGAN -> ComfyUI/models/gfpgan/
   - CodeFormer -> ComfyUI/models/codeformer/
   - XTTS v2 -> ComfyUI/models/tts/
   - LatentSync -> ComfyUI/models/latentsync/
   - Wav2Lip -> ComfyUI/models/wav2lip/
   - DWPose yolox -> ComfyUI/models/dwpose/
   - DWPose dwpose -> ComfyUI/models/dwpose/
   - ControlNet OpenPose -> ComfyUI/models/controlnet/

3. PIP Dependencies:
   - onnxruntime, insightface, gfpgan, basicsr, facexlib, yapf, numba

Features:
- Command-line arguments via argparse (--comfyui-dir, --skip-nodes, --skip-models, --dry-run, --skip-pip)
- Color-coded terminal output (ANSI escape codes)
- Download progress indicators with speed & size formatting
- VRAM / GPU detection (PyTorch or nvidia-smi fallback)
- Download verification with file size check
- Non-blocking error handling (logs warnings and continues on error)
- Complete summary output at the end
"""

import os
import sys
import time
import argparse
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Tuple

# --- ANSI Formatting & Color Codes ---
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
MAGENTA = '\033[0;35m'
CYAN = '\033[0;36m'
BOLD = '\033[1m'
NC = '\033[0m'  # No Color

# Enable ANSI colors on Windows terminal if supported
if os.name == 'nt':
    os.system('color')


def log_banner():
    print(f"{CYAN}{BOLD}")
    print("====================================================================")
    print("          🚀 ShimiStudio Pro Pipeline Upgrade Script                ")
    print("====================================================================")
    print(f"{NC}")


def log_step(title: str):
    print(f"\n{MAGENTA}{BOLD}=== {title} ==={NC}")


def log_info(msg: str):
    print(f"{CYAN}[INFO]{NC} {msg}")


def log_success(msg: str):
    print(f"{GREEN}[SUCCESS]{NC} {msg}")


def log_warn(msg: str):
    print(f"{YELLOW}[WARN]{NC} {msg}")


def log_error(msg: str):
    print(f"{RED}[ERROR]{NC} {msg}")


# --- CUSTOM NODES DEFINITIONS ---
CUSTOM_NODES = [
    {
        "name": "ComfyUI-ReActor",
        "desc": "face swap",
        "url": "https://github.com/Gourieff/ComfyUI-ReActor.git",
        "folder": "ComfyUI-ReActor",
    },
    {
        "name": "ComfyUI-PuLID-Flux",
        "desc": "face consistency",
        "url": "https://github.com/ltdrdata/ComfyUI-PuLID-Flux.git",
        "folder": "ComfyUI-PuLID-Flux",
    },
    {
        "name": "ComfyUI-XTTS",
        "desc": "voice cloning",
        "url": "https://github.com/MadeByAiden/ComfyUI-XTTS.git",
        "folder": "ComfyUI-XTTS",
    },
    {
        "name": "ComfyUI-LatentSyncWrapper",
        "desc": "lip sync",
        "url": "https://github.com/kijai/ComfyUI-LatentSyncWrapper.git",
        "folder": "ComfyUI-LatentSyncWrapper",
    },
    {
        "name": "ComfyUI-wav2lip",
        "desc": "lip sync",
        "url": "https://github.com/kijai/ComfyUI-wav2lip.git",
        "folder": "ComfyUI-wav2lip",
    },
    {
        "name": "ComfyUI-DWPose",
        "desc": "pose detection",
        "url": "https://github.com/chflame163/ComfyUI-DWPose.git",
        "folder": "ComfyUI-DWPose",
    },
    {
        "name": "ComfyUI-ControlNet-Aux",
        "desc": "controlnet aux",
        "url": "https://github.com/Fannovel16/comfyui_controlnet_aux.git",
        "folder": "comfyui_controlnet_aux",
    },
    {
        "name": "ComfyUI-LivePortrait",
        "desc": "live portrait",
        "url": "https://github.com/kijai/ComfyUI-LivePortrait.git",
        "folder": "ComfyUI-LivePortrait",
    },
]

# --- MODEL DEFINITIONS ---
MODELS = [
    {
        "name": "PuLID model",
        "url": "https://huggingface.co/DepthAnything/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors",
        "rel_dir": "models/pulid",
        "filename": "pulid_flux_v0.9.1.safetensors",
    },
    {
        "name": "ReActor inswapper",
        "url": "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/inswapper_128.onnx",
        "rel_dir": "models/insightface",
        "filename": "inswapper_128.onnx",
    },
    {
        "name": "InsightFace buffalo_l",
        "url": "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/buffalo_l.zip",
        "rel_dir": "models/insightface",
        "filename": "buffalo_l.zip",
        "unzip": True,
    },
    {
        "name": "GFPGAN",
        "url": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth",
        "rel_dir": "models/gfpgan",
        "filename": "GFPGANv1.4.pth",
    },
    {
        "name": "CodeFormer",
        "url": "https://huggingface.co/datasets/Gourieff/ReActor/resolve/main/models/codeformer.pth",
        "rel_dir": "models/codeformer",
        "filename": "codeformer.pth",
    },
    {
        "name": "XTTS v2",
        "url": "https://huggingface.co/coqui/XTTS-v2/resolve/main/model.pth",
        "rel_dir": "models/tts",
        "filename": "model.pth",
    },
    {
        "name": "LatentSync",
        "url": "https://huggingface.co/jhliu/latentsync/resolve/main/latentsync_unet.pth",
        "rel_dir": "models/latentsync",
        "filename": "latentsync_unet.pth",
    },
    {
        "name": "Wav2Lip",
        "url": "https://huggingface.co/numz/wav2lip-uhq/resolve/main/wav2lip.pth",
        "rel_dir": "models/wav2lip",
        "filename": "wav2lip.pth",
    },
    {
        "name": "DWPose yolox",
        "url": "https://huggingface.co/yzd-v/DWPose/resolve/main/yolox_l.onnx",
        "rel_dir": "models/dwpose",
        "filename": "yolox_l.onnx",
    },
    {
        "name": "DWPose dwpose",
        "url": "https://huggingface.co/yzd-v/DWPose/resolve/main/dw-ll_ucoco_384.onnx",
        "rel_dir": "models/dwpose",
        "filename": "dw-ll_ucoco_384.onnx",
    },
    {
        "name": "ControlNet OpenPose",
        "url": "https://huggingface.co/thibaud/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors",
        "rel_dir": "models/controlnet",
        "filename": "diffusion_pytorch_model.safetensors",
    },
]

# --- PIP PACKAGES ---
PIP_PACKAGES = [
    "onnxruntime",
    "insightface",
    "gfpgan",
    "basicsr",
    "facexlib",
    "yapf",
    "numba",
]


def detect_vram() -> List[str]:
    """Detect GPU / VRAM capabilities using PyTorch or fallback to nvidia-smi."""
    vram_info = []

    # 1. Try PyTorch
    try:
        import torch
        if torch.cuda.is_available():
            device_count = torch.cuda.device_count()
            for i in range(device_count):
                device_name = torch.cuda.get_device_name(i)
                props = torch.cuda.get_device_properties(i)
                total_mem_gb = props.total_memory / (1024 ** 3)
                vram_info.append(f"GPU {i}: {device_name} ({total_mem_gb:.2f} GB VRAM) [via PyTorch]")
            return vram_info
    except ImportError:
        pass
    except Exception as e:
        vram_info.append(f"PyTorch CUDA detection error: {e}")

    # 2. Fallback to nvidia-smi
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        lines = res.stdout.strip().splitlines()
        for idx, line in enumerate(lines):
            if line:
                parts = [p.strip() for p in line.split(",")]
                name = parts[0] if len(parts) > 0 else "Unknown GPU"
                total_mb = parts[1] if len(parts) > 1 else "0"
                try:
                    total_gb = float(total_mb) / 1024.0
                    vram_info.append(f"GPU {idx}: {name} ({total_gb:.2f} GB VRAM) [via nvidia-smi]")
                except ValueError:
                    vram_info.append(f"GPU {idx}: {name} ({total_mb} MB VRAM) [via nvidia-smi]")
        if vram_info:
            return vram_info
    except Exception:
        pass

    return ["No CUDA GPU detected (CPU mode or GPU drivers not found)"]


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def download_file(url: str, dest_path: Path, dry_run: bool = False) -> bool:
    """Download file with progress bar indicator and verification."""
    if dry_run:
        log_info(f"[DRY-RUN] Would download: {url}")
        log_info(f"[DRY-RUN] Destination: {dest_path}")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists() and dest_path.stat().st_size > 0:
        log_info(f"File already exists: {dest_path.name} ({format_size(dest_path.stat().st_size)}). Skipping download.")
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    log_info(f"Downloading {dest_path.name} from {url}...")

    start_time = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ShimiStudioUpgrade/1.0"}
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 1024 * 1024  # 1MB chunk size

            with open(temp_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    elapsed = time.time() - start_time
                    speed = downloaded / elapsed if elapsed > 0 else 0

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        bar_len = 20
                        filled = int(bar_len * downloaded / total_size)
                        bar = "=" * filled + (">" if filled < bar_len else "")
                        bar = bar.ljust(bar_len)
                        sys.stdout.write(
                            f"\r{CYAN}[DOWNLOADING]{NC} [{bar}] {percent:5.1f}% "
                            f"({format_size(downloaded)} / {format_size(total_size)}) "
                            f"{format_size(int(speed))}/s"
                        )
                    else:
                        sys.stdout.write(
                            f"\r{CYAN}[DOWNLOADING]{NC} {format_size(downloaded)} "
                            f"{format_size(int(speed))}/s"
                        )
                    sys.stdout.flush()

        sys.stdout.write("\n")
        temp_path.replace(dest_path)

        # File size verification
        if not dest_path.exists() or dest_path.stat().st_size == 0:
            log_warn(f"Verification failed: Downloaded file {dest_path.name} is empty.")
            if dest_path.exists():
                dest_path.unlink()
            return False

        log_success(f"Downloaded {dest_path.name} ({format_size(dest_path.stat().st_size)}) successfully.")
        return True

    except Exception as e:
        sys.stdout.write("\n")
        log_warn(f"Failed to download {dest_path.name}: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return False


def extract_buffalo_zip(zip_path: Path, insightface_dir: Path, dry_run: bool = False) -> bool:
    """Extract buffalo_l.zip into insightface directory."""
    if dry_run:
        log_info(f"[DRY-RUN] Would extract {zip_path.name} into {insightface_dir}")
        return True

    if not zip_path.exists():
        log_warn(f"Cannot extract {zip_path.name}: Archive file missing.")
        return False

    try:
        log_info(f"Extracting {zip_path.name} into {insightface_dir}...")
        target_subdir1 = insightface_dir / "models" / "buffalo_l"
        target_subdir2 = insightface_dir / "buffalo_l"
        target_subdir1.mkdir(parents=True, exist_ok=True)
        target_subdir2.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(insightface_dir)
            zip_ref.extractall(target_subdir1)
            zip_ref.extractall(target_subdir2)

        log_success(f"Extracted {zip_path.name} successfully.")
        return True
    except Exception as e:
        log_warn(f"Failed to extract {zip_path.name}: {e}")
        return False


def install_custom_nodes(nodes: List[Dict[str, str]], comfyui_dir: Path, dry_run: bool = False) -> Dict[str, str]:
    """Clone or update custom nodes in ComfyUI/custom_nodes."""
    results = {}
    custom_nodes_dir = comfyui_dir / "custom_nodes"

    log_step("Installing ComfyUI Custom Nodes")

    for node in nodes:
        name = node["name"]
        url = node["url"]
        folder = node["folder"]
        target_dir = custom_nodes_dir / folder

        log_info(f"Processing node: {BOLD}{name}{NC} ({node['desc']})")

        if dry_run:
            log_info(f"[DRY-RUN] Would clone {url} -> {target_dir}")
            results[name] = "SUCCESS (Dry-Run)"
            continue

        target_dir.parent.mkdir(parents=True, exist_ok=True)

        if target_dir.exists() and (target_dir / ".git").exists():
            log_info(f"Repository {folder} already exists. Pulling latest...")
            try:
                res = subprocess.run(
                    ["git", "-C", str(target_dir), "pull"],
                    capture_output=True, text=True, timeout=60
                )
                if res.returncode == 0:
                    log_success(f"Updated {name} successfully.")
                    results[name] = "SUCCESS (Updated)"
                else:
                    log_warn(f"git pull warning for {name}: {res.stderr.strip()}")
                    results[name] = "SUCCESS (Already Exists)"
            except Exception as e:
                log_warn(f"Could not pull latest for {name}: {e}")
                results[name] = "SUCCESS (Already Exists)"
        else:
            log_info(f"Cloning {url} into {target_dir}...")
            try:
                res = subprocess.run(
                    ["git", "clone", url, str(target_dir)],
                    capture_output=True, text=True, timeout=300
                )
                if res.returncode == 0:
                    log_success(f"Cloned {name} successfully.")
                    results[name] = "SUCCESS"
                else:
                    log_warn(f"git clone failed for {name}: {res.stderr.strip()}")
                    results[name] = "FAILED"
            except Exception as e:
                log_warn(f"Exception while cloning {name}: {e}")
                results[name] = "FAILED"

    return results


def install_models(models: List[Dict[str, str]], comfyui_dir: Path, dry_run: bool = False) -> Dict[str, str]:
    """Download and verify model files for ComfyUI."""
    results = {}

    log_step("Downloading Pipeline Models")

    for m in models:
        name = m["name"]
        url = m["url"]
        rel_dir = m["rel_dir"]
        filename = m["filename"]
        target_dir = comfyui_dir / rel_dir
        dest_path = target_dir / filename

        log_info(f"Processing model: {BOLD}{name}{NC} -> {rel_dir}/{filename}")

        success = download_file(url, dest_path, dry_run=dry_run)

        if success and m.get("unzip", False):
            unzip_ok = extract_buffalo_zip(dest_path, target_dir, dry_run=dry_run)
            if not unzip_ok:
                success = False

        if success:
            results[name] = "SUCCESS"
        else:
            results[name] = "FAILED"

    return results


def install_pip_packages(packages: List[str], dry_run: bool = False) -> Dict[str, str]:
    """Install required python packages via pip."""
    results = {}

    log_step("Installing Python Dependencies via PIP")

    for pkg in packages:
        log_info(f"Installing package: {BOLD}{pkg}{NC}...")

        if dry_run:
            log_info(f"[DRY-RUN] Would execute: {sys.executable} -m pip install {pkg}")
            results[pkg] = "SUCCESS (Dry-Run)"
            continue

        try:
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg],
                capture_output=True, text=True, timeout=300
            )
            if res.returncode == 0:
                log_success(f"Installed {pkg} successfully.")
                results[pkg] = "SUCCESS"
            else:
                log_warn(f"pip install {pkg} failed: {res.stderr.strip()}")
                results[pkg] = "FAILED"
        except Exception as e:
            log_warn(f"Exception during pip install of {pkg}: {e}")
            results[pkg] = "FAILED"

    return results


def print_summary(
    vram_info: List[str],
    node_results: Dict[str, str],
    model_results: Dict[str, str],
    pip_results: Dict[str, str],
    elapsed_sec: float
):
    """Print complete color-coded summary report."""
    print(f"\n{CYAN}{BOLD}")
    print("====================================================================")
    print("                📊 Upgrade Pipeline Summary Report                 ")
    print("====================================================================")
    print(f"{NC}")

    print(f"{BOLD}GPU / VRAM Detection:{NC}")
    for info in vram_info:
        print(f"  • {GREEN}{info}{NC}")

    def render_section(title: str, results: Dict[str, str]):
        if not results:
            print(f"\n{BOLD}{title}:{NC} [Skipped / None]")
            return

        succeeded = sum(1 for status in results.values() if "SUCCESS" in status)
        total = len(results)
        print(f"\n{BOLD}{title} ({succeeded}/{total} succeeded):{NC}")
        for item, status in results.items():
            if "SUCCESS" in status:
                color = GREEN
                icon = "✓"
            else:
                color = RED
                icon = "✗"
            print(f"  [{color}{icon}{NC}] {item.ljust(30)} -> {color}{status}{NC}")

    render_section("Custom Nodes", node_results)
    render_section("Models", model_results)
    render_section("Pip Packages", pip_results)

    total_tasks = len(node_results) + len(model_results) + len(pip_results)
    total_success = (
        sum(1 for s in node_results.values() if "SUCCESS" in s) +
        sum(1 for s in model_results.values() if "SUCCESS" in s) +
        sum(1 for s in pip_results.values() if "SUCCESS" in s)
    )

    print(f"\n{BOLD}Overall Status:{NC}")
    if total_success == total_tasks and total_tasks > 0:
        print(f"  {GREEN}{BOLD}ALL COMPONENTS INSTALLED SUCCESSFULLY! ({total_success}/{total_tasks}){NC}")
    elif total_success > 0:
        print(f"  {YELLOW}{BOLD}COMPLETED WITH WARNINGS ({total_success}/{total_tasks} succeeded){NC}")
    else:
        print(f"  {RED}{BOLD}UPGRADE FAILED OR ALL SKIPPED ({total_success}/{total_tasks} succeeded){NC}")

    print(f"\n{CYAN}Total Time Elapsed: {elapsed_sec:.2f} seconds{NC}")
    print(f"{CYAN}{BOLD}===================================================================={NC}\n")


def main():
    parser = argparse.ArgumentParser(
        description="ShimiStudio Pro Pipeline Upgrade Script - Installs custom nodes, models, and dependencies."
    )
    parser.add_argument(
        "--comfyui-dir",
        type=str,
        default="./ComfyUI",
        help="Path to ComfyUI directory (default: ./ComfyUI)"
    )
    parser.add_argument(
        "--skip-nodes",
        action="store_true",
        help="Skip cloning ComfyUI custom nodes"
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Skip downloading model files"
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip installing python dependencies via pip"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate actions without downloading or modifying disk"
    )

    args = parser.parse_args()

    log_banner()
    start_time = time.time()

    comfyui_path = Path(args.comfyui_dir).resolve()
    log_info(f"Target ComfyUI directory: {comfyui_path}")
    if args.dry_run:
        log_warn("DRY-RUN MODE ENABLED - No changes will be written to disk.")

    log_step("Hardware & VRAM Detection")
    vram_info = detect_vram()
    for line in vram_info:
        log_info(line)

    node_results = {}
    model_results = {}
    pip_results = {}

    # 1. Custom Nodes
    if args.skip_nodes:
        log_info("Skipping custom nodes (--skip-nodes flag set).")
    else:
        node_results = install_custom_nodes(CUSTOM_NODES, comfyui_path, dry_run=args.dry_run)

    # 2. Models
    if args.skip_models:
        log_info("Skipping models (--skip-models flag set).")
    else:
        model_results = install_models(MODELS, comfyui_path, dry_run=args.dry_run)

    # 3. Pip Packages
    if args.skip_pip:
        log_info("Skipping pip dependencies (--skip-pip flag set).")
    else:
        pip_results = install_pip_packages(PIP_PACKAGES, dry_run=args.dry_run)

    elapsed = time.time() - start_time
    print_summary(vram_info, node_results, model_results, pip_results, elapsed)


if __name__ == "__main__":
    main()
