# ShimiStudio Installer — All-in-One PowerShell
# Run: powershell -ExecutionPolicy Bypass -File install.ps1
# Or:  irm https://raw.githubusercontent.com/sunraz/ShimiStudio/main/install.ps1 | iex

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Say($msg, $color="White") {
    Write-Host $msg -ForegroundColor $color
}

Say ""
Say "========================================" "Green"
Say "  ShimiStudio Installer" "Green"
Say "========================================" "Green"
Say ""

# Config
$INSTALL = "$env:USERPROFILE\ShimiStudio"
$SERVER  = "https://solas-6a095a77.base44.app/functions/shimiStudioAPI"
$TOKEN   = "shimi_worker_auto"
$GITHUB  = "https://raw.githubusercontent.com/sunraz/ShimiStudio/main"

# Create folder
Say "[1/8] Install folder: $INSTALL" "Cyan"
if (!(Test-Path $INSTALL)) { New-Item -ItemType Directory -Path $INSTALL -Force | Out-Null }
Set-Location $INSTALL
Say "  OK" "Green"
Say ""

# Find Python
Say "[2/8] Checking Python..." "Cyan"
$py = $null
foreach ($cmd in @("python","py -3","py")) {
    try {
        $v = Invoke-Expression "$cmd --version 2>&1"
        if ($v -match "Python") { Say "  Found: $v" "Green"; $py = $cmd; break }
    } catch {}
}
if (-not $py) {
    $paths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($p in $paths) {
        if (Test-Path $p) { $v = & $p --version 2>&1; if ($v -match "Python") { Say "  Found: $v at $p" "Green"; $py = $p; break } }
    }
}
if (-not $py) {
    Say "  Python not found. Installing via winget..." "Yellow"
    try { & winget install Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null } catch {}
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Start-Sleep 2
    try { $v = & python --version 2>&1; if ($v -match "Python") { $py = "python" } } catch {}
    if (-not $py) { try { $v = & py -3 --version 2>&1; if ($v -match "Python") { $py = "py -3" } } catch {} }
}
if (-not $py) {
    Say "  FAILED. Install Python from https://python.org" "Red"
    Say "  Check 'Add Python to PATH' during install!" "Yellow"
    Read-Host "Press ENTER to close"
    exit 1
}
Say ""

