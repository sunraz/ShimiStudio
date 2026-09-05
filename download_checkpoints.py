#!/usr/bin/env python3
"""
ShimiStudio — NSFW Checkpoints Downloader
מוריד checkpoints חזקות ל-NSFW (SD 1.5, ללא צנזורה)
כל מודל ~2GB — מתאים ל-Quadro P2200 (5GB VRAM)
"""
import requests
import os
import sys

import os
API_KEY = os.environ.get("CIVITAI_API_KEY", "")
BASE_URL = "https://civitai.com/api/download/models"

# תיקיית יעד
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_DIR = os.path.join(SCRIPT_DIR, "checkpoints")

# המודלים החזקים ביותר ל-NSFW (SD 1.5)
# (filename, model_id, version_id, file_id, size_mb, description)
CHECKPOINTS = [
    # === 1. URPM — מלך ה-NSFW הפוטוריאליסטי ===
    (
        "uberRealisticPornMerge_v23Final.safetensors",
        2661, 915814, 1155723, 2033,
        "URPM v23 — פוטוריאליסטי קשה (hardcore porn, photorealistic) — הכי חזק ל-NSFW"
    ),
    # === 2. Juggernaut — פוטוריאליסטי עם עירום ===
    (
        "juggernaut_reborn.safetensors",
        46422, 274039, 214158, 2033,
        "Juggernaut Reborn — פוטוריאליסטי פרימיום, תומך עירום (nude), דמויות מציאותיות"
    ),
    # === 3. Realistic Vision V6 — פוטוריאליסטי ללא צנזורה ===
    (
        "realisticVisionV60B1_v51HyperVAE.safetensors",
        4201, 501240, 418901, 2033,
        "Realistic Vision V6.0 — המציאותי ביותר, ללא צנזורה, מבנה גוף אנטומי מדויק"
    ),
    # === 4. epiCRealism — טבעי ומציאותי ===
    (
        "epicrealism_naturalSinRC1VAE.safetensors",
        25694, 143906, 106430, 2033,
        "epiCRealism Natural — פוטוריאליסטי טבעי, פורטרטים וגוף מלא מציאותיים"
    ),
    # === 5. majicMIX realistic — אסיאתי ריאליסטי ===
    (
        "majicmixRealistic_v7.safetensors",
        43331, 176425, 134792, 2033,
        "majicMIX Realistic v7 — מציאותי עם דגש אסיאתי, פופולרי מאוד ל-NSFW"
    ),
    # === 6. Beautiful Realistic Asians — נשים יפניות ===
    (
        "beautifulRealistic_v7.safetensors",
        25494, 177164, 135410, 2033,
        "Beautiful Realistic Asians v7 — נשים אסיאתיות פוטוריאליסטיות"
    ),
    # === 7. Photon — סקסי ומציאותי ===
    (
        "photon_v1.safetensors",
        84728, 90072, 61934, 2033,
        "Photon — פוטוריאליסטי, סקסי, נשים, בגדים/ללא בגדים"
    ),
    # === 8. epiCPhotoGasm — נשים מציאותיות ===
    (
        "epicphotogasm_ultimateFidelity.safetensors",
        132632, 429454, 350416, 2033,
        "epiCPhotoGasm — פוטוריאליסטי, נשים, נאמנות תמונה אולטימטיבית"
    ),
]

def download_file(url, filepath, name, size_mb, desc):
    """מוריד קובץ עם דיווח התקדמות"""
    if os.path.exists(filepath):
        existing_size = os.path.getsize(filepath)
        if existing_size > 0 and existing_size >= size_mb * 1024 * 1024 * 0.95:
            print(f"  [SKIP] {name} — כבר קיים ({existing_size//1024//1024}MB)")
            return True
    
    headers = {"Authorization": f"Bearer {API_KEY}"}
    print(f"\n  [{desc}]")
    print(f"  [DOWNLOAD] {name} (~{size_mb}MB)...")
    
    try:
        r = requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=30)
        if r.status_code != 200:
            print(f"  [ERROR] HTTP {r.status_code}: {r.text[:200]}")
            return False
        
        total = 0
        with open(filepath, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
                    total += len(chunk)
                    mb = total // 1024 // 1024
                    if mb > 0 and mb % 200 == 0:
                        pct = (total / (size_mb * 1024 * 1024)) * 100
                        print(f"    {mb}MB ({pct:.0f}%)...", flush=True)
        
        print(f"  [OK] {name} — {total//1024//1024}MB")
        return True
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return False

def main():
    print("=" * 60)
    print("  ShimiStudio — NSFW Checkpoints Downloader")
    print("  סה\"כ להורדה: 8 מודלים × ~2GB = ~16GB")
    print("=" * 60)
    
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    
    print("\nרשימת מודלים:")
    for i, (name, _, _, _, size_mb, desc) in enumerate(CHECKPOINTS, 1):
        print(f"  {i}. {desc}")
        print(f"     קובץ: {name} (~{size_mb}MB)")
    
    print(f"\nתיקיית יעד: {CHECKPOINT_DIR}")
    print()
    
    # אפשרות לבחור — כל המודלים או רק חלק
    if len(sys.argv) > 1:
        # פרמטרים משורת הפקודה — מספרי מודלים
        selected = []
        for arg in sys.argv[1:]:
            try:
                idx = int(arg) - 1
                if 0 <= idx < len(CHECKPOINTS):
                    selected.append(CHECKPOINTS[idx])
            except ValueError:
                pass
        if selected:
            print(f"מוריד {len(selected)} מודלים נבחרים")
            to_download = selected
        else:
            to_download = CHECKPOINTS
    else:
        to_download = CHECKPOINTS
    
    total_ok = 0
    total_fail = 0
    
    for name, model_id, version_id, file_id, size_mb, desc in to_download:
        url = f"{BASE_URL}/{model_id}?fileId={file_id}"
        filepath = os.path.join(CHECKPOINT_DIR, name)
        if download_file(url, filepath, name, size_mb, desc):
            total_ok += 1
        else:
            total_fail += 1
    
    print("\n" + "=" * 60)
    print(f"  הורדה הושלמה: {total_ok} הצליחו, {total_fail} נכשלו")
    print("=" * 60)
    
    # רשימת קבצים
    print("\nקבצי Checkpoints:")
    if os.path.exists(CHECKPOINT_DIR):
        for f in sorted(os.listdir(CHECKPOINT_DIR)):
            sz = os.path.getsize(os.path.join(CHECKPOINT_DIR, f)) // 1024 // 1024
            print(f"  {f} ({sz}MB)")

if __name__ == "__main__":
    main()
