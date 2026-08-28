#!/usr/bin/env python3
"""
ShimiStudio - CivitAI Model Downloader
Downloads curated NSFW/realism LoRAs and Checkpoints from CivitAI.
"""

import argparse
import json
import os
import re
import struct
import sys
import time
import urllib.parse
from typing import Dict, List, Optional, Tuple

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error


# ANSI Color Codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


# Curated Collection of 9 CivitAI Models
MODEL_COLLECTION = [
    {
        "id": 1822984,
        "name": "Instagirl WAN 2.2",
        "type": "LoRA",
        "description": "realism for Wan 2.2"
    },
    {
        "id": 133005,
        "name": "Realistic Vision V6.0",
        "type": "Checkpoint",
        "description": "realistic images"
    },
    {
        "id": 102691,
        "name": "CyberRealistic",
        "type": "Checkpoint",
        "description": "photorealistic"
    },
    {
        "id": 121923,
        "name": "Realistic Vision V5.1",
        "type": "Checkpoint",
        "description": ""
    },
    {
        "id": 176470,
        "name": "Beautiful Realistic Asians",
        "type": "Checkpoint",
        "description": ""
    },
    {
        "id": 101055,
        "name": "MajicMix Realistic",
        "type": "Checkpoint",
        "description": ""
    },
    {
        "id": 74855,
        "name": "Photon",
        "type": "Checkpoint",
        "description": ""
    },
    {
        "id": 24620,
        "name": "Beautiful Art",
        "type": "LoRA",
        "description": ""
    },
    {
        "id": 278630,
        "name": "NSFW Wan 2.2",
        "type": "LoRA",
        "description": ""
    }
]


def format_size(size_bytes: int) -> str:
    """Formats byte size into human readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def parse_filename_from_headers(headers: Dict[str, str], fallback: str) -> str:
    """Extracts filename from Content-Disposition header if available."""
    content_disp = ""
    for k, v in headers.items():
        if k.lower() == "content-disposition":
            content_disp = v
            break

    if content_disp:
        match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', content_disp, re.IGNORECASE)
        if match:
            fname = urllib.parse.unquote(match.group(1)).strip()
            if fname:
                return os.path.basename(fname)
    return fallback


def verify_safetensors(file_path: str) -> Tuple[bool, str]:
    """
    Verifies that the downloaded file is a valid .safetensors file by checking magic bytes and header.
    Returns (is_valid, message).
    """
    try:
        if not os.path.exists(file_path):
            return False, "File does not exist"

        file_size = os.path.getsize(file_path)
        if file_size < 8:
            return False, "File size too small (< 8 bytes)"

        with open(file_path, "rb") as f:
            header_len_bytes = f.read(8)
            header_len = struct.unpack("<Q", header_len_bytes)[0]

            if header_len <= 0:
                return False, f"Invalid header length ({header_len})"
            if header_len > 100_000_000:
                return False, f"Header length unreasonably large ({header_len})"
            if header_len + 8 > file_size:
                return False, f"Header length ({header_len}) exceeds file size ({file_size})"

            header_json_bytes = f.read(header_len)
            if not header_json_bytes.strip().startswith(b'{'):
                return False, "Header does not start with JSON object ('{')"

            try:
                json_str = header_json_bytes.decode('utf-8')
                json.loads(json_str)
            except Exception as e:
                return False, f"Invalid JSON header: {e}"

        return True, "Valid .safetensors file"
    except Exception as e:
        return False, f"Error verifying file: {e}"


def print_model_collection():
    """Prints the curated model collection details without downloading."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}=== CivitAI Curated Model Collection ({len(MODEL_COLLECTION)} models) ==={Colors.RESET}\n")
    print(f"{'ID':<10} | {'Type':<10} | {'Name':<30} | {'Description'}")
    print("-" * 75)
    for model in MODEL_COLLECTION:
        desc = model['description'] if model['description'] else "-"
        type_color = Colors.CYAN if model['type'] == 'LoRA' else Colors.YELLOW
        print(f"{model['id']:<10} | {type_color}{model['type']:<10}{Colors.RESET} | {model['name']:<30} | {desc}")
    print(f"\n{Colors.BOLD}Total Models:{Colors.RESET} {len(MODEL_COLLECTION)}\n")


