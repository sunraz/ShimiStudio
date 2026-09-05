#!/usr/bin/env python3
"""
ShimiStudio — LoRA Downloader
מוריד 10 LoRAs חזקים ל-CyberRealistic (SD 1.5) מ-CivitAI
"""
import requests, os, sys, time

import os
API_KEY = os.environ.get("CIVITAI_API_KEY", "")
LORA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ComfyUI", "models", "loras")
os.makedirs(LORA_DIR, exist_ok=True)

LORAS = [
    ("add_detail.safetensors", "https://civitai.com/api/download/models/62833", "Detail Tweaker LoRA (578K dl)"),
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

def download(filename, url, desc):
    dest = os.path.join(LORA_DIR, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 10000:
        print(f"  [SKIP] {filename} already exists ({os.path.getsize(dest)//1024}KB)")
        return True
    
    print(f"  [DOWN] {filename} — {desc}")
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"}, 
                        stream=True, allow_redirects=True, timeout=300)
        if r.status_code != 200:
            print(f"  [FAIL] HTTP {r.status_code}")
            return False
        
        total = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
                total += len(chunk)
        
        size_mb = total / (1024*1024)
        print(f"  [OK]   {filename} — {size_mb:.1f}MB")
        return True
    except Exception as e:
        print(f"  [FAIL] {e}")
        if os.path.exists(dest):
            os.remove(dest)
        return False

print("=" * 50)
print("  ShimiStudio — LoRA Downloader")
print("=" * 50)
print(f"  Target: {LORA_DIR}")
print(f"  LoRAs to download: {len(LORAS)}")
print()

success = 0
for i, (fname, url, desc) in enumerate(LORAS, 1):
    print(f"  [{i}/{len(LORAS)}]")
    if download(fname, url, desc):
        success += 1
    time.sleep(1)  # rate limit

print()
print(f"  Done: {success}/{len(LORAS)} LoRAs downloaded")
print(f"  Location: {LORA_DIR}")

# List all LoRAs
print("\n  All LoRAs in folder:")
for f in os.listdir(LORA_DIR):
    size = os.path.getsize(os.path.join(LORA_DIR, f))
    print(f"    {f} — {size//1024}KB")
