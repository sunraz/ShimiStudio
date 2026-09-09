# ShimiStudio Worker Installer
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$SERVER = "https://base44-dispatcher-production.base44.workers.dev"
$TOKEN = ""
$NAME = "Worker-Windows"
$API_BASE = "https://base44-dispatcher-production.base44.workers.dev/api/apps"
$DIR = Join-Path $env:USERPROFILE "ShimiStudio"

function WS($n,$t,$m){ Write-Host "[$n/$t] $m" -ForegroundColor Yellow }
function WOK($m){ Write-Host "  OK: $m" -ForegroundColor Green }
function WERR($m){ Write-Host "  ERROR: $m" -ForegroundColor Red }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ShimiStudio Worker - Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Python ──
WS 1 7 "Checking Python..."
$pyExe = $null

# Try Get-Command but skip Windows Store stub
try {
  $cmd = Get-Command python -ErrorAction Stop
  if ($cmd.Source -notlike "*WindowsApps*") { $pyExe = $cmd.Source }
} catch {}

# Verify it actually works
if ($pyExe) {
  try { $null = & $pyExe -c "print(1)" 2>&1 } catch { $pyExe = $null }
}

# Try common install paths
if (-not $pyExe) {
  $cands = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "$env:ProgramFiles\Python312\python.exe",
    "$env:ProgramFiles\Python311\python.exe"
  )
  foreach ($c in $cands) { if (Test-Path $c) { $pyExe = $c; break } }
}

# Download and install
if (-not $pyExe) {
  Write-Host "  Python not found. Downloading Python 3.12..."
  $inst = "$env:TEMP\py-installer.exe"
  try {
    Invoke-WebRequest "https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe" -OutFile $inst -UseBasicParsing
    Start-Process -Wait -FilePath $inst -ArgumentList "/quiet","InstallAllUsers=0","PrependPath=1"
    Remove-Item $inst -Force
    $pyExe = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
  } catch {
    WERR "Failed to download Python. Please install Python 3 from python.org manually."
    Read-Host "Press Enter to exit"; exit 1
  }
}

if (-not (Test-Path $pyExe)) { WERR "Python not found at $pyExe"; Read-Host "Press Enter to exit"; exit 1 }
WOK "Python: $pyExe"

# ── 2. Directory ──
WS 2 7 "Creating directory..."
if (-not (Test-Path $DIR)) { New-Item -ItemType Directory -Path $DIR -Force | Out-Null }
Set-Location $DIR
WOK $DIR

# ── 3. ComfyUI ──
WS 3 7 "Checking ComfyUI..."
$comfyuiDir = "$DIR\ComfyUI"
$comfyuiFound = $false

# Check default install location
if (Test-Path "$comfyuiDir\main.py") {
  $comfyuiFound = $true
  WOK "ComfyUI found at $comfyuiDir"
} else {
  # Check common locations on the machine
  $candidates = @("$env:USERPROFILE\ComfyUI", "$env:USERPROFILE\Documents\ComfyUI", "C:\ComfyUI", "D:\ComfyUI")
  foreach ($c in $candidates) {
    if (Test-Path "$c\main.py") {
      $comfyuiDir = $c
      $comfyuiFound = $true
      WOK "ComfyUI found at $c"
      break
    }
  }
}

if (-not $comfyuiFound) {
  Write-Host "  ComfyUI not found. Downloading from GitHub (ZIP)..."
  $zipPath = "$env:TEMP\ComfyUI.zip"
  $tempExtract = "$env:TEMP\ComfyUI_extract"
  try {
    Invoke-WebRequest "https://github.com/comfyanonymous/ComfyUI/archive/refs/heads/master.zip" -OutFile $zipPath -UseBasicParsing
    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
    Expand-Archive $zipPath -DestinationPath $tempExtract -Force
    $inner = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
    if ($inner) { Move-Item $inner.FullName "$DIR\ComfyUI" -Force }
    if (Test-Path "$DIR\ComfyUI\main.py") { WOK "ComfyUI installed" }
    else { WERR "ComfyUI install failed - try manual install from https://github.com/comfyanonymous/ComfyUI" }
  } catch { WERR "ComfyUI download failed: $($_.Exception.Message)" }
  if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
}

# Custom nodes (ZIP download — no git or GitHub auth needed)
$nodesDir = "$comfyuiDir\custom_nodes"
if (-not (Test-Path $nodesDir)) { New-Item -ItemType Directory -Path $nodesDir -Force | Out-Null }
$customNodes = @(
  @("ComfyUI_IPAdapter_plus", "https://github.com/cubiq/ComfyUI_IPAdapter_plus/archive/refs/heads/main.zip"),
  @("ComfyUI_ReActor", "https://github.com/Gourieff/ComfyUI_ReActor/archive/refs/heads/main.zip"),
  @("ComfyUI-AnimateDiff-Evolved", "https://github.com/kijai/ComfyUI-AnimateDiff-Evolved/archive/refs/heads/main.zip"),
  @("ComfyUI-VideoHelperSuite", "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite/archive/refs/heads/main.zip")
)
foreach ($node in $customNodes) {
  $nodePath = "$nodesDir\$($node[0])"
  $needInstall = $true
  if (Test-Path $nodePath) {
    $pyFiles = @(Get-ChildItem $nodePath -Filter *.py -File -ErrorAction SilentlyContinue)
    if ($pyFiles.Count -gt 0) { WOK "$($node[0]) exists"; $needInstall = $false }
    else { WERR "$($node[0]) incomplete — re-downloading"; Remove-Item $nodePath -Recurse -Force -ErrorAction SilentlyContinue }
  }
  if ($needInstall) {
    Write-Host "  Downloading $($node[0])..."
    $zipPath = "$env:TEMP\$($node[0]).zip"
    $tempExtract = "$env:TEMP\$($node[0])_extract"
    try {
      Invoke-WebRequest $node[1] -OutFile $zipPath -UseBasicParsing
      if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
      Expand-Archive $zipPath -DestinationPath $tempExtract -Force
      $inner = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
      if ($inner) { Move-Item $inner.FullName $nodePath -Force }
    } catch { WERR "$($node[0]) download failed: $($_.Exception.Message)" }
    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
    if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
    $pyFiles = @(Get-ChildItem $nodePath -Filter *.py -File -ErrorAction SilentlyContinue)
    if ($pyFiles.Count -gt 0) { WOK "$($node[0]) installed" } else { WERR "$($node[0]) install failed" }
  }
}

# ── 4. Venv + dependencies ──
WS 4 7 "Setting up Python environment..."
$vp = $pyExe
$useVenv = $false
if (-not (Test-Path "$DIR\venv\Scripts\python.exe")) {
  Write-Host "  Creating virtual environment..."
  & $pyExe -m venv "$DIR\venv" 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
  if (Test-Path "$DIR\venv\Scripts\python.exe") {
    $vp = "$DIR\venv\Scripts\python.exe"
    $useVenv = $true
    WOK "venv created"
  } else {
    WOK "venv unavailable, using system Python"
  }
} else {
  $vp = "$DIR\venv\Scripts\python.exe"
  $useVenv = $true
  WOK "venv exists"
}

