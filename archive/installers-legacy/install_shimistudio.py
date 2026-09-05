#!/usr/bin/env python3
"""
ShimiStudio — מתקין אוטומטי (Python)
====================================
הפעלה: python install_shimistudio.py

הסקריפט הזה:
1. מתקין Python (אם חסר) דרך ה-PS1
2. מוריד ומתקין את כל מה שצריך
3. מפעיל את ה-Worker
"""

import os
import sys
import subprocess
import urllib.request
import json
import time
from pathlib import Path

# ═══ הגדרות ═══
INSTALL_DIR = Path.home() / "ShimiStudio"
SERVER_URL = "https://solas-6a095a77.base44.app/functions/shimiStudioAPI"
APP_ID = "6a901f55a4d9a9b76a095a77"
WORKER_TOKEN = "shimi_worker_auto"
GITHUB_RAW = "https://raw.githubusercontent.com/sunraz/ShimiStudio/main"

WORKER_FILES = [
    "worker.py", "config.json", "base44_client.py", "comfyui_client.py",
    "workflows.py", "config.py", "style_library.py", "free_api.py",
    "batch_generator.py", "realtime_avatar.py", "lora_trainer.py",
    "pipeline.py", "civitai_models.py", "studio.py",
    "requirements.txt",
]

CUSTOM_NODES = [
    ("ComfyUI_IPAdapter_plus", "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git"),
    ("ComfyUI_ReActor", "https://github.com/Gourieff/ComfyUI_ReActor.git"),
    ("ComfyUI-AnimateDiff-Evolved", "https://github.com/kijai/ComfyUI-AnimateDiff-Evolved.git"),
    ("comfyui_wan", "https://github.com/kijai/ComfyUI-Wan.git"),
]

MODELS = [
    ("checkpoints/flux1-dev-fp8.safetensors", "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"),
    ("diffusion_models/wan2.1-t2v-1.3B.safetensors", "https://huggingface.co/Comfy-Org/Wan_2.1/resolve/main/wan2.1-t2v-1.3B.safetensors"),
    ("checkpoints/ltx-video-2b.safetensors", "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b.safetensors"),
]

def run(cmd, **kwargs):
    """הפעלת פקודה עם טיפול שגיאות"""
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=kwargs.pop('timeout', 300), **kwargs)
    except Exception as e:
        class FakeResult:
            returncode = -1
            stdout = ""
            stderr = str(e)
        return FakeResult()

def download(url, dest):
    """הורדת קובץ עם progress"""
    try:
        dest = Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=600) as response:
            total = int(response.headers.get('Content-Length', 0))
            downloaded = 0
            with open(dest, 'wb') as f:
                while True:
                    chunk = response.read(1024 * 1024)  # 1MB
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = (downloaded / total) * 100
                        print(f"\r  {downloaded/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB ({pct:.0f}%)", end='', flush=True)
            print()
        return True
    except Exception as e:
        print(f"\n  שגיאה: {e}")
        return False

def step(n, total, name):
    print(f"\n[{n}/{total}] {name}")
    print("-" * 40)

def ok(msg="OK"):
    print(f"  ✓ {msg}")

def fail(msg):
    print(f"  ✗ {msg}")

def info(msg):
    print(f"  → {msg}")

# ═══════════════════════════════════════════════════════════
# תחילת התקנה
# ═══════════════════════════════════════════════════════════

TOTAL_STEPS = 9
print()
print("=" * 50)
print("  ShimiStudio - התקנה אוטומטית")
print("  Python Installer")
print("=" * 50)
print()
print(f"תיקיית התקנה: {INSTALL_DIR}")

# ═══ 1. יצירת תיקייה ═══
step(1, TOTAL_STEPS, "יצירת תיקיית התקנה")
try:
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    ok(str(INSTALL_DIR))
except Exception as e:
    fail(f"שגיאה: {e}")
    sys.exit(1)

# ═══ 2. בדיקת Git ═══
step(2, TOTAL_STEPS, "בדיקת Git")
git_result = run(["git", "--version"])
if git_result.returncode == 0:
    ok(f"Git: {git_result.stdout.strip()}")
