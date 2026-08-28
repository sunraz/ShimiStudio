# ShimiStudio — התקנה אוטומטית ל-Windows
# הורד, הפעל, והמחשב שלך הופך לתחנת כח ✅
# קליק ימני → "הפעל עם PowerShell"

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     ShimiStudio — התקנה אוטומטית        ║" -ForegroundColor Green
Write-Host "║     נא לא לסגור את החלון הזה!           ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# ═══ הגדרות שרת ═══
$SERVER_URL = "https://solas-6a095a77.base44.app/functions/shimiStudioAPI"
$APP_ID = "6a901f55a4d9a9b76a095a77"
$WORKER_TOKEN = "shimi_worker_auto"
$INSTALL_DIR = "$env:USERPROFILE\ShimiStudio"

# ═══ 1. תיקיית התקנה ═══
Write-Host "[1/10] יוצר תיקיית התקנה: $INSTALL_DIR" -ForegroundColor Cyan
if (!(Test-Path $INSTALL_DIR)) { New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null }
Set-Location $INSTALL_DIR
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 2. בדיקת Python ═══
Write-Host "[2/10] בודק Python..." -ForegroundColor Cyan
try {
    $pyVer = (python --version 2>&1) -replace "Python ", ""
    Write-Host "✓ Python $pyVer מותקן" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Python לא מותקן. מוריד Python 3.11..." -ForegroundColor Yellow
    $pyInstaller = "$env:TEMP\python-installer.exe"
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe" -OutFile $pyInstaller
    Start-Process -FilePath $pyInstaller -ArgumentList "/passive InstallAllUsers=1 PrependPath=1" -Wait
    Remove-Item $pyInstaller
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    $pyVer = (python --version 2>&1) -replace "Python ", ""
    Write-Host "✓ Python $pyVer מותקן" -ForegroundColor Green
}
Write-Host ""

# ═══ 3. סביבה וירטואלית ═══
Write-Host "[3/10] יוצר סביבה וירטואלית..." -ForegroundColor Cyan
if (!(Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 4. PyTorch ═══
Write-Host "[4/10] מתקין PyTorch עם CUDA... (יכול לקחת דקות)" -ForegroundColor Cyan
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -q
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 5. ComfyUI ═══
Write-Host "[5/10] מוריד ComfyUI..." -ForegroundColor Cyan
if (!(Test-Path "ComfyUI")) {
    git clone https://github.com/comfyanonymous/ComfyUI.git
} else {
    Write-Host "✓ ComfyUI כבר קיים" -ForegroundColor Green
}
Set-Location ComfyUI
pip install -r requirements.txt -q
Set-Location ..
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 6. מודלים ═══
Write-Host "[6/10] מוריד מודלים... (יכול לקחת 15-30 דקות)" -ForegroundColor Cyan
New-Item -ItemType Directory -Path "ComfyUI\models\checkpoints" -Force | Out-Null
New-Item -ItemType Directory -Path "ComfyUI\models\diffusion_models" -Force | Out-Null

if (!(Test-Path "ComfyUI\models\checkpoints\flux1-dev-fp8.safetensors")) {
    Write-Host "  מוריד Flux.1..." -ForegroundColor Gray
    Invoke-WebRequest -Uri "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" -OutFile "ComfyUI\models\checkpoints\flux1-dev-fp8.safetensors"
}

if (!(Test-Path "ComfyUI\models\diffusion_models\wan2.1-t2v-1.3B.safetensors")) {
    Write-Host "  מוריד Wan 2.1..." -ForegroundColor Gray
    Invoke-WebRequest -Uri "https://huggingface.co/Comfy-Org/Wan_2.1/resolve/main/wan2.1-t2v-1.3B.safetensors" -OutFile "ComfyUI\models\diffusion_models\wan2.1-t2v-1.3B.safetensors"
}

if (!(Test-Path "ComfyUI\models\checkpoints\ltx-video-2b.safetensors")) {
    Write-Host "  מוריד LTX-Video..." -ForegroundColor Gray
    Invoke-WebRequest -Uri "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b.safetensors" -OutFile "ComfyUI\models\checkpoints\ltx-video-2b.safetensors"
}
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 7. Custom Nodes ═══
Write-Host "[7/10] מתקין Custom Nodes..." -ForegroundColor Cyan
Set-Location ComfyUI\custom_nodes
if (!(Test-Path "ComfyUI_IPAdapter_plus")) { git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git 2>$null }
if (!(Test-Path "ComfyUI_ReActor")) { git clone https://github.com/Gourieff/ComfyUI_ReActor.git 2>$null }
if (!(Test-Path "ComfyUI-AnimateDiff-Evolved")) { git clone https://github.com/kijai/ComfyUI-AnimateDiff-Evolved.git 2>$null }
if (!(Test-Path "comfyui_wan")) { git clone https://github.com/kijai/ComfyUI-Wan.git 2>$null }
Set-Location ..\..
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 8. Worker ═══
Write-Host "[8/10] מוריד Worker..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/worker.py" -OutFile "worker.py" -UseBasicParsing
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/config.json" -OutFile "config.json" -UseBasicParsing
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/base44_client.py" -OutFile "base44_client.py" -UseBasicParsing
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/comfyui_client.py" -OutFile "comfyui_client.py" -UseBasicParsing
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/workflows.py" -OutFile "workflows.py" -UseBasicParsing

# עדכן config
$config = Get-Content "config.json" -Raw | ConvertFrom-Json
$config.base44_url = $SERVER_URL
$config.app_id = $APP_ID
$config.worker_token = $WORKER_TOKEN
$config | ConvertTo-Json -Depth 10 | Set-Content "config.json" -Encoding UTF8
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 9. דרישות ═══
Write-Host "[9/10] מתקין דרישות נוספות..." -ForegroundColor Cyan
pip install requests pillow tqdm watchdog -q
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ 10. קיצור דרך ═══
Write-Host "[10/10] יוצר קיצור דרך בשולחן העבודה..." -ForegroundColor Cyan

# סקריפט הפעלה
$startScript = @"
@echo off
chcp 65001 >nul
cd /d "$INSTALL_DIR"
call .venv\Scripts\activate.bat
echo מפעיל ShimiStudio Worker...
python worker.py --server=$SERVER_URL --token=$WORKER_TOKEN
pause
"@
Set-Content -Path "$INSTALL_DIR\start_worker.bat" -Value $startScript -Encoding UTF8

# קיצור דרך
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\ShimiStudio Worker.lnk")
$sc.TargetPath = "$INSTALL_DIR\start_worker.bat"
$sc.IconLocation = "shell32.dll,13"
$sc.Save()
Write-Host "✓ הושלם" -ForegroundColor Green
Write-Host ""

# ═══ סיום ═══
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     התקנה הושלמה! 🎉                    ║" -ForegroundColor Green
Write-Host "║                                          ║" -ForegroundColor Green
Write-Host "║  המחשב מחובר כתחנת כח ✅                 ║" -ForegroundColor Green
Write-Host "║                                          ║" -ForegroundColor Green
Write-Host "║  להפעלה: לחץ על הקיצור בשולחן העבודה    ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "מפעיל Worker עכשיו..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process -FilePath "$INSTALL_DIR\start_worker.bat"