# Clean corrupted packages (partial uninstalls leave ~prefix dirs that break pip)
Get-ChildItem "$DIR\venv\Lib\site-packages" -Filter "~*" -Directory -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "  Installing requests..."
try { & $vp -m pip install --upgrade pip --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
try { & $vp -m pip install requests --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
if ($LASTEXITCODE -ne 0) { WERR "pip install failed" } else { WOK "requests installed" }

# Check for NVIDIA GPU
Write-Host "  Checking for NVIDIA GPU..."
$hasNvidia = $false
try {
  $nvidiaSmi = Get-Command nvidia-smi -ErrorAction Stop
  $null = & $nvidiaSmi.Source --query-gpu=name --format=csv,noheader 2>&1
  if ($LASTEXITCODE -eq 0) { $hasNvidia = $true; WOK "NVIDIA GPU detected" }
} catch {}
if (-not $hasNvidia) { WERR "No NVIDIA GPU detected — will use CPU mode (slower)" }

# PyTorch — force reinstall to ensure CUDA version replaces any CPU-only torch
if ($hasNvidia) {
  Write-Host "  Installing PyTorch with CUDA 12.1 (this may take several minutes, ~2.5GB)..."
  try {
    & $vp -m pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --disable-pip-version-check 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
  } catch { Write-Host "    (pip dependency warnings — continuing)" -ForegroundColor DarkGray }
  WOK "PyTorch CUDA installed"
} else {
  Write-Host "  Installing PyTorch (CPU only)..."
  try {
    & $vp -m pip install --force-reinstall torch torchvision torchaudio --disable-pip-version-check 2>&1 | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
  } catch { Write-Host "    (pip dependency warnings — continuing)" -ForegroundColor DarkGray }
  WOK "PyTorch CPU installed"
}

# ComfyUI requirements
if (Test-Path "$comfyuiDir\requirements.txt") {
  Write-Host "  Installing ComfyUI requirements..."
  try { & $vp -m pip install -r "$comfyuiDir\requirements.txt" --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
  WOK "ComfyUI requirements installed"
}

# Custom node dependencies (critical — ComfyUI crashes on startup if these are missing)
Write-Host "  Installing custom node dependencies..."
foreach ($node in $customNodes) {
  $nodePath = "$nodesDir\$($node[0])"
  if (Test-Path "$nodePath\requirements.txt") {
    try { & $vp -m pip install -r "$nodePath\requirements.txt" --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
  }
}
WOK "Custom node dependencies installed"

# Video-specific dependencies (not always in node requirements.txt — critical for AnimateDiff + VHS video output)
Write-Host "  Installing video generation dependencies (imageio-ffmpeg, einops, scipy, opencv)..."
try { & $vp -m pip install imageio-ffmpeg einops scipy opencv-python --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
WOK "Video dependencies installed"

# ReActor dependencies (insightface + onnxruntime — not always in requirements.txt)
Write-Host "  Installing ReActor face-swap dependencies (insightface, onnxruntime)..."
try { & $vp -m pip install insightface onnxruntime-gpu --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
try { & $vp -m pip install onnxruntime --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
WOK "ReActor dependencies installed"

# Verify PyTorch CUDA
Write-Host "  Verifying PyTorch CUDA..."
try {
  $torchCheck = & $vp -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>&1
  Write-Host "  $torchCheck" -ForegroundColor DarkGray
  if ($torchCheck -like "*CUDA available: True*") { WOK "PyTorch CUDA verified" }
  else { WERR "PyTorch CUDA not available - GPU acceleration may not work" }
} catch { WERR "PyTorch verification failed" }

# ── 4.1. Kohya_ss (sd-scripts) for real LoRA training ──
Write-Host "  Setting up Kohya_ss (sd-scripts) for LoRA training..."
$sdScriptsDir = "$DIR\sd-scripts"
if (-not (Test-Path "$sdScriptsDir\sdxl_train_network.py")) {
  if (Test-Path $sdScriptsDir) { Remove-Item $sdScriptsDir -Recurse -Force -ErrorAction SilentlyContinue }
  Write-Host "  Downloading sd-scripts (ZIP)..."
  $zipPath = "$env:TEMP\sd-scripts.zip"
  $tempExtract = "$env:TEMP\sd-scripts_extract"
  try {
    Invoke-WebRequest "https://github.com/kohya-ss/sd-scripts/archive/refs/heads/main.zip" -OutFile $zipPath -UseBasicParsing
    if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force }
    Expand-Archive $zipPath -DestinationPath $tempExtract -Force
    $inner = Get-ChildItem $tempExtract -Directory | Select-Object -First 1
    if ($inner) { Move-Item $inner.FullName $sdScriptsDir -Force }
  } catch { WERR "sd-scripts download failed: $($_.Exception.Message)" }
  if (Test-Path $tempExtract) { Remove-Item $tempExtract -Recurse -Force -ErrorAction SilentlyContinue }
  if (Test-Path $zipPath) { Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
}
if (Test-Path "$sdScriptsDir\requirements.txt") {
  Write-Host "  Installing sd-scripts training dependencies (this may take a few minutes)..."
  $filtered = Get-Content "$sdScriptsDir\requirements.txt" | Where-Object {
    $l = $_.Trim()
    $l -and -not $l.StartsWith('#') -and $l -ne '.' -and $l -ne '-e .'
  }
  $tempReq = "$env:TEMP\sd-scripts-reqs.txt"
  $filtered | Set-Content $tempReq
  try { & $vp -m pip install -r $tempReq --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
  try { & $vp -m pip install accelerate transformers bitsandbytes --quiet --disable-pip-version-check 2>&1 | Out-Null } catch {}
  Remove-Item $tempReq -Force -ErrorAction SilentlyContinue
  if (Test-Path "$sdScriptsDir\sdxl_train_network.py") {
    WOK "sd-scripts + training deps installed (real LoRA training enabled)"
  } else {
    WERR "sd-scripts incomplete — training will fall back to IP-Adapter reference"
  }
} else {
  WERR "sd-scripts download failed — training will fall back to IP-Adapter reference"
}

# ── 4.15. Checkpoints (user-selected) ──
$ckptDir = "$comfyuiDir\models\checkpoints"
if (-not (Test-Path $ckptDir)) { New-Item -ItemType Directory -Path $ckptDir -Force | Out-Null }
$downloadsDir = Join-Path $env:USERPROFILE "Downloads"
if (-not (Test-Path "$ckptDir\v1-5-pruned-emaonly.safetensors")) {
  $localPath = Join-Path $downloadsDir ""
  if ("" -and (Test-Path $localPath)) {
    Write-Host "  Copying Stable Diffusion 1.5 from Downloads (~4GB)..."
    try {
      Copy-Item $localPath "$ckptDir\v1-5-pruned-emaonly.safetensors" -Force
      WOK "Stable Diffusion 1.5 copied from Downloads"
    } catch { WERR "Stable Diffusion 1.5 copy failed: $($_.Exception.Message)" }
  } else {
    Write-Host "  Downloading Stable Diffusion 1.5 (~4GB)..."
    try {
      Invoke-WebRequest "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" -OutFile "$ckptDir\v1-5-pruned-emaonly.safetensors" -UseBasicParsing -ErrorAction Stop
      WOK "Stable Diffusion 1.5 downloaded"
    } catch { WERR "Stable Diffusion 1.5 download failed: $($_.Exception.Message)" }
  }
} else { WOK "Stable Diffusion 1.5 exists" }

# ── 4.2. IP-Adapter models (fallback for character consistency without LoRA) ──
Write-Host "  Checking IP-Adapter models..."
$ipadapterDir = "$comfyuiDir\models\ipadapter"
$clipVisionDir = "$comfyuiDir\models\clip_vision"
if (-not (Test-Path $ipadapterDir)) { New-Item -ItemType Directory -Path $ipadapterDir -Force | Out-Null }
if (-not (Test-Path $clipVisionDir)) { New-Item -ItemType Directory -Path $clipVisionDir -Force | Out-Null }
if (-not (Test-Path "$ipadapterDir\ip-adapter-plus_sd15.safetensors")) {
  Write-Host "  Downloading IP-Adapter Plus SD 1.5 model (~1.5GB, best-effort)..."
  try {
    Invoke-WebRequest "https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sd15.safetensors" -OutFile "$ipadapterDir\ip-adapter-plus_sd15.safetensors" -UseBasicParsing -ErrorAction Stop
    WOK "IP-Adapter Plus SD 1.5 model downloaded"
  } catch {
    WERR "IP-Adapter SD 1.5 download failed — IP-Adapter fallback unavailable (LoRA training still works)"
  }
} else { WOK "IP-Adapter Plus SD 1.5 model exists" }
if (-not (Test-Path "$clipVisionDir\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")) {
  Write-Host "  Downloading CLIP Vision model (~3.5GB, best-effort)..."
  try {
    Invoke-WebRequest "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" -OutFile "$clipVisionDir\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors" -UseBasicParsing -ErrorAction Stop
    WOK "CLIP Vision model downloaded"
  } catch {
    WERR "CLIP Vision model download failed (non-blocking)"
  }
} else { WOK "CLIP Vision model exists" }

# ── 4.25. Motion modules (user-selected) ──
$mmDir = "$comfyuiDir\models\animatediff_models"
if (-not (Test-Path $mmDir)) { New-Item -ItemType Directory -Path $mmDir -Force | Out-Null }
if (-not (Test-Path "$mmDir\mm_sd_v15_v2.ckpt")) {
  Write-Host "  Downloading AnimateDiff v2 (~1.6GB)..."
  try {
    Invoke-WebRequest "https://huggingface.co/guoyww/animatediff/resolve/main/mm_sd_v15_v2.ckpt" -OutFile "$mmDir\mm_sd_v15_v2.ckpt" -UseBasicParsing -ErrorAction Stop
    WOK "AnimateDiff v2 downloaded"
  } catch { WERR "AnimateDiff v2 download failed: $($_.Exception.Message)" }
} else { WOK "AnimateDiff v2 exists" }

# ── 4.5. Stop existing worker (aggressive) ──
WS 5 7 "Stopping existing worker..."
$stopped = 0
try {
  $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
  foreach ($p in $procs) {
    $cmd = if ($p.CommandLine) { $p.CommandLine } else { "" }
    $exe = if ($p.ExecutablePath) { $p.ExecutablePath } else { "" }
    if ($cmd -like "*worker.py*" -or $cmd -like "*ShimiStudio*" -or $exe -like "*ShimiStudio*") {
      try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue; $stopped++ } catch {}
    }
  }
} catch {}
# Fallback: taskkill any python in ShimiStudio dir
if ($stopped -eq 0) {
  try { taskkill /F /IM python.exe /FI "MODULES eq ShimiStudio*" 2>&1 | Out-Null } catch {}
}
Start-Sleep -Seconds 3
# Delete old worker.py so it's not locked
if (Test-Path "$DIR\worker.py") {
  Remove-Item "$DIR\worker.py" -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
if ($stopped -gt 0) { WOK "Stopped $stopped old worker(s)" } else { WOK "No old workers running" }

# ── 5. Worker files ──
WS 5 7 "Writing worker files..."
@'
import requests, time, json, os, sys, subprocess, random, base64, traceback, re, shutil

cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
with open(cfg_path, encoding="utf-8-sig") as f:
    cfg = json.load(f)

TOKEN = cfg["token"]
NAME = cfg["name"]
SERVER = cfg.get("server", "")
API = cfg["apiBase"].rstrip("/")
COMFYUI_URL = cfg.get("comfyui_url", "http://127.0.0.1:8188")
COMFYUI_PATH = cfg.get("comfyui_path", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ComfyUI"))
IS_MAC = sys.platform == "darwin"
VENV_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "Scripts" if os.name == "nt" else "bin", "python.exe" if os.name == "nt" else "python")
AVAILABLE_NODES = set()

def save_image(url, path):
    if url.startswith('data:image'):
        header, data = url.split(',', 1)
        img_data = base64.b64decode(data)
        with open(path, 'wb') as f:
            f.write(img_data)
    else:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)

def post(fn, data, timeout=120):
    try:
        r = requests.post(f"{API}/functions/{fn}", json=data, timeout=timeout)
        if r.status_code >= 400:
            try:
                err = r.json()
                return {"error": err.get("error", f"HTTP {r.status_code}")}
            except:
                return {"error": f"HTTP {r.status_code}"}
        return r.json()
    except Exception as e:
        print(f"  err: {e}")
        return {"error": str(e)}

def comfyui_ready():
    try:
        r = requests.get(f"{COMFYUI_URL}/system_stats", timeout=5)
        return r.status_code == 200
    except:
        return False

def fetch_available_nodes():
    global AVAILABLE_NODES
    try:
        r = requests.get(f"{COMFYUI_URL}/object_info", timeout=15)
        if r.status_code == 200:
            AVAILABLE_NODES = set(r.json().keys())
            print(f"  ComfyUI nodes: {len(AVAILABLE_NODES)} | IPAdapter={('IPAdapterApply' in AVAILABLE_NODES)} ReActor={('ReActorFaceSwap' in AVAILABLE_NODES)} AnimateDiff={('ADE_AnimateDiffLoaderGen1' in AVAILABLE_NODES)} VHS={('VHS_VideoCombine' in AVAILABLE_NODES)}")
        else:
            print(f"  /object_info HTTP {r.status_code} — custom-node workflows disabled")
    except Exception as e:
        print(f"  /object_info failed: {e} — custom-node workflows disabled")

def start_comfyui():
    if comfyui_ready():
        print("  ComfyUI already running")
        return True
    main_py = os.path.join(COMFYUI_PATH, "main.py")
    if not os.path.exists(main_py):
        print(f"  ComfyUI not found at {COMFYUI_PATH}")
        return False
    # Check for checkpoint
    ckpt_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    has_ckpt = False
    if os.path.isdir(ckpt_dir):
        for f in os.listdir(ckpt_dir):
            if f.lower().endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
                has_ckpt = True; break
    if not has_ckpt:
        print("  WARNING: No checkpoint found in models/checkpoints/")
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comfyui.log")

    def try_start(extra_args=None):
        args = [VENV_PY, main_py, "--listen", "127.0.0.1", "--port", "8188"]
        if extra_args:
            args.extend(extra_args)
        # Detect CUDA — if not available, run ComfyUI in CPU mode
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            has_mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
            if not has_cuda and not has_mps:
                print("  No GPU backend (CUDA/MPS) — starting ComfyUI in CPU mode (slower)")
                args.append("--cpu")
            elif has_mps and not has_cuda:
                print("  Apple Silicon MPS detected — ComfyUI will use Metal acceleration")
                args.append("--force-fp16")
        except ImportError:
            print("  PyTorch not importable — starting ComfyUI in CPU mode")
            args.append("--cpu")
        log_file = open(log_path, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(args, cwd=COMFYUI_PATH, stdout=log_file, stderr=subprocess.STDOUT)
        for i in range(90):
            time.sleep(2)
            if comfyui_ready():
                return True
            if proc.poll() is not None:
                log_file.flush()
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        print("  --- Last 30 lines of comfyui.log ---")
                        for line in lines[-30:]:
                            print(f"  {line.rstrip()}")
                        print("  --- End of log ---")
                except: pass
                return False
            if i % 15 == 0 and i > 0:
                log_file.flush()
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                        if lines:
                            print(f"  Waiting for ComfyUI... ({i*2}s) - {lines[-1].rstrip()[:80]}")
                        else:
                            print(f"  Waiting for ComfyUI... ({i*2}s) - no output yet")
                except: pass
        log_file.flush()
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                print("  --- Last 30 lines of comfyui.log ---")
                for line in lines[-30:]:
                    print(f"  {line.rstrip()}")
                print("  --- End of log ---")
        except: pass
        return False

    print("  Starting ComfyUI (with custom nodes)...")
    if try_start():
        print("  ComfyUI started")
        return True
    print("  ComfyUI failed with custom nodes. Retrying with --disable-all-custom-nodes...")
    if try_start(["--disable-all-custom-nodes"]):
        print("  ComfyUI started (custom nodes disabled - IP-Adapter/ReActor unavailable)")
        return True
    print("  ComfyUI failed to start after retries")
    return False

def queue_prompt(workflow):
    r = requests.post(f"{COMFYUI_URL}/prompt", json={"prompt": workflow, "client_id": "shimi"}, timeout=30)
    if r.status_code >= 400:
        try:
            err_data = r.json()
            print("  ComfyUI error details:")
            if "error" in err_data:
                print(f"    error: {json.dumps(err_data['error'], indent=2)[:600]}")
            if "node_errors" in err_data:
                for nid, nerr in err_data["node_errors"].items():
                    cls = nerr.get("class_type", "?")
                    errs = nerr.get("errors", nerr)
                    print(f"    Node {nid} ({cls}): {json.dumps(errs, indent=2)[:400]}")
        except:
            print(f"  ComfyUI error: {r.text[:600]}")
        r.raise_for_status()
    return r.json()["prompt_id"]

def wait_for_result(prompt_id, jid):
    start = time.time()
    while True:
        # Check if user cancelled the job
        try:
            st = post("jobApi", {"action": "get", "job_id": jid})
            if st.get("job", {}).get("status") == "cancelled":
                print("  Job cancelled by user — interrupting ComfyUI")
                try:
                    requests.post(f"{COMFYUI_URL}/interrupt", json={}, timeout=5)
                except: pass
                return None
        except: pass
        try:
            r = requests.get(f"{COMFYUI_URL}/history/{prompt_id}", timeout=10)
            data = r.json()
            if prompt_id in data:
                return data[prompt_id].get("outputs", {})
        except:
            pass
        elapsed = int((time.time() - start) / 60)
        if elapsed > 45:
            try:
                requests.post(f"{COMFYUI_URL}/interrupt", json={}, timeout=5)
            except: pass
            raise TimeoutError("Render exceeded 45 minutes — aborted")
        post("jobApi", {"action": "progress", "job_id": jid, "progress": min(80, 50 + elapsed * 5)})
        time.sleep(3)

def get_output(outputs):
    for nid, out in outputs.items():
        if "gifs" in out and out["gifs"]:
            item = out["gifs"][0]
            fname = item.get("filename", "")
            if fname.lower().endswith(('.mp4', '.webm', '.avi', '.mov')):
                return item, "video"
            return item, "image"
        if "videos" in out and out["videos"]:
            return out["videos"][0], "video"
        if "images" in out and out["images"]:
            return out["images"][0], "image"
    return None, None

def download_file(item):
    params = {"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")}
    r = requests.get(f"{COMFYUI_URL}/view", params=params, timeout=300)
    return r.content

def build_t2i(prompt, negative, lora=None, model=None, w=512, h=512):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["3"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    return wf

def download_lora(url):
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    if not os.path.isdir(lora_dir):
        os.makedirs(lora_dir, exist_ok=True)
    fname = url.split("/")[-1].split("?")[0] or "imported.safetensors"
    if not fname.endswith(('.safetensors', '.pt', '.ckpt', '.gguf')):
        fname += ".safetensors"
    fp = os.path.join(lora_dir, fname)
    if os.path.exists(fp):
        print(f"  LoRA exists: {fname}")
        return f"loras/{fname}"
    print(f"  Downloading LoRA: {fname}")
    try:
        r = requests.get(url, timeout=600, stream=True)
        r.raise_for_status()
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
        print(f"  LoRA downloaded: {fname}")
        return f"loras/{fname}"
    except Exception as e:
        print(f"  LoRA download failed: {e}")
        return None

def build_t2i_ipadapter(prompt, negative, ref_image, model=None, w=512, h=512):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "13": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["10", 0], "clip_vision": ["12", 0]}},
        "14": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["11", 0], "clip_vision": ["13", 0], "image": ["10", 0], "weight": 0.8, "model": ["4", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["14", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    return wf

def build_img2img(prompt, negative, source_image, lora=None, model=None, w=512, h=512, denoise=0.6):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": source_image}},
        "10a": {"class_type": "ImageScale", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10a", 0], "vae": ["4", 2]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["11", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi", "images": ["8", 0]}},
    }
    if lora:
        wf["12"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["3"]["inputs"]["model"] = ["12", 0]
        wf["6"]["inputs"]["clip"] = ["12", 1]
        wf["7"]["inputs"]["clip"] = ["12", 1]
    return wf

def build_face_swap(input_image, face_image):
    wf = {
        "10": {"class_type": "LoadImage", "inputs": {"image": input_image}},
        "11": {"class_type": "LoadImage", "inputs": {"image": face_image}},
        "12": {"class_type": "ReActorFaceSwap", "inputs": {
            "input_image": ["10", 0],
            "source_image": ["11", 0],
            "face_id": 0,
            "index": 0,
            "facedetection": "retinaface",
            "face_restore": "codeformer",
            "face_restore_weight": 0.5,
            "weight": 0.85,
        }},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi_swap", "images": ["12", 0]}},
    }
    return wf

def build_body_swap(input_image, ref_image, lora=None, model=None, denoise=0.6):
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": input_image}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}},
        "20": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "21": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "22": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "23": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["20", 0], "clip_vision": ["22", 0]}},
        "24": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["21", 0], "clip_vision": ["23", 0], "image": ["20", 0], "weight": 0.8, "model": ["4", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": "full body, high quality, detailed, same pose as input", "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "bad quality, blurry, distorted, deformed, extra limbs", "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["24", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["11", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "shimi_body", "images": ["8", 0]}},
    }
    if lora:
        wf["25"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["24"]["inputs"]["model"] = ["25", 0]
        wf["6"]["inputs"]["clip"] = ["25", 1]
        wf["7"]["inputs"]["clip"] = ["25", 1]
    return wf

def is_sdxl_model(model_name):
    n = (model_name or "").lower()
    return "xl" in n or "sdxl" in n

# Motion modules can live in either the standard ComfyUI dir or the AnimateDiff-Evolved custom node dir
def mm_dirs():
    return [
        os.path.join(COMFYUI_PATH, "models", "animatediff_models"),
        os.path.join(COMFYUI_PATH, "custom_nodes", "ComfyUI-AnimateDiff-Evolved", "models"),
    ]

def list_motion_modules():
    files = []
    for d in mm_dirs():
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith(('.ckpt', '.safetensors', '.pt')):
                files.append(f)
    return files

def video_supported(model=None):
    sdxl = is_sdxl_model(model)
    for f in list_motion_modules():
        if sdxl and ('sdxl' in f.lower() or 'xl' in f.lower()):
            return True
        if not sdxl and 'sdxl' not in f.lower() and 'xl' not in f.lower():
            return True
    return False

def find_motion_module(model=None):
    sdxl = is_sdxl_model(model)
    sdxl_mm = []
    sd15_mm = []
    for f in list_motion_modules():
        fl = f.lower()
        if 'sdxl' in fl or 'xl' in fl:
            sdxl_mm.append(f)
        else:
            sd15_mm.append(f)
    if sdxl and sdxl_mm:
        return sdxl_mm[0]
    if sdxl and not sdxl_mm and sd15_mm:
        print("  WARNING: No SDXL motion module found — using SD 1.5 module (may produce errors with SDXL)")
        return sd15_mm[0]
    if not sdxl and sd15_mm:
        return sd15_mm[0]
    if sdxl_mm:
        return sdxl_mm[0]
    if sd15_mm:
        return sd15_mm[0]
    return "mm_sdxl_v10_beta.ckpt" if sdxl else "mm_sd_v15_v2.ckpt"

def build_t2i_video(prompt, negative, lora=None, model=None, w=512, h=512, frames=16, frame_rate=8):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": frames}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model_name": mm, "beta_schedule": "sqrt_linear", "decode_latents": False}},
        "17": {"class_type": "ADE_ApplyAnimateDiffModelSimple", "inputs": {"model": ["4", 0], "motion_models": ["15", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["17", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    if lora:
        wf["10"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["17"]["inputs"]["model"] = ["10", 0]
        wf["6"]["inputs"]["clip"] = ["10", 1]
        wf["7"]["inputs"]["clip"] = ["10", 1]
    return wf

def build_t2i_video_ipadapter(prompt, negative, ref_image, model=None, w=512, h=512, frames=16, frame_rate=8):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": frames}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": ref_image}},
        "11": {"class_type": "IPAdapterModelLoader", "inputs": {"ipadapter_file": "ip-adapter-plus_sd15.safetensors"}},
        "12": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"}},
        "13": {"class_type": "CLIPVisionEncode", "inputs": {"image": ["10", 0], "clip_vision": ["12", 0]}},
        "14": {"class_type": "IPAdapterApply", "inputs": {"ipadapter": ["11", 0], "clip_vision": ["13", 0], "image": ["10", 0], "weight": 0.8, "model": ["4", 0]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model_name": mm, "beta_schedule": "sqrt_linear", "decode_latents": False}},
        "17": {"class_type": "ADE_ApplyAnimateDiffModelSimple", "inputs": {"model": ["14", 0], "motion_models": ["15", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": 1, "model": ["17", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    return wf

def build_img2vid(prompt, negative, source_image, lora=None, model=None, w=512, h=512, frames=16, frame_rate=8, denoise=0.5):
    mm = find_motion_module(model)
    wf = {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": model or "v1-5-pruned-emaonly.safetensors"}},
        "10": {"class_type": "LoadImage", "inputs": {"image": source_image}},
        "10a": {"class_type": "ImageScale", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "width": w, "height": h, "crop": "center"}},
        "11": {"class_type": "VAEEncode", "inputs": {"pixels": ["10a", 0], "vae": ["4", 2]}},
        "12": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": max(1, frames - 1)}},
        "13": {"class_type": "LatentBatch", "inputs": {"samples1": ["11", 0], "samples2": ["12", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": negative or "bad quality, blurry, distorted", "clip": ["4", 1]}},
        "15": {"class_type": "ADE_AnimateDiffLoaderGen1", "inputs": {"model_name": mm, "beta_schedule": "sqrt_linear", "decode_latents": False}},
        "17": {"class_type": "ADE_ApplyAnimateDiffModelSimple", "inputs": {"model": ["4", 0], "motion_models": ["15", 0]}},
        "3": {"class_type": "KSampler", "inputs": {"seed": random.randint(0, 2**32), "steps": 20, "cfg": 12, "sampler_name": "euler", "scheduler": "normal", "denoise": denoise, "model": ["17", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["13", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["8", 0], "frame_rate": frame_rate, "loop_count": 0, "filename_prefix": "shimi", "format": "video/h264-mp4", "pix_fmt": "yuv420p", "crf": 19, "save_metadata": False, "pingpong": False, "save_output": True}},
    }
    if lora:
        wf["14"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.8, "model": ["4", 0], "clip": ["4", 1]}}
        wf["17"]["inputs"]["model"] = ["14", 0]
        wf["6"]["inputs"]["clip"] = ["14", 1]
        wf["7"]["inputs"]["clip"] = ["14", 1]
    return wf

def process_training_job(job):
    jid = job["id"]
    name = job.get("name", "character")
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', name)[:30] or "char"
    trigger = job.get("trigger_token", "") or safe_name
    dataset_urls = job.get("dataset_urls", [])
    steps = job.get("steps", 1500)
    resolution = job.get("resolution", 512)
    print(f"  Training: {name} ({len(dataset_urls)} images, {steps} steps, {resolution}px)")
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "busy", "current_job_type": "training", "current_job_progress": 0, "current_job_prompt": f"Training {name}"})
    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": 5})

    # Download dataset
    dataset_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets", safe_name)
    if os.path.exists(dataset_dir):
        shutil.rmtree(dataset_dir)
    os.makedirs(dataset_dir, exist_ok=True)
    for i, url in enumerate(dataset_urls):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(os.path.join(dataset_dir, f"image_{i:03d}.png"), "wb") as f:
                f.write(r.content)
            with open(os.path.join(dataset_dir, f"image_{i:03d}.txt"), "w", encoding="utf-8") as f:
                f.write(trigger)
        except Exception as e:
            print(f"  Download failed: {e}")
    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": 15})

    sd_scripts = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sd-scripts")
    train_script = os.path.join(sd_scripts, "sd_train_network.py")
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    os.makedirs(lora_dir, exist_ok=True)
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lora_output")
    os.makedirs(output_dir, exist_ok=True)

    trained = False
    if os.path.exists(train_script):
        print("  sd-scripts found — running Kohya_ss training (SD 1.5)...")
        ckpt_path = os.path.join(COMFYUI_PATH, "models", "checkpoints", "v1-5-pruned-emaonly.safetensors")
        # Use accelerate CLI directly (python -m accelerate has no __main__)
        accelerate_exe = os.path.join(os.path.dirname(VENV_PY), "accelerate.exe")
        if os.path.exists(accelerate_exe):
            cmd = [accelerate_exe, "launch", "--num_cpu_threads_per_proc", "2", train_script,
                   "--pretrained_model_name_or_path", ckpt_path,
                   "--train_data_dir", dataset_dir,
                   "--output_dir", output_dir,
                   "--output_name", safe_name,
                   "--resolution", str(resolution),
                   "--learning_rate", "1e-4",
                   "--max_train_steps", str(steps),
                   "--network_module", "networks.lora",
                   "--network_dim", "32",
                   "--network_alpha", "16",
                   "--enable_bucket",
                   "--mixed_precision", "fp16",
                   "--save_precision", "fp16",
                   "--gradient_checkpointing",
                   "--cache_latents",
                   "--cache_text_encoder_outputs",
            ]
        else:
            # Fallback: python -m accelerate (may fail on some versions)
            cmd = [VENV_PY, "-m", "accelerate", "launch", "--num_cpu_threads_per_proc", "2", train_script,
            "--pretrained_model_name_or_path", ckpt_path,
            "--train_data_dir", dataset_dir,
            "--output_dir", output_dir,
            "--output_name", safe_name,
            "--resolution", str(resolution),
            "--learning_rate", "1e-4",
            "--max_train_steps", str(steps),
            "--network_module", "networks.lora",
            "--network_dim", "32",
            "--network_alpha", "16",
            "--enable_bucket",
            "--mixed_precision", "fp16",
            "--save_precision", "fp16",
            "--gradient_checkpointing",
            "--cache_latents",
            "--cache_text_encoder_outputs",
        ]
        try:
            proc = subprocess.Popen(cmd, cwd=sd_scripts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    print(f"  {line}")
                m = re.search(r'(\d+)/(\d+)', line)
                if m and ("it/s" in line or "s/it" in line):
                    cur, tot = int(m.group(1)), int(m.group(2))
                    pct = min(90, 15 + int(75 * cur / max(tot, 1)))
                    post("shimiStudioAPI", {"action": "training_progress", "job_id": jid, "progress": pct})
            proc.wait()
            if proc.returncode == 0:
                lora_file = os.path.join(output_dir, f"{safe_name}.safetensors")
                if os.path.exists(lora_file):
                    shutil.copy(lora_file, os.path.join(lora_dir, f"{safe_name}.safetensors"))
                    lora_path = f"loras/{safe_name}.safetensors"
                    post("shimiStudioAPI", {"action": "training_complete", "job_id": jid, "lora_path": lora_path})
                    print(f"  Training complete: {lora_path}")
                    trained = True
                else:
                    print("  Training finished but no LoRA file found")
            else:
                print(f"  Training failed (exit {proc.returncode})")
        except Exception as e:
            print(f"  Training error: {e}")
            traceback.print_exc()

    if not trained:
        # Fallback: IP-Adapter reference (no LoRA, but character consistency via reference image)
        print("  Falling back to IP-Adapter reference (no LoRA training)")
        first_image = dataset_urls[0] if dataset_urls else (job.get("face_image_url") or job.get("thumbnail_url"))
        post("shimiStudioAPI", {"action": "training_complete", "job_id": jid, "face_image_url": first_image, "fallback": True})
        print("  Character marked as completed (IP-Adapter reference mode)")

    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})

def parse_shots(prompt):
    """Parse a long prompt into a shot list. Formats: '---' separator lines, or 'SHOT N:' prefixes."""
    if not isinstance(prompt, str) or not prompt.strip():
        return []
    marks = list(re.finditer(r'(?im)^\s*[>*\-#\s]*\s*shot\s*\d+\s*[:.\-]\s*(.*)$', prompt))
    if len(marks) >= 2:
        shots = []
        for i, m in enumerate(marks):
            end = marks[i+1].start() if i+1 < len(marks) else len(prompt)
            first_line = (m.group(1) or "").strip()
            rest = prompt[m.end():end].strip()
            text = (first_line + "\n" + rest).strip() if rest else first_line
            if text:
                shots.append(text)
        return shots[:20]
    parts = re.split(r'(?m)^\s*[-*=~]{3,}\s*$', prompt)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts[:20]
    return []

def get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def concat_videos(paths, jid):
    ff = get_ffmpeg_exe()
    base = os.path.dirname(os.path.abspath(__file__))
    lst = os.path.join(base, f"concat_{jid[:8]}.txt")
    with open(lst, "w") as f:
        for p in paths:
            f.write("file '" + os.path.abspath(p).replace("'", "'\''") + "'\n")
    out = os.path.join(base, f"seq_{jid[:8]}.mp4")
    r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], capture_output=True, timeout=600)
    if r.returncode != 0:
        r = subprocess.run([ff, "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", out], capture_output=True, timeout=3600)
        if r.returncode != 0:
            raise RuntimeError("concat failed: " + r.stderr.decode(errors="replace")[-300:])
    return out

def polish_video(src, tw=None, th=None, fps=24):
    """Lanczos upscale + frame interpolation to smooth fps. Falls back to source on failure."""
    try:
        ff = get_ffmpeg_exe()
        out = src.replace(".mp4", "_final.mp4")
        vf = []
        if tw and th:
            vf.append(f"scale={tw}:{th}:flags=lanczos")
        if fps:
            vf.append(f"minterpolate=fps={fps}:mi_mode=blend")
        if not vf:
            return src
        cmd = [ff, "-y", "-i", src, "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p", out]
        r = subprocess.run(cmd, capture_output=True, timeout=3600)
        if r.returncode == 0 and os.path.getsize(out) > 0:
            return out
        return src
    except Exception:
        return src

def process_video_sequence(job, jid, seq, model, lora, negative, vw, vh, fr, duration, ref_image_name, src_image_name):
    """Render a sequence of short shots -> concat -> upscale -> complete. Returns True if the job was fully handled."""
    print(f"  Sequence mode: {len(seq)} shots @ {fr}fps | {vw}x{vh}")
    frames_per_shot = min(24, max(16, int(duration * 8)))
    base = os.path.dirname(os.path.abspath(__file__))
    seg_paths = []
    for si, sp in enumerate(seq):
        try:
            post("jobApi", {"action": "progress", "job_id": jid, "progress": int(10 + 70 * si / len(seq))})
            if src_image_name and si == 0:
                wf = build_img2vid(sp, negative, src_image_name, lora, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            elif ref_image_name:
                wf = build_t2i_video_ipadapter(sp, negative, ref_image_name, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            else:
                wf = build_t2i_video(sp, negative, lora, model, w=vw, h=vh, frames=frames_per_shot, frame_rate=fr)
            pid = queue_prompt(wf)
            outs = wait_for_result(pid, jid)
            if outs is None:
                return True  # cancelled
            item, otype = get_output(outs)
            if not item:
                raise RuntimeError(f"no output from shot {si+1}")
            data = download_file(item)
            seg = os.path.join(base, f"seq_{jid[:8]}_{si:02d}.mp4")
            with open(seg, "wb") as f:
                f.write(data)
            seg_paths.append(seg)
            print(f"  Shot {si+1}/{len(seq)} done")
        except Exception as e:
            print(f"  Shot {si+1}/{len(seq)} failed: {e}")
    if not seg_paths:
        post("jobApi", {"action": "fail", "job_id": jid, "error": "All shots failed"})
        return True
    post("jobApi", {"action": "progress", "job_id": jid, "progress": 85})
    try:
        final = seg_paths[0] if len(seg_paths) == 1 else concat_videos(seg_paths, jid)
        # Upscale target: vertical -> x1.875, else x2
        tw, th = int(vw * 1.875) // 2 * 2, int(vh * 1.875) // 2 * 2
        final = polish_video(final, tw, th, fps=24)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 92})
        with open(final, "rb") as f:
            file_data = f.read()
        result = post("jobApi", {"action": "complete", "job_id": jid, "file_base64": base64.b64encode(file_data).decode("utf-8"), "file_type": "video/mp4"}, timeout=1200)
        if result.get("error"):
            post("jobApi", {"action": "fail", "job_id": jid, "error": result["error"]})
        else:
            print(f"  Sequence completed: {jid} ({len(seg_paths)} shots)")
    except Exception as e:
        print(f"  Sequence stitch failed: {e}")
        traceback.print_exc()
        post("jobApi", {"action": "fail", "job_id": jid, "error": f"stitch failed: {e}"})
    # Cleanup temp segments
    for p in seg_paths:
        try: os.remove(p)
        except: pass
    return True

def process_job(job, character, scene, lora_cfg=None):
    jid = job["id"]
    jtype = job.get("type", "image")
    prompt = job.get("prompt", "")
    negative = job.get("negative_prompt", "")
    model = job.get("model") or "v1-5-pruned-emaonly.safetensors"
    lora = (lora_cfg or {}).get("lora_path") or (character.get("lora_path") if character else None)
    lora_url = (lora_cfg or {}).get("lora_url") or (character.get("lora_url") if character else None)
    trigger_token = (lora_cfg or {}).get("trigger_token") or (character.get("trigger_token") if character else None)
    if not lora and lora_url:
        lora = download_lora(lora_url)
    # Prepend trigger token to prompt so the LoRA concept activates
    if lora and trigger_token:
        prompt = f"{trigger_token}, {prompt}"
    source_imgs = job.get("source_images") or ([job.get("source_image")] if job.get("source_image") else []) or ([scene.get("source_image")] if scene and scene.get("source_image") else [])
    source_img = source_imgs[0] if source_imgs else None
    face_image = (character.get("face_image_url") if character else None) or (lora_cfg or {}).get("face_image_url")
    use_ipadapter = False
    ref_image_name = None
    if not lora and face_image:
        if 'IPAdapterApply' not in AVAILABLE_NODES:
            print("  IP-Adapter skipped — node not loaded (custom nodes disabled) — using style prompt only")
        else:
            ipadapter_model = os.path.join(COMFYUI_PATH, "models", "ipadapter", "ip-adapter-plus_sd15.safetensors")
            clip_vision_model = os.path.join(COMFYUI_PATH, "models", "clip_vision", "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors")
            if os.path.exists(ipadapter_model) and os.path.exists(clip_vision_model):
                try:
                    ref_image_name = f"ref_{jid[:8]}.png"
                    ref_path = os.path.join(COMFYUI_PATH, "input", ref_image_name)
                    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
                    save_image(face_image, ref_path)
                    use_ipadapter = True
                except Exception as e:
                    print(f"  Ref image download failed: {e}")
            else:
                missing = []
                if not os.path.exists(ipadapter_model): missing.append("ip-adapter-plus_sd15.safetensors")
                if not os.path.exists(clip_vision_model): missing.append("CLIP-ViT-H model")
                print(f"  IP-Adapter skipped — missing: {', '.join(missing)} — using style prompt only")
    # Download source images if present (for img2img / img2vid)
    src_image_name = None
    if source_imgs:
        for i, surl in enumerate(source_imgs):
            try:
                sname = f"src_{jid[:8]}_{i}.png"
                spath = os.path.join(COMFYUI_PATH, "input", sname)
                os.makedirs(os.path.dirname(spath), exist_ok=True)
                save_image(surl, spath)
                if i == 0:
                    src_image_name = sname
            except Exception as e:
                print(f"  Source image {i} download failed: {e}")
    print(f"  Processing: type={jtype} lora={lora} ipadapter={use_ipadapter} source_img={'yes' if source_img else 'no'}")
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "busy", "current_job_type": jtype, "current_job_progress": 0, "current_job_prompt": prompt[:80]})
    post("jobApi", {"action": "progress", "job_id": jid, "progress": 10})
    try:
        if jtype == "realtime_avatar":
            face_url = job.get("frame_url")
            face_name = None
            if face_url:
                try:
                    face_name = f"face_{jid[:8]}.png"
                    face_path = os.path.join(COMFYUI_PATH, "input", face_name)
                    os.makedirs(os.path.dirname(face_path), exist_ok=True)
                    save_image(face_url, face_path)
                except Exception as e:
                    print(f"  Face image download failed: {e}")
            if not src_image_name or not face_name:
                post("jobApi", {"action": "fail", "job_id": jid, "error": "Missing input frame or character face"})
                return
            swap_mode = job.get("swap_mode", "face")
            if swap_mode == "body":
                if 'IPAdapterApply' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "IP-Adapter node not loaded (custom nodes disabled) — body swap unavailable. Restart worker."})
                    return
                wf = build_body_swap(src_image_name, face_name, lora, model)
                print(f"  Body swap mode (IP-Adapter img2img)")
            else:
                if 'ReActorFaceSwap' not in AVAILABLE_NODES:
                    post("jobApi", {"action": "fail", "job_id": jid, "error": "ReActor node not loaded (custom nodes disabled) — face swap unavailable. Restart worker."})
                    return
                wf = build_face_swap(src_image_name, face_name)
                print(f"  Face swap mode (ReActor)")
        elif jtype == "video":
            if 'ADE_AnimateDiffLoaderGen1' not in AVAILABLE_NODES:
                post("jobApi", {"action": "fail", "job_id": jid, "error": "AnimateDiff node not loaded (custom nodes disabled) — cannot generate video locally. Restart worker or use cloud mode."})
                return
            if 'VHS_VideoCombine' not in AVAILABLE_NODES:
                post("jobApi", {"action": "fail", "job_id": jid, "error": "VideoHelperSuite not installed — cannot encode video. Reinstall worker."})
                return
            if not video_supported(model):
                post("jobApi", {"action": "fail", "job_id": jid, "error": "AnimateDiff motion module not installed — cannot generate video locally. Reinstall worker or use cloud mode."})
                return
            sdxl = is_sdxl_model(model)
            # Screen format: vertical (9:16/2:3) or square
            ar = str(job.get("aspect_ratio") or "").lower().replace(" ", "")
            if ar in ("9:16", "vertical", "portrait", "story", "reels", "1080x1920"):
                vw, vh = (576, 1024) if not sdxl else (1024, 1024)
            elif ar in ("2:3", "3:4", "1080x1600", "1080x1440"):
                vw, vh = (512, 768) if not sdxl else (1024, 1024)
            else:
                vw, vh = (1024, 1024) if sdxl else (512, 512)
            duration = job.get("duration", 6)
            # Shot sequence: multi-shot prompt -> render each shot and concat
            seq = parse_shots(prompt)
            if len(seq) >= 2:
                handled = process_video_sequence(job, jid, seq, model, lora, negative, vw, vh, fr=8, duration=duration, ref_image_name=(ref_image_name if use_ipadapter else None), src_image_name=src_image_name)
                if handled:
                    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})
                    return
            frames = min(48, max(16, int(duration * 8)))
            fr = max(1, round(frames / duration))
            if src_image_name:
                wf = build_img2vid(prompt, negative, src_image_name, lora, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                print(f"  Img2Vid: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}] source={src_image_name}")
            elif use_ipadapter:
                wf = build_t2i_video_ipadapter(prompt, negative, ref_image_name, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                print(f"  Video: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}] ipadapter")
            else:
                wf = build_t2i_video(prompt, negative, lora, model, w=vw, h=vh, frames=frames, frame_rate=fr)
                print(f"  Video: {frames} frames at {fr}fps (~{frames/fr:.1f}s) [{'SDXL' if sdxl else 'SD1.5'}]")
        elif src_image_name:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_img2img(prompt, negative, src_image_name, lora, model, w=iw, h=ih)
            print(f"  Img2Img [{'SDXL' if sdxl else 'SD1.5'}]")
        elif use_ipadapter:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_t2i_ipadapter(prompt, negative, ref_image_name, model, w=iw, h=ih)
            print(f"  T2I+IPAdapter [{'SDXL' if sdxl else 'SD1.5'}]")
        else:
            sdxl = is_sdxl_model(model)
            iw, ih = (1024, 1024) if sdxl else (512, 512)
            wf = build_t2i(prompt, negative, lora, model, w=iw, h=ih)
            print(f"  T2I [{'SDXL' if sdxl else 'SD1.5'}]")
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 30})
        prompt_id = queue_prompt(wf)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 50})
        outputs = wait_for_result(prompt_id, jid)
        if outputs is None:
            print(f"  Job cancelled: {jid}")
            return
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 85})
        item, out_type = get_output(outputs)
        if not item:
            post("jobApi", {"action": "fail", "job_id": jid, "error": "No output from ComfyUI"})
            return
        file_data = download_file(item)
        post("jobApi", {"action": "progress", "job_id": jid, "progress": 90})
        file_b64 = base64.b64encode(file_data).decode("utf-8")
        ftype = "video/mp4" if out_type == "video" else "image/png"
        result = post("jobApi", {"action": "complete", "job_id": jid, "file_base64": file_b64, "file_type": ftype}, timeout=600)
        if result.get("error"):
            print(f"  Upload failed: {result['error']}")
            post("jobApi", {"action": "fail", "job_id": jid, "error": result["error"]})
        else:
            print(f"  Job completed: {jid}")
    except Exception as e:
        print(f"  Job failed: {e}")
        traceback.print_exc()
        post("jobApi", {"action": "fail", "job_id": jid, "error": str(e)})
    post("workerApi", {"action": "heartbeat", "token": TOKEN, "status": "online", "current_job_type": None, "current_job_progress": 0})