else:
    info("Git לא מותקן - מתקין...")
    if sys.platform == "win32":
        # נסה winget
        wg = run(["winget", "install", "--id", "Git.Git", "-e", "--accept-package-agreements", "--accept-source-agreements"], timeout=120)
        if wg.returncode == 0:
            ok("Git הותקן דרך winget")
        else:
            # נסה הורדה ישירה
            info("מוריד Git...")
            git_exe = INSTALL_DIR / "git-installer.exe"
            if download("https://github.com/git-for-windows/git/releases/download/v2.45.0.windows.1/Git-2.45.0-64-bit.exe", git_exe):
                run([str(git_exe), "/VERYSILENT", "/NORESTART"], timeout=120)
                git_exe.unlink(missing_ok=True)
                ok("Git הותקן")
            else:
                fail("נכשלה התקנת Git - נא להתקין ידנית מ https://git-scm.com")
    else:
        run(["apt-get", "install", "-y", "git"] if os.geteuid() == 0 else ["sudo", "apt-get", "install", "-y", "git"])
        ok("Git הותקן")

# ═══ 3. ComfyUI ═══
step(3, TOTAL_STEPS, "הורדת ComfyUI")
comfyui_dir = INSTALL_DIR / "ComfyUI"
if comfyui_dir.exists():
    ok("ComfyUI כבר קיים")
else:
    git_result = run(["git", "clone", "https://github.com/comfyanonymous/ComfyUI.git", str(comfyui_dir)], timeout=120)
    if git_result.returncode == 0:
        ok("ComfyUI הורד")
    else:
        info("git clone נכשל, מוריד ZIP...")
        zip_path = INSTALL_DIR / "comfyui.zip"
        if download("https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip", zip_path):
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(str(INSTALL_DIR))
            extracted = INSTALL_DIR / "ComfyUI-master"
            if extracted.exists():
                extracted.rename(comfyui_dir)
            zip_path.unlink(missing_ok=True)
            ok("ComfyUI הורד (ZIP)")
        else:
            fail("נכשלה הורדת ComfyUI")

# ═══ 4. סביבה וירטואלית + PyTorch ═══
step(4, TOTAL_STEPS, "יצירת סביבה וירטואלית + PyTorch")
venv_dir = INSTALL_DIR / ".venv"
if sys.platform == "win32":
    pip_exe = str(venv_dir / "Scripts" / "pip.exe")
    python_exe = str(venv_dir / "Scripts" / "python.exe")
else:
    pip_exe = str(venv_dir / "bin" / "pip")
    python_exe = str(venv_dir / "bin" / "python")

if not venv_dir.exists():
    info("יוצר venv...")
    run([sys.executable, "-m", "venv", str(venv_dir)])
    ok("venv נוצר")
else:
    ok("venv כבר קיים")

# PyTorch
info("מתקין PyTorch (CUDA)... דקות אחדות")
torch_result = run([pip_exe, "install", "torch", "torchvision", "torchaudio", "--index-url", "https://download.pytorch.org/whl/cu121", "-q"], timeout=600)
if torch_result.returncode == 0:
    ok("PyTorch הותקן")
else:
    info("מנסה ללא CUDA...")
    run([pip_exe, "install", "torch", "torchvision", "torchaudio", "-q"], timeout=600)
    ok("PyTorch הותקן (ללא CUDA)")

# ComfyUI requirements
info("מתקין דרישות ComfyUI...")
req_path = comfyui_dir / "requirements.txt"
if req_path.exists():
    run([pip_exe, "install", "-r", str(req_path), "-q"], timeout=300)
ok("דרישות הותקנו")

# ═══ 5. מודלים ═══
step(5, TOTAL_STEPS, "הורדת מודלים")
models_dir = comfyui_dir / "models"
for model_rel_path, model_url in MODELS:
    model_path = models_dir / model_rel_path
    if model_path.exists():
        ok(f"{model_path.name} כבר קיים")
    else:
        info(f"מוריד {model_path.name}...")
        if download(model_url, model_path):
            ok(model_path.name)
        else:
            fail(f"{model_path.name} נכשל - ניתן להוריד ידנית")

# ═══ 6. Custom Nodes ═══
step(6, TOTAL_STEPS, "התקנת Custom Nodes")
nodes_dir = comfyui_dir / "custom_nodes"
nodes_dir.mkdir(parents=True, exist_ok=True)
for node_name, node_url in CUSTOM_NODES:
    node_path = nodes_dir / node_name
    if node_path.exists():
        ok(f"{node_name} כבר קיים")
    else:
        r = run(["git", "clone", node_url, str(node_path)], timeout=60)
        if r.returncode == 0:
            ok(node_name)
        else:
            fail(f"{node_name} - {r.stderr[:80]}")