def print_token_instructions():
    """Prints instructions on how to obtain a CivitAI API token."""
    print(f"\n{Colors.RED}{Colors.BOLD}Error: CivitAI API token is required to download models.{Colors.RESET}\n")
    print(f"{Colors.YELLOW}{Colors.BOLD}How to get a CivitAI API Token:{Colors.RESET}")
    print(f"  1. Go to {Colors.CYAN}civitai.com → Settings → API Keys{Colors.RESET}")
    print(f"  2. Scroll down to 'API Keys' and click 'Add API Key'")
    print(f"  3. Give it a name and click 'Save'")
    print(f"  4. Copy your generated API key")
    print(f"\n{Colors.BOLD}Usage:{Colors.RESET}")
    print(f"  python {sys.argv[0]} --token YOUR_API_KEY\n")


def fetch_metadata(model_id: int, token: str) -> Optional[Dict]:
    """Fetches model version metadata from CivitAI API."""
    url = f"https://civitai.com/api/v1/model-versions/{model_id}"
    headers = {
        "User-Agent": "ShimiStudio/1.0",
        "Authorization": f"Bearer {token}"
    }
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        else:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    return json.loads(resp.read().decode('utf-8'))
    except Exception:
        pass
    return None


def detect_model_details(model_info: Dict, token: str) -> Tuple[str, str]:
    """
    Detects model type ('LoRA' or 'Checkpoint') and filename using CivitAI API metadata.
    Falls back to preset model_info values if API metadata is unavailable.
    """
    model_id = model_info["id"]
    preset_type = model_info["type"]
    preset_name = model_info["name"]

    detected_type = preset_type
    filename = None

    metadata = fetch_metadata(model_id, token)
    if metadata:
        meta_type = None
        if "model" in metadata and isinstance(metadata["model"], dict):
            meta_type = metadata["model"].get("type")
        if not meta_type:
            meta_type = metadata.get("type")

        if meta_type:
            meta_type_str = str(meta_type).upper()
            if any(k in meta_type_str for k in ["LORA", "LOCON", "DORA", "TEXTUALINVERSION"]):
                detected_type = "LoRA"
            elif "CHECKPOINT" in meta_type_str:
                detected_type = "Checkpoint"

        files = metadata.get("files", [])
        if isinstance(files, list):
            for f in files:
                if isinstance(f, dict):
                    fname = f.get("name")
                    if fname and fname.endswith(".safetensors"):
                        filename = fname
                        break
            if not filename and files and isinstance(files[0], dict):
                filename = files[0].get("name")

    if not filename:
        clean_name = re.sub(r'[^\w\s.-]', '', preset_name).strip().replace(" ", "_")
        filename = f"{clean_name}.safetensors"

    return detected_type, filename