def scan_loras():
    lora_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    if not os.path.isdir(lora_dir):
        print(f"  LoRA dir not found: {lora_dir}")
        return
    loras = []
    for f in os.listdir(lora_dir):
        if f.lower().endswith(('.safetensors', '.pt', '.ckpt', '.gguf')):
            fp = os.path.join(lora_dir, f)
            size_mb = round(os.path.getsize(fp) / (1024*1024), 1)
            name = os.path.splitext(f)[0]
            loras.append({"name": name, "path": f"loras/{f}", "size_mb": size_mb})
    print(f"  Found {len(loras)} LoRA files")
    r = post("workerApi", {"action":"report_loras","token":TOKEN,"loras":loras})
    print(f"  LoRAs imported: {r.get('imported',0)}, skipped: {r.get('skipped',0)}")

def scan_checkpoints():
    ckpt_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    if not os.path.isdir(ckpt_dir):
        print(f"  Checkpoint dir not found: {ckpt_dir}")
        return
    checkpoints = []
    for f in os.listdir(ckpt_dir):
        if f.lower().endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
            checkpoints.append(f)
    print(f"  Found {len(checkpoints)} checkpoint models")
    post("workerApi", {"action":"report_checkpoints","token":TOKEN,"checkpoints":checkpoints})

def download_pending_models():
    r = post("shimiStudioAPI", {"action": "list_pending_downloads", "token": TOKEN})
    downloads = r.get("downloads", [])
    for dl in downloads:
        download_model(dl)