# Find Git
Say "[3/8] Checking Git..." "Cyan"
$gitOk = $false
try { $gv = & git --version 2>&1; if ($gv -match "git") { Say "  Found: $gv" "Green"; $gitOk = $true } } catch {}
if (-not $gitOk) {
    Say "  Git not found. Installing..." "Yellow"
    try { & winget install Git.Git -e --accept-package-agreements --accept-source-agreements 2>&1 | Out-Null; $gitOk = $true } catch {}
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Say ""

# venv
Say "[4/8] Creating virtual environment..." "Cyan"
$venvPy = "$INSTALL\.venv\Scripts\python.exe"
$venvPip = "$INSTALL\.venv\Scripts\pip.exe"
if (!(Test-Path "$INSTALL\.venv")) {
    Invoke-Expression "$py -m venv `"$INSTALL\.venv`""
}
if (Test-Path $venvPy) { Say "  OK" "Green" }
else {
    Say "  venv failed, using system Python" "Yellow"
    $venvPy = $py
    $venvPip = "$py -m pip"
}
Say ""

# PyTorch
Say "[5/8] Installing PyTorch... (few minutes)" "Cyan"
& $venvPip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -q 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Say "  CUDA failed, trying CPU..." "Yellow"
    & $venvPip install torch torchvision torchaudio -q 2>&1 | Out-Null
}
Say "  OK" "Green"
Say ""

# ComfyUI
Say "[6/8] Downloading ComfyUI..." "Cyan"
$comfy = "$INSTALL\ComfyUI"
if (Test-Path $comfy) { Say "  Already exists" "Green" }
else {
    if ($gitOk) { & git clone https://github.com/comfyanonymous/ComfyUI.git $comfy 2>&1 | Out-Null }
    if (-not (Test-Path $comfy)) {
        Say "  git failed, downloading ZIP..." "Yellow"
        $zip = "$INSTALL\comfy.zip"
        Invoke-WebRequest -Uri "https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip" -OutFile $zip -UseBasicParsing
        Expand-Archive -Path $zip -DestinationPath $INSTALL -Force
        if (Test-Path "$INSTALL\ComfyUI-master") { Rename-Item "$INSTALL\ComfyUI-master" "ComfyUI" }
        Remove-Item $zip -ErrorAction SilentlyContinue
    }
}
if (Test-Path "$comfy\requirements.txt") { & $venvPip install -r "$comfy\requirements.txt" -q 2>&1 | Out-Null }
Say ""

# Models
Say "[7/8] Downloading models... (10-20 min)" "Cyan"
$ckpt = "$comfy\models\checkpoints"
$diff = "$comfy\models\diffusion_models"
New-Item -ItemType Directory -Path $ckpt -Force | Out-Null
New-Item -ItemType Directory -Path $diff -Force | Out-Null

$models = @(
    @("$ckpt\flux1-dev-fp8.safetensors", "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors"),
    @("$diff\wan2.1-t2v-1.3B.safetensors", "https://huggingface.co/Comfy-Org/Wan_2.1/resolve/main/wan2.1-t2v-1.3B.safetensors"),
    @("$ckpt\ltx-video-2b.safetensors", "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b.safetensors")
)
foreach ($m in $models) {
    $dest = $m[0]; $url = $m[1]; $name = Split-Path $dest -Leaf
    if (Test-Path $dest) { Say "  $name - exists" "Green" }
    else {
        Say "  Downloading $name..." "Gray"
        try { Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing; Say "  $name - OK" "Green" }
        catch { Say "  $name - FAILED" "Red" }
    }
}
Say ""

# Worker files + start script
Say "[8/8] Downloading worker files..." "Cyan"
$files = @(
    "worker.py","config.json","base44_client.py","comfyui_client.py",
    "workflows.py","config.py","style_library.py","free_api.py",
    "batch_generator.py","realtime_avatar.py","lora_trainer.py",
    "pipeline.py","civitai_models.py","studio.py","requirements.txt"
)
foreach ($f in $files) {
    $dest = "$INSTALL\$f"
    try { Invoke-WebRequest -Uri "$GITHUB/$f" -OutFile $dest -UseBasicParsing }
    catch { Say "  $f - skip" "Yellow" }
}

# Custom nodes
$nodesDir = "$comfy\custom_nodes"
New-Item -ItemType Directory -Path $nodesDir -Force | Out-Null
if ($gitOk) {
    Push-Location $nodesDir
    $nodeRepos = @(
        @("ComfyUI_IPAdapter_plus","https://github.com/cubiq/ComfyUI_IPAdapter_plus.git"),
        @("ComfyUI_ReActor","https://github.com/Gourieff/ComfyUI_ReActor.git"),
        @("ComfyUI-AnimateDiff-Evolved","https://github.com/kijai/ComfyUI-AnimateDiff-Evolved.git"),
        @("comfyui_wan","https://github.com/kijai/ComfyUI-Wan.git")
    )
    foreach ($r in $nodeRepos) {
        if (!(Test-Path $r[0])) { & git clone $r[1] $r[0] 2>&1 | Out-Null }
    }
    Pop-Location
}

# pip extras
& $venvPip install requests pillow tqdm watchdog diffusers transformers accelerate peft safetensors -q 2>&1 | Out-Null

# Update config
$configPath = "$INSTALL\config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw | ConvertFrom-Json
        $cfg.base44_url = $SERVER
        $cfg.app_id = "6a901f55a4d9a9b76a095a77"
        $cfg.worker_token = $TOKEN
        $cfg | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    } catch {
        # Write fresh config
        $newCfg = @{ base44_url=$SERVER; app_id="6a901f55a4d9a9b76a095a77"; worker_token=$TOKEN; comfyui_url="http://127.0.0.1:8188"; worker_id="worker_$(Get-Date -Format 'yyyyMMddHHmm')"; poll_interval=10 }
        $newCfg | ConvertTo-Json -Depth 10 | Set-Content $configPath -Encoding UTF8
    }
}

# Start script — ENGLISH ONLY, no Hebrew, no UTF-8 issues
$startBat = @"
@echo off
cd /d "$INSTALL"
call .venv\Scripts\activate.bat
echo.
echo ========================================
echo   ShimiStudio Worker - Running
echo ========================================
echo.
python worker.py --server=$SERVER --token=$TOKEN
echo.
echo Worker stopped. Press any key to close.
pause >nul
"@
Set-Content -Path "$INSTALL\start_worker.bat" -Value $startBat -Encoding ASCII

# Desktop shortcut
try {
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\ShimiStudio Worker.lnk")
    $sc.TargetPath = "$INSTALL\start_worker.bat"
    $sc.IconLocation = "shell32.dll,13"
    $sc.WorkingDirectory = $INSTALL
    $sc.Save()
    Say "  Desktop shortcut created" "Green"
} catch { Say "  Shortcut failed - use start_worker.bat" "Yellow" }

Say ""
Say "========================================" "Green"
Say "  INSTALL COMPLETE" "Green"
Say "========================================" "Green"
Say ""
Say "To start: click 'ShimiStudio Worker' on your Desktop"
Say ""
Say "Start now? (Y/N)" "Yellow"
$r = Read-Host
if ($r -eq "Y" -or $r -eq "y") { Start-Process -FilePath "$INSTALL\start_worker.bat" }
Say ""
Read-Host "Press ENTER to close"