# ═══ 7. קבצי Worker ═══
step(7, TOTAL_STEPS, "הורדת קבצי Worker")
for fname in WORKER_FILES:
    dest = INSTALL_DIR / fname
    if dest.exists():
        ok(f"{fname} כבר קיים")
        continue
    url = f"{GITHUB_RAW}/{fname}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read()
        with open(dest, 'wb') as f:
            f.write(content)
        ok(f"{fname} ({len(content)/1024:.0f}KB)")
    except Exception as e:
        # ייתכן שהקובץ לא קיים ב-GitHub עדיין
        if "404" in str(e):
            info(f"{fname} - לא זמין עדיין ב-GitHub")
        else:
            fail(f"{fname} - {e}")

# עדכן config.json
info("מעדכן config.json...")
config_path = INSTALL_DIR / "config.json"
if config_path.exists():
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        config["base44_url"] = SERVER_URL
        config["app_id"] = APP_ID
        config["worker_token"] = WORKER_TOKEN
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        ok("config.json עודכן")
    except Exception as e:
        fail(f"config.json: {e}")
else:
    # צור config חדש
    config = {
        "base44_url": SERVER_URL,
        "app_id": APP_ID,
        "worker_token": WORKER_TOKEN,
        "comfyui_url": "http://127.0.0.1:8188",
        "worker_id": f"worker_{int(time.time())}",
        "poll_interval": 10,
    }
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    ok("config.json נוצר")

# דרישות נוספות
info("מתקין דרישות נוספות...")
run([pip_exe, "install", "requests", "pillow", "tqdm", "watchdog", "-q"], timeout=120)

# diffusers + peft לאימון LoRA
info("מתקין דרישות אימון LoRA...")
run([pip_exe, "install", "diffusers", "transformers", "accelerate", "peft", "safetensors", "datasets", "-q"], timeout=300)
ok("דרישות הותקנו")

# ═══ 8. סקריפט הפעלה ═══
step(8, TOTAL_STEPS, "יצירת סקריפט הפעלה")

if sys.platform == "win32":
    start_bat = INSTALL_DIR / "start_worker.bat"
    start_bat.write_text(f"""@echo off
chcp 65001 >nul
cd /d "{INSTALL_DIR}"
call .venv\\Scripts\\activate.bat
echo.
echo ========================================
echo   ShimiStudio Worker - פעיל
echo ========================================
echo.
python worker.py --server={SERVER_URL} --token={WORKER_TOKEN}
echo.
echo ה-Worker הפסיק. לחץ על מקש כלשהו לסגירה.
pause >nul
""", encoding='ascii', errors='replace')
    ok(f"start_worker.bat נוצר")
    
    # קיצור דרך בשולחן העבודה
    try:
        import winreg
        # נסה ליצור קיצור דרך דרך PowerShell
        ps_cmd = f'''
        $ws = New-Object -ComObject WScript.Shell
        $sc = $ws.CreateShortcut("{Path.home()}\\Desktop\\ShimiStudio Worker.lnk")
        $sc.TargetPath = "{start_bat}"
        $sc.IconLocation = "shell32.dll,13"
        $sc.WorkingDirectory = "{INSTALL_DIR}"
        $sc.Save()
        '''
        run(["powershell", "-Command", ps_cmd], timeout=10)
        ok("קיצור דרך נוצר בשולחן העבודה")
    except:
        info("קיצור דרך ידני - גרור start_worker.bat לשולחן העבודה")

else:
    start_sh = INSTALL_DIR / "start_worker.sh"
    start_sh.write_text(f"""#!/bin/bash
cd "{INSTALL_DIR}"
source .venv/bin/activate
echo "ShimiStudio Worker - פעיל"
python worker.py --server={SERVER_URL} --token={WORKER_TOKEN}
""", encoding='utf-8')
    start_sh.chmod(0o755)
    ok(f"start_worker.sh נוצר")

# ═══ 9. סיכום ═══
step(9, TOTAL_STEPS, "סיכום")
print()
print("=" * 50)
print("  התקנה הושלמה!")
print("=" * 50)
print()
print(f"תיקיית התקנה: {INSTALL_DIR}")
print()
if sys.platform == "win32":
    print("להפעלה:")
    print(f"  לחץ על 'ShimiStudio Worker' בשולחן העבודה")
    print(f"  או הרץ: {start_bat}")
else:
    print("להפעלה:")
    print(f"  {start_sh}")
print()
print("האם להפעיל את ה-Worker עכשיו? (y/n)")
response = input().strip().lower()

if response == 'y':
    print()
    print("מפעיל Worker...")
    if sys.platform == "win32":
        subprocess.Popen([str(start_bat)])
    else:
        subprocess.Popen([str(start_sh)])
    print("Worker הופעל! בדוק את החלון החדש.")
else:
    print("לחץ על קיצור הדרך כשתרצה להתחיל.")

print()
input("לחץ ENTER לסגירה...")