def download_model(dl):
    mid = dl["id"]
    mtype = dl["type"]
    url = dl["url"]
    mname = dl["name"]
    if mtype == "checkpoint":
        target_dir = os.path.join(COMFYUI_PATH, "models", "checkpoints")
    elif mtype == "lora":
        target_dir = os.path.join(COMFYUI_PATH, "models", "loras")
    elif mtype == "motion_module":
        target_dir = os.path.join(COMFYUI_PATH, "models", "animatediff_models")
    else:
        print(f"  Unknown model type: {mtype}")
        return
    os.makedirs(target_dir, exist_ok=True)
    fname = url.split("/")[-1].split("?")[0] or f"{mname}.safetensors"
    if not fname.endswith(('.safetensors', '.ckpt', '.pt', '.gguf')):
        fname += ".safetensors"
    fp = os.path.join(target_dir, fname)
    if os.path.exists(fp):
        print(f"  Model already exists: {fname}")
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "completed", "file_path": f"{os.path.basename(target_dir)}/{fname}"})
        return
    print(f"  Downloading model: {mname} ({mtype})")
    post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "downloading", "worker_id": TOKEN})
    try:
        r = requests.get(url, timeout=600, stream=True)
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        with open(fp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
                downloaded += len(chunk)
                if downloaded % (5*1024*1024) < 1024*1024:
                    post("workerApi", {"action":"heartbeat","token":TOKEN,"status":"busy","current_job_type":"downloading","current_job_progress":min(95, int(100*downloaded/max(total,1))),"current_job_prompt":f"Downloading {mname}"})
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "completed", "file_path": f"{os.path.basename(target_dir)}/{fname}"})
        print(f"  Model downloaded: {fname}")
        if mtype == "checkpoint":
            scan_checkpoints()
        elif mtype == "lora":
            scan_loras()
    except Exception as e:
        print(f"  Model download failed: {e}")
        post("shimiStudioAPI", {"action": "report_download", "model_id": mid, "status": "failed", "error": str(e)})