def download_model(
    model_info: Dict,
    token: str,
    output_dir: str,
    checkpoint_dir: str
) -> Dict:
    """
    Downloads a single model.
    Download URL format: https://civitai.com/api/download/models/{ID}?token={TOKEN}
    """
    model_id = model_info["id"]
    name = model_info["name"]

    print(f"\n{Colors.HEADER}--------------------------------------------------{Colors.RESET}")
    print(f"{Colors.BOLD}Processing [{model_id}] {name}{Colors.RESET}")

    # Detect model type and target directory
    model_type, filename = detect_model_details(model_info, token)
    target_dir = output_dir if model_type == "LoRA" else checkpoint_dir
    os.makedirs(target_dir, exist_ok=True)

    dest_path = os.path.join(target_dir, filename)

    print(f"Detected Type: {Colors.CYAN if model_type == 'LoRA' else Colors.YELLOW}{model_type}{Colors.RESET}")
    print(f"Target Path  : {dest_path}")

    # Check if file already exists and is valid
    if os.path.exists(dest_path):
        is_valid, msg = verify_safetensors(dest_path)
        if is_valid:
            size_bytes = os.path.getsize(dest_path)
            print(f"{Colors.GREEN}✓ File already exists and passed safetensors verification ({format_size(size_bytes)}). Skipping.{Colors.RESET}")
            return {
                "id": model_id,
                "name": name,
                "type": model_type,
                "path": dest_path,
                "size": size_bytes,
                "status": "skipped"
            }
        else:
            print(f"{Colors.YELLOW}! Existing file is invalid ({msg}). Re-downloading...{Colors.RESET}")

    download_url = f"https://civitai.com/api/download/models/{model_id}?token={token}"
    temp_path = dest_path + ".tmp"

    try:
        if HAS_REQUESTS:
            response = requests.get(
                download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                stream=True,
                allow_redirects=True,
                timeout=30
            )
            status_code = response.status_code
            if status_code in (403, 404):
                print(f"{Colors.RED}Token invalid or model not found{Colors.RESET}")
                return {
                    "id": model_id,
                    "name": name,
                    "type": model_type,
                    "path": dest_path,
                    "size": 0,
                    "status": "failed",
                    "error": "Token invalid or model not found"
                }

            if status_code != 200:
                print(f"{Colors.RED}HTTP Error {status_code} for {name}{Colors.RESET}")
                return {
                    "id": model_id,
                    "name": name,
                    "type": model_type,
                    "path": dest_path,
                    "size": 0,
                    "status": "failed",
                    "error": f"HTTP {status_code}"
                }

            header_fname = parse_filename_from_headers(dict(response.headers), filename)
            if header_fname != filename:
                filename = header_fname
                dest_path = os.path.join(target_dir, filename)
                temp_path = dest_path + ".tmp"

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            start_time = time.time()
            chunk_size = 1024 * 1024

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        speed_str = f"{format_size(int(speed))}/s"

                        if total_size > 0:
                            percent = min(100.0, (downloaded / total_size) * 100)
                            bar_len = 30
                            filled = int(bar_len * downloaded // total_size)
                            bar = '=' * filled + ('>' if filled < bar_len else '')
                            bar = bar.ljust(bar_len)
                            sys.stdout.write(
                                f"\r{Colors.GREEN}[{bar}] {percent:5.1f}% ({format_size(downloaded)} / {format_size(total_size)}) @ {speed_str}{Colors.RESET}"
                            )
                        else:
                            sys.stdout.write(f"\r{Colors.GREEN}Downloaded {format_size(downloaded)} @ {speed_str}{Colors.RESET}")
                        sys.stdout.flush()

            sys.stdout.write("\n")

        else:
            req = urllib.request.Request(
                download_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                if status_code in (403, 404):
                    print(f"{Colors.RED}Token invalid or model not found{Colors.RESET}")
                    return {
                        "id": model_id,
                        "name": name,
                        "type": model_type,
                        "path": dest_path,
                        "size": 0,
                        "status": "failed",
                        "error": "Token invalid or model not found"
                    }

                header_fname = parse_filename_from_headers(dict(resp.headers), filename)
                if header_fname != filename:
                    filename = header_fname
                    dest_path = os.path.join(target_dir, filename)
                    temp_path = dest_path + ".tmp"

                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                start_time = time.time()
                chunk_size = 1024 * 1024

                with open(temp_path, "wb") as f:
                    while True:
                        chunk = resp.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        elapsed = time.time() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0
                        speed_str = f"{format_size(int(speed))}/s"

                        if total_size > 0:
                            percent = min(100.0, (downloaded / total_size) * 100)
                            bar_len = 30
                            filled = int(bar_len * downloaded // total_size)
                            bar = '=' * filled + ('>' if filled < bar_len else '')
                            bar = bar.ljust(bar_len)
                            sys.stdout.write(
                                f"\r{Colors.GREEN}[{bar}] {percent:5.1f}% ({format_size(downloaded)} / {format_size(total_size)}) @ {speed_str}{Colors.RESET}"
                            )
                        else:
                            sys.stdout.write(f"\r{Colors.GREEN}Downloaded {format_size(downloaded)} @ {speed_str}{Colors.RESET}")
                        sys.stdout.flush()

            sys.stdout.write("\n")

        # Verify download integrity
        print("Verifying download integrity...")
        is_valid, err_msg = verify_safetensors(temp_path)
        if not is_valid:
            print(f"{Colors.RED}Verification failed: {err_msg}{Colors.RESET}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return {
                "id": model_id,
                "name": name,
                "type": model_type,
                "path": dest_path,
                "size": 0,
                "status": "failed",
                "error": f"Verification failed: {err_msg}"
            }

        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(temp_path, dest_path)

        final_size = os.path.getsize(dest_path)
        print(f"{Colors.GREEN}✓ Download verified & saved successfully! ({format_size(final_size)}){Colors.RESET}")
        return {
            "id": model_id,
            "name": name,
            "type": model_type,
            "path": dest_path,
            "size": final_size,
            "status": "downloaded"
        }

    except Exception as e:
        err_str = str(e)
        if "403" in err_str or "404" in err_str:
            print(f"{Colors.RED}Token invalid or model not found{Colors.RESET}")
            err_msg = "Token invalid or model not found"
        else:
            print(f"{Colors.RED}Download error: {e}{Colors.RESET}")
            err_msg = str(e)

        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

        return {
            "id": model_id,
            "name": name,
            "type": model_type,
            "path": dest_path,
            "size": 0,
            "status": "failed",
            "error": err_msg
        }


def print_summary(results: List[Dict]):
    """Prints a summary report of all processed models."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}==================================================")
    print("                DOWNLOAD SUMMARY                  ")
    print(f"=================================================={Colors.RESET}\n")

    downloaded = [r for r in results if r["status"] == "downloaded"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"] == "failed"]

    if downloaded:
        print(f"{Colors.GREEN}{Colors.BOLD}Downloaded Models ({len(downloaded)}):{Colors.RESET}")
        for item in downloaded:
            print(f"  • {item['name']} ({item['type']})")
            print(f"    Path: {item['path']}")
            print(f"    Size: {format_size(item['size'])}\n")

    if skipped:
        print(f"{Colors.YELLOW}{Colors.BOLD}Skipped / Already Present ({len(skipped)}):{Colors.RESET}")
        for item in skipped:
            print(f"  • {item['name']} ({item['type']})")
            print(f"    Path: {item['path']}")
            print(f"    Size: {format_size(item['size'])}\n")

    if failed:
        print(f"{Colors.RED}{Colors.BOLD}Failed Downloads ({len(failed)}):{Colors.RESET}")
        for item in failed:
            print(f"  • {item['name']} (ID: {item['id']})")
            print(f"    Reason: {item.get('error', 'Unknown error')}\n")

    total_downloaded_size = sum(r["size"] for r in downloaded)
    total_existing_size = sum(r["size"] for r in skipped)
    total_size = total_downloaded_size + total_existing_size

    print(f"{Colors.BOLD}--------------------------------------------------{Colors.RESET}")
    print(f"Successfully downloaded : {len(downloaded)} files ({format_size(total_downloaded_size)})")
    print(f"Skipped / Pre-existing  : {len(skipped)} files ({format_size(total_existing_size)})")
    print(f"Failed                  : {len(failed)} files")
    print(f"Total Collection Size   : {format_size(total_size)}")
    print(f"{Colors.HEADER}=================================================={Colors.RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download NSFW and realism LoRAs / Checkpoints from CivitAI for ShimiStudio."
    )
    parser.add_argument(
        "--token",
        "-t",
        type=str,
        help="CivitAI API Token (required for downloads)"
    )
    parser.add_argument(
        "--output-dir",
        default="./ComfyUI/models/loras",
        help="Output directory for LoRAs (default: ./ComfyUI/models/loras)"
    )
    parser.add_argument(
        "--checkpoint-dir",
        default="./ComfyUI/models/checkpoints",
        help="Output directory for Checkpoints (default: ./ComfyUI/models/checkpoints)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Show curated model collection without downloading"
    )

    args = parser.parse_args()

    if args.list:
        print_model_collection()
        return

    if not args.token:
        print_token_instructions()
        sys.exit(1)

    print(f"\n{Colors.HEADER}{Colors.BOLD}Starting CivitAI Model Downloader for ShimiStudio{Colors.RESET}")
    print(f"LoRA Target Directory       : {args.output_dir}")
    print(f"Checkpoint Target Directory : {args.checkpoint_dir}")
    print(f"Models to process           : {len(MODEL_COLLECTION)}")

    results = []
    for i, model_info in enumerate(MODEL_COLLECTION):
        res = download_model(
            model_info=model_info,
            token=args.token,
            output_dir=args.output_dir,
            checkpoint_dir=args.checkpoint_dir
        )
        results.append(res)

        # Sleep 2s between downloads
        if i < len(MODEL_COLLECTION) - 1:
            time.sleep(2)

    print_summary(results)


if __name__ == "__main__":
    main()