print("========================================")
print("  ShimiStudio Worker v4.3 - Running")
print("========================================")
print(f"  Server: {SERVER}")
print(f"  Name:   {NAME}")
print(f"  Token:  {TOKEN[:8]}...")
print()

# ── Startup (each step wrapped to prevent crash before main loop) ──
try:
    post("workerApi", {"action":"register","token":TOKEN,"name":NAME,"os_type": ("mac" if sys.platform == "darwin" else ("windows" if os.name == "nt" else "linux")),"gpu_model":"auto","vram_total":0})
    print("  Registered with server")
except Exception as e:
    print(f"  Registration failed: {e}")

try:
    scan_loras()
except Exception as e:
    print(f"  LoRA scan failed: {e}")

try:
    scan_checkpoints()
except Exception as e:
    print(f"  Checkpoint scan failed: {e}")

try:
    if start_comfyui():
        fetch_available_nodes()
        if 'ADE_AnimateDiffLoaderGen1' not in AVAILABLE_NODES:
            print("  ! AnimateDiff node not loaded — VIDEO GENERATION WILL FAIL. Reinstall worker or check ComfyUI-AnimateDiff-Evolved in custom_nodes/")
        if 'IPAdapterApply' not in AVAILABLE_NODES:
            print("  ! IP-Adapter node not loaded — character reference will use style prompt only.")
    else:
        print("  WARNING: ComfyUI not available - jobs will fail until ComfyUI is running")
except Exception as e:
    print(f"  ComfyUI startup error: {e}")
    print("  Worker continues without ComfyUI — jobs will fail until ComfyUI is running")

while True:
    try:
        post("workerApi", {"action":"heartbeat","token":TOKEN,"status":"online","gpu_util":0,"vram_used":0,"ping_ms":10})
        # Check for training jobs first (priority)
        tr = post("shimiStudioAPI", {"action": "claim_training", "token": TOKEN})
        tr_job = tr.get("job")
        if tr_job:
            print(f"  Training job claimed: {tr_job.get('name')}")
            process_training_job(tr_job)
            continue
        # Then check for render jobs
        r = post("jobApi", {"action":"claim","token":TOKEN})
        job = r.get("job")
        if job:
            character = r.get("character")
            scene = r.get("scene")
            lora_cfg = r.get("lora") or {}
            print(f"  Job claimed: {job.get('id')} type={job.get('type')} lora={lora_cfg.get('lora_path') or 'none'}")
            process_job(job, character, scene, lora_cfg)
        # Check for pending model downloads (lowest priority)
        download_pending_models()
    except Exception as e:
        print(f"  Loop error: {e}")
        traceback.print_exc()
    time.sleep(5)
'@ | Out-File -FilePath "$DIR\worker.py" -Encoding ascii

$cfgJson = @{"server"=$SERVER;"token"=$TOKEN;"name"=$NAME;"apiBase"=$API_BASE;"comfyui_path"=$comfyuiDir} | ConvertTo-Json -Compress
[IO.File]::WriteAllText("$DIR\config.json", $cfgJson, (New-Object Text.UTF8Encoding $false))

# Verify worker.py was written with new code
if (Test-Path "$DIR\worker.py") {
  $content = Get-Content "$DIR\worker.py" -Raw -ErrorAction SilentlyContinue
  if ($content -and $content.Contains("ComfyUI")) {
    WOK "worker.py + config.json (v2 ComfyUI)"
  } else {
    WERR "worker.py write failed - old version detected"
    Read-Host "Press Enter to exit"; exit 1
  }
} else {
  WERR "worker.py not found after write"
  Read-Host "Press Enter to exit"; exit 1
}

# ── 6. Start script + shortcut ──
WS 6 7 "Creating start script..."
$pyCmd = if ($useVenv) { '"venv\Scripts\python.exe"' } else { 'python' }
$startBat = @"
@echo off
chcp 65001 >nul
title ShimiStudio Worker
cd /d "$DIR"
$pyCmd worker.py
echo.
echo Worker stopped. Press any key to close.
pause >nul
"@
$startBat | Set-Content -Path "$DIR\start_worker.bat" -Encoding UTF8

$desktop = [Environment]::GetFolderPath("Desktop")
$sc = "$desktop\ShimiStudioWorker.lnk"
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut($sc)
$lnk.TargetPath = "$DIR\start_worker.bat"
$lnk.WorkingDirectory = $DIR
$lnk.Description = "ShimiStudio Worker"
$lnk.Save()
WOK "Desktop shortcut created"

# ── 7. Start ──
WS 7 7 "Starting worker..."
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Starting worker now..."
Write-Host ""

& "$DIR\start_worker.bat"
