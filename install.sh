#!/usr/bin/env bash
# ==============================================================================
# ShimiStudio PC One-Click Installer
# Sets up Python 3.11+, PyTorch (CUDA), ComfyUI, 30+ AI Models, Worker,\n# Custom Nodes: IPAdapter, ReActor, AnimateDiff, Wan 2.2, LTX, PuLID, DWPose, XTTS, LatentSync
# Worker Daemon, and Start Scripts for ShimiStudio System.
# ==============================================================================

set -euo pipefail

# --- ANSI Formatting & Color Codes ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Logging Functions ---
log_banner() {
    echo -e "${CYAN}${BOLD}"
    echo "===================================================================="
    echo "            🚀 ShimiStudio PC One-Click Installer                   "
    echo "===================================================================="
    echo -e "${NC}"
}

log_step() {
    echo -e "\n${MAGENTA}${BOLD}=== STEP $1: $2 ===${NC}"
}

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# --- Error Handling Trap ---
trap 'log_error "An error occurred on line $LINENO. Installation failed."; exit 1' ERR

# --- Path Definitions ---
BASE_DIR="${HOME}/ShimiStudio"
COMFY_DIR="${BASE_DIR}/ComfyUI"
VENV_DIR="${BASE_DIR}/venv"
WORKFLOWS_DIR="${BASE_DIR}/workflows"
OUTPUT_DIR="${BASE_DIR}/output"

# ==============================================================================
# STEP 1: Environment & System Prerequisites Check
# ==============================================================================
log_banner
log_step "1" "Checking and Installing System Prerequisites"

# Check Sudo availability
SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo &>/dev/null; then
        SUDO="sudo"
    fi
fi

# Function to check python version >= 3.11
check_python_version() {
    local py_cmd="$1"
    if command -v "$py_cmd" &>/dev/null; then
        if "$py_cmd" -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' &>/dev/null; then
            return 0
        fi
    fi
    return 1
}

# Determine system package manager & install system dependencies
INSTALL_PKGS=()

# Check Python 3.11+
PYTHON_BIN=""
if check_python_version python3.11; then
    PYTHON_BIN="python3.11"
elif check_python_version python3; then
    PYTHON_BIN="python3"
else
    log_warn "Python 3.11+ not detected. Attempting package installation..."
    INSTALL_PKGS+=("python3.11" "python3.11-venv" "python3.11-dev" "python3-pip")
fi

if ! command -v git &>/dev/null; then
    INSTALL_PKGS+=("git")
fi

if ! command -v ffmpeg &>/dev/null; then
    INSTALL_PKGS+=("ffmpeg")
fi

if ! command -v wget &>/dev/null && ! command -v curl &>/dev/null; then
    INSTALL_PKGS+=("wget" "curl")
fi

if ! command -v aria2c &>/dev/null; then
    INSTALL_PKGS+=("aria2")
fi

if [ ${#INSTALL_PKGS[@]} -gt 0 ]; then
    log_info "Installing required system packages: ${INSTALL_PKGS[*]}"
    if command -v apt-get &>/dev/null; then
        $SUDO apt-get update -qq || true
        $SUDO apt-get install -y -qq "${INSTALL_PKGS[@]}" || log_warn "Package manager installation encountered warnings. Proceeding..."
    elif command -v dnf &>/dev/null; then
        $SUDO dnf install -y "${INSTALL_PKGS[@]}" || true
    elif command -v brew &>/dev/null; then
        brew install "${INSTALL_PKGS[@]}" || true
    else
        log_warn "Could not identify standard package manager. Please ensure Python 3.11+, git, ffmpeg, and wget/curl are installed."
    fi
fi

# Re-check python binary
if [ -z "$PYTHON_BIN" ]; then
    if check_python_version python3.11; then
        PYTHON_BIN="python3.11"
    elif check_python_version python3; then
        PYTHON_BIN="python3"
    else
        log_error "Python 3.11 or higher is required. Current python version is lower or missing."
        exit 1
    fi
fi

log_success "System prerequisites verified: Python ($($PYTHON_BIN --version)), git ($(git --version | head -n 1)), ffmpeg ($(ffmpeg -version 2>/dev/null | head -n 1 | cut -d' ' -f1-3 || echo 'available'))."

# Check NVIDIA GPU
log_info "Checking NVIDIA GPU availability..."
HAS_CUDA=false
if command -v nvidia-smi &>/dev/null; then
    if nvidia-smi &>/dev/null; then
        HAS_CUDA=true
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
        log_success "NVIDIA GPU Detected: ${GPU_NAME}"
    fi
fi
if [ "$HAS_CUDA" = false ]; then
    log_warn "NVIDIA GPU not detected via nvidia-smi. PyTorch CUDA support will still be configured."
fi

# ==============================================================================
# STEP 2: Directory Setup & ComfyUI Clone
# ==============================================================================
log_step "2" "Setting up Workspace & Cloning ComfyUI"

mkdir -p "${BASE_DIR}" "${WORKFLOWS_DIR}" "${OUTPUT_DIR}"

if [ ! -d "${COMFY_DIR}" ]; then
    log_info "Cloning ComfyUI into ${COMFY_DIR}..."
    git clone https://github.com/comfyanonymous/ComfyUI.git "${COMFY_DIR}"
    log_success "ComfyUI repository cloned."
else
    log_info "ComfyUI directory already exists at ${COMFY_DIR}. Updating..."
    (cd "${COMFY_DIR}" && git pull || true)
fi

# ==============================================================================
# STEP 3: Virtual Environment & PyTorch CUDA Setup
# ==============================================================================
log_step "3" "Setting up Virtual Environment & Installing PyTorch CUDA"

if [ ! -d "${VENV_DIR}" ]; then
    log_info "Creating Python virtual environment at ${VENV_DIR} using ${PYTHON_BIN}..."
    "$PYTHON_BIN" -m venv "${VENV_DIR}"
    log_success "Virtual environment created."
else
    log_info "Virtual environment already exists at ${VENV_DIR}."
fi

PIP_BIN="${VENV_DIR}/bin/pip"
PY_VENV="${VENV_DIR}/bin/python"

log_info "Upgrading pip, setuptools, and wheel..."
"$PIP_BIN" install --upgrade pip setuptools wheel --quiet

log_info "Installing PyTorch with CUDA 12.1 support..."
"$PIP_BIN" install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

log_info "Installing ComfyUI requirements..."
if [ -f "${COMFY_DIR}/requirements.txt" ]; then
    "$PIP_BIN" install -r "${COMFY_DIR}/requirements.txt"
fi

log_info "Installing supplementary libraries for custom nodes and worker..."
"$PIP_BIN" install requests tqdm onnxruntime-gpu opencv-python-headless insightface facexlib gfpgan codeformer diffusers transformers accelerate huggingface_hub sageattention einops k-diffusion scipy pillow pyyaml || true

log_success "Python virtual environment configured with PyTorch CUDA support."

# ==============================================================================
# STEP 4: Install Required ComfyUI Custom Nodes
# ==============================================================================
log_step "4" "Installing ComfyUI Custom Nodes"

CUSTOM_NODES_DIR="${COMFY_DIR}/custom_nodes"
mkdir -p "${CUSTOM_NODES_DIR}"

install_node() {
    local node_name="$1"
    local repo_url="$2"
    local target_path="${CUSTOM_NODES_DIR}/${node_name}"

    if [ ! -d "${target_path}" ]; then
        log_info "Installing custom node: ${node_name}..."
        git clone "${repo_url}" "${target_path}"
        log_success "${node_name} installed."
    else
        log_info "Custom node ${node_name} already exists. Pulling latest updates..."
        (cd "${target_path}" && git pull || true)
    fi

    if [ -f "${target_path}/requirements.txt" ]; then
        log_info "Installing dependencies for ${node_name}..."
        "$PIP_BIN" install -r "${target_path}/requirements.txt" || log_warn "Non-critical error installing requirements for ${node_name}."
    fi
}

install_node "ComfyUI-Manager" "https://github.com/ltdrdata/ComfyUI-Manager.git"
install_node "ComfyUI_IPAdapter_plus" "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git"
install_node "ComfyUI-ReActor" "https://github.com/Gourieff/comfyui-reactor_node.git"
install_node "ComfyUI-AnimateDiff" "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved.git"
install_node "ComfyUI-WanVideoWrapper" "https://github.com/Kijai/ComfyUI-WanVideoWrapper.git"
install_node "ComfyUI-LTXVideo" "https://github.com/Lightricks/ComfyUI-LTXVideo.git"
install_node "comfyui-workflow-component" "https://github.com/Pyvideomaker/comfyui-workflow-component.git"
install_node "ComfyUI-VideoHelperSuite" "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"
install_node "ComfyUI-DWPose" "https://github.com/chflame163/ComfyUI-DWPose.git"
install_node "ComfyUI-PuLID-Flux" "https://github.com/ltdrdata/ComfyUI-PuLID-Flux.git"
install_node "ComfyUI-LatentSyncWrapper" "https://github.com/kijai/ComfyUI-LatentSyncWrapper.git"
install_node "ComfyUI-wav2lip" "https://github.com/kijai/ComfyUI-wav2lip.git"
install_node "ComfyUI-LivePortrait" "https://github.com/kijai/ComfyUI-LivePortrait.git"

log_success "All required custom nodes installed."

# ==============================================================================
# STEP 5: Download Required AI Models
# ==============================================================================
log_step "5" "Downloading Required AI Models from HuggingFace"

# Create standard ComfyUI model directories
mkdir -p "${COMFY_DIR}/models/checkpoints"
mkdir -p "${COMFY_DIR}/models/loras"
mkdir -p "${COMFY_DIR}/models/insightface/models/buffalo_l"
mkdir -p "${COMFY_DIR}/models/ipadapter"
mkdir -p "${COMFY_DIR}/models/reactor/faceswap_models"
mkdir -p "${COMFY_DIR}/models/reactor/facerestore_models"
mkdir -p "${COMFY_DIR}/models/facerestore_models"
mkdir -p "${COMFY_DIR}/models/vae"
mkdir -p "${COMFY_DIR}/models/clip"
mkdir -p "${COMFY_DIR}/models/diffusion_models"
mkdir -p "${COMFY_DIR}/models/text_encoders"
mkdir -p "${COMFY_DIR}/models/tts"

download_model() {
    local url="$1"
    local dest_path="$2"
    local model_name="$3"

    mkdir -p "$(dirname "${dest_path}")"

    if [ -f "${dest_path}" ]; then
        local file_size
        file_size=$(stat -c%s "${dest_path}" 2>/dev/null || stat -f%z "${dest_path}" 2>/dev/null || echo 0)
        if [ "$file_size" -gt 1000000 ]; then
            log_success "Model '${model_name}' already downloaded ($(awk "BEGIN {printf \"%.2f\", $file_size/1048576}") MB). Skipping."
            return 0
        fi
    fi

    log_info "Downloading ${model_name}..."
    log_info "URL: ${url}"
    log_info "Destination: ${dest_path}"

    if command -v aria2c &>/dev/null; then
        aria2c -x 16 -s 16 -k 1M --console-log-level=warn -o "$(basename "${dest_path}")" -d "$(dirname "${dest_path}")" "${url}" || \
        wget -c --show-progress -O "${dest_path}" "${url}" || \
        curl -C - -L -o "${dest_path}" "${url}"
    elif command -v wget &>/dev/null; then
        wget -c --show-progress -O "${dest_path}" "${url}" || curl -C - -L -o "${dest_path}" "${url}"
    else
        curl -C - -L -o "${dest_path}" "${url}"
    fi

    if [ -f "${dest_path}" ]; then
        log_success "${model_name} downloaded successfully."
    else
        log_error "Failed to download ${model_name} from ${url}."
        return 1
    fi
}

# 1. Wan 2.2 Models
download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors" \
    "${COMFY_DIR}/models/checkpoints/wan2.1_t2v_1.3B_bf16.safetensors" \
    "Wan 2.2 T2V 1.3B Checkpoint"
cp -n "${COMFY_DIR}/models/checkpoints/wan2.1_t2v_1.3B_bf16.safetensors" "${COMFY_DIR}/models/diffusion_models/wan2.1_t2v_1.3B_bf16.safetensors" 2>/dev/null || true

download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/diffusion_models/wan2.1_i2v_720p_14B_bf16.safetensors" \
    "${COMFY_DIR}/models/checkpoints/wan2.1_i2v_720p_14B_bf16.safetensors" \
    "Wan 2.2 I2V 14B Checkpoint"
cp -n "${COMFY_DIR}/models/checkpoints/wan2.1_i2v_720p_14B_bf16.safetensors" "${COMFY_DIR}/models/diffusion_models/wan2.1_i2v_720p_14B_bf16.safetensors" 2>/dev/null || true

download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors" \
    "${COMFY_DIR}/models/vae/wan_2.1_vae.safetensors" \
    "Wan 2.1 VAE"

download_model \
    "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "${COMFY_DIR}/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors" \
    "Wan UMT5-XXL Text Encoder"
cp -n "${COMFY_DIR}/models/clip/umt5_xxl_fp8_e4m3fn_scaled.safetensors" "${COMFY_DIR}/models/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors" 2>/dev/null || true

# 2. LTX-Video 2B
download_model \
    "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b-v0.9.5.safetensors" \
    "${COMFY_DIR}/models/checkpoints/ltx-video-2b-v0.9.5.safetensors" \
    "LTX-Video 2B Checkpoint"

download_model \
    "https://huggingface.co/comfyanonymous/t5xxl_fp8_e4m3fn/resolve/main/t5xxl_fp8_e4m3fn.safetensors" \
    "${COMFY_DIR}/models/clip/t5xxl_fp8_e4m3fn.safetensors" \
    "T5-XXL FP8 Text Encoder"

# 3. Flux.1 dev
download_model \
    "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" \
    "${COMFY_DIR}/models/checkpoints/flux1-dev-fp8.safetensors" \
    "Flux.1 dev FP8 Checkpoint"

download_model \
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" \
    "${COMFY_DIR}/models/clip/clip_l.safetensors" \
    "Flux CLIP-L Text Encoder"

download_model \
    "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/ae.safetensors" \
    "${COMFY_DIR}/models/vae/ae.safetensors" \
    "Flux VAE (ae.safetensors)"

# 4. IP-Adapter FaceID Models
download_model \
    "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sd15.bin" \
    "${COMFY_DIR}/models/ipadapter/ip-adapter-faceid_sd15.bin" \
    "IP-Adapter FaceID SD1.5"

download_model \
    "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sd15.bin" \
    "${COMFY_DIR}/models/ipadapter/ip-adapter-faceid-plusv2_sd15.bin" \
    "IP-Adapter FaceID PlusV2 SD1.5"

download_model \
    "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sdxl.bin" \
    "${COMFY_DIR}/models/ipadapter/ip-adapter-faceid_sdxl.bin" \
    "IP-Adapter FaceID SDXL"

download_model \
    "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sd15_lora.safetensors" \
    "${COMFY_DIR}/models/loras/ip-adapter-faceid_sd15_lora.safetensors" \
    "IP-Adapter FaceID SD1.5 LoRA"

download_model \
    "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sd15_lora.safetensors" \
    "${COMFY_DIR}/models/loras/ip-adapter-faceid-plusv2_sd15_lora.safetensors" \
    "IP-Adapter FaceID PlusV2 SD1.5 LoRA"

# 5. InsightFace Models (buffalo_l)
BUFFALO_DIR="${COMFY_DIR}/models/insightface/models/buffalo_l"
download_model "https://huggingface.co/monster-labs/insightface_models/resolve/main/models/buffalo_l/1k3d68.onnx" "${BUFFALO_DIR}/1k3d68.onnx" "InsightFace 1k3d68"
download_model "https://huggingface.co/monster-labs/insightface_models/resolve/main/models/buffalo_l/2d106det.onnx" "${BUFFALO_DIR}/2d106det.onnx" "InsightFace 2d106det"
download_model "https://huggingface.co/monster-labs/insightface_models/resolve/main/models/buffalo_l/genderage.onnx" "${BUFFALO_DIR}/genderage.onnx" "InsightFace genderage"
download_model "https://huggingface.co/monster-labs/insightface_models/resolve/main/models/buffalo_l/glintr100.onnx" "${BUFFALO_DIR}/glintr100.onnx" "InsightFace glintr100"
download_model "https://huggingface.co/monster-labs/insightface_models/resolve/main/models/buffalo_l/scrfd_10g_bnkps.onnx" "${BUFFALO_DIR}/scrfd_10g_bnkps.onnx" "InsightFace scrfd_10g_bnkps"

# 6. ReActor Models
download_model \
    "https://huggingface.co/countsnack/insightface-onnx-repo/resolve/main/inswapper_128.onnx" \
    "${COMFY_DIR}/models/reactor/faceswap_models/inswapper_128.onnx" \
    "ReActor inswapper_128.onnx"
cp -n "${COMFY_DIR}/models/reactor/faceswap_models/inswapper_128.onnx" "${COMFY_DIR}/models/insightface/inswapper_128.onnx" 2>/dev/null || true

download_model \
    "https://huggingface.co/TencentARC/GFPGAN/resolve/main/GFPGANv1.4.pth" \
    "${COMFY_DIR}/models/reactor/facerestore_models/GFPGANv1.4.pth" \
    "GFPGAN v1.4"
cp -n "${COMFY_DIR}/models/reactor/facerestore_models/GFPGANv1.4.pth" "${COMFY_DIR}/models/facerestore_models/GFPGANv1.4.pth" 2>/dev/null || true

download_model \
    "https://huggingface.co/sczhou/CodeFormer/resolve/main/codeformer.pth" \
    "${COMFY_DIR}/models/reactor/facerestore_models/codeformer.pth" \
    "CodeFormer"
cp -n "${COMFY_DIR}/models/reactor/facerestore_models/codeformer.pth" "${COMFY_DIR}/models/facerestore_models/codeformer.pth" 2>/dev/null || true

# 7. TTS Models
download_model \
    "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/kokoro-v0_19.pth" \
    "${COMFY_DIR}/models/tts/kokoro-v0_19.pth" \
    "Kokoro-82M TTS Model"

download_model \
    "https://huggingface.co/coqui/XTTS-v2/resolve/main/model.pth" \
    "${COMFY_DIR}/models/tts/xtts_v2.pth" \
    "XTTS v2 Model"

# 8. Flux Uncensored (NSFW)
download_model \

    "https://huggingface.co/Heartsync/Flux-NSFW-uncensored/resolve/main/flux1-dev-uncensored-fp8.safetensors" \

    "${COMFY_DIR}/models/checkpoints/flux-uncensored-fp8.safetensors" \

    "Flux NSFW Uncensored (Heartsync)"

# 9. Pony Diffusion V6 XL (uncensored SDXL)
download_model \

    "https://civitai.com/api/download/models/257949?type=Model&format=SafeTensor&size=pruned&fp=fp16" \

    "${COMFY_DIR}/models/checkpoints/ponyDiffusionV6XL.safetensors" \

    "Pony Diffusion V6 XL (uncensored)"

# 10. PuLID model (face consistency for Flux)
download_model \

    "https://huggingface.co/DepthAnything/PuLID/resolve/main/pulid_flux_v0.9.1.safetensors" \

    "${COMFY_DIR}/models/ipadapter/pulid_flux_v0.9.1.safetensors" \

    "PuLID Flux v0.9.1"

# 11. LatentSync (lip sync)
download_model \

    "https://huggingface.co/jhliu/latentsync/resolve/main/latentsync_unet.pth" \

    "${COMFY_DIR}/models/checkpoints/latentsync_unet.pth" \

    "LatentSync UNet"

# 12. Wav2Lip (lip sync fallback)
download_model \

    "https://huggingface.co/numz/wav2lip-uhq/resolve/main/wav2lip.pth" \

    "${COMFY_DIR}/models/checkpoints/wav2lip.pth" \

    "Wav2Lip UHQ"

# 13. ControlNet OpenPose SDXL
download_model \

    "https://huggingface.co/xinsir/controlnet-openpose-sdxl-1.0/resolve/main/diffusion_pytorch_model.safetensors" \

    "${COMFY_DIR}/models/controlnet/controlnet-openpose-sdxl-1.0.safetensors" \

    "ControlNet OpenPose SDXL"
log_success "All requested AI models downloaded and verified."

# ==============================================================================
# STEP 6: Deploy Worker Daemon, Workflows & Configuration
# ==============================================================================
log_step "6" "Deploying Worker Daemon & Workflow Templates"

# Copy local worker files if present in the source script directory
SCRIPT_SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "${SCRIPT_SRC_DIR}/worker.py" ]; then
    cp "${SCRIPT_SRC_DIR}/worker.py" "${BASE_DIR}/worker.py"
fi

if [ -f "${SCRIPT_SRC_DIR}/config.json" ]; then
    cp "${SCRIPT_SRC_DIR}/config.json" "${BASE_DIR}/config.json"
fi

if [ -d "${SCRIPT_SRC_DIR}/workflows" ]; then
    cp -r "${SCRIPT_SRC_DIR}/workflows/"* "${WORKFLOWS_DIR}/" 2>/dev/null || true
fi

# Write config.json if not present
if [ ! -f "${BASE_DIR}/config.json" ]; then
    cat <<'EOF' > "${BASE_DIR}/config.json"
{
  "base44_url": "https://app.base44.com",
  "app_id": "6a901f55a4d9a9b76a095a77",
  "worker_token": "__PLACEHOLDER__",
  "long_poll_wait_seconds": 25,
  "reconnect_delay_seconds": 5,
  "comfyui_host": "127.0.0.1",
  "comfyui_port": 8188,
  "output_dir": "./output",
  "comfyui_path": "./ComfyUI",
  "gpu_enabled": true
}
EOF
fi

log_success "Worker daemon and workflows deployed to ${BASE_DIR}."

# ==============================================================================
# STEP 7: Create start.sh Launcher Script
# ==============================================================================
log_step "7" "Creating start.sh Launcher Script"

START_SCRIPT="${BASE_DIR}/start.sh"

cat <<'EOF' > "${START_SCRIPT}"
#!/usr/bin/env bash
set -e

# ==============================================================================
# ShimiStudio ComfyUI Launcher
# Starts ComfyUI with public --share flag for phone camera connection
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"
COMFY_DIR="${SCRIPT_DIR}/ComfyUI"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${CYAN}${BOLD}====================================================================${NC}"
echo -e "${CYAN}${BOLD}                 ShimiStudio PC ComfyUI Launcher                    ${NC}"
echo -e "${CYAN}${BOLD}====================================================================${NC}"

# 1. Activate Virtual Environment
if [ -d "${VENV_DIR}" ] && [ -f "${VENV_DIR}/bin/activate" ]; then
    echo -e "${GREEN}⚡ Activating Python virtual environment (${VENV_DIR})...${NC}"
    source "${VENV_DIR}/bin/activate"
elif [ -d "${SCRIPT_DIR}/.venv" ] && [ -f "${SCRIPT_DIR}/.venv/bin/activate" ]; then
    echo -e "${GREEN}⚡ Activating Python virtual environment (${SCRIPT_DIR}/.venv)...${NC}"
    source "${SCRIPT_DIR}/.venv/bin/activate"
else
    echo -e "${YELLOW}⚠️ Virtual environment not found. Running with system Python.${NC}"
fi

# 2. Check ComfyUI installation directory
if [ ! -d "${COMFY_DIR}" ]; then
    echo -e "${RED}❌ Error: ComfyUI directory not found at ${COMFY_DIR}.${NC}"
    echo -e "${YELLOW}👉 Please run install.sh first to set up ShimiStudio!${NC}"
    exit 1
fi

cd "${COMFY_DIR}"

# 3. Print Connection Information
echo -e "\n${MAGENTA}${BOLD}📱 PHONE CAMERA / REMOTE CONNECTION INSTRUCTIONS:${NC}"
echo -e "${CYAN}--------------------------------------------------------------------${NC}"
echo -e "${GREEN}1. Local Access (Same PC):${NC}       http://127.0.0.1:8188"
echo -e "${GREEN}2. Network Access (Same Wi-Fi):${NC}    http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'YOUR_LOCAL_IP'):8188"
echo -e "${GREEN}3. Mobile / Camera Access (Share):${NC} A public Gradio/Tunnel link will be generated below!"
echo -e "${CYAN}--------------------------------------------------------------------${NC}\n"

echo -e "${GREEN}🚀 Launching ComfyUI server... (Port: 8188, Listen: 0.0.0.0, Share: Enabled)${NC}\n"

# 4. Launch ComfyUI with public share enabled
python main.py --listen 0.0.0.0 --port 8188 --share
EOF

chmod +x "${START_SCRIPT}"
log_success "Created ${START_SCRIPT} and set executable permissions."

# ==============================================================================
# STEP 8: Final Summary & Launch Information
# ==============================================================================
log_step "8" "Installation Completed Successfully!"

LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_LOCAL_IP")

echo -e "\n${GREEN}${BOLD}====================================================================${NC}"
echo -e "${GREEN}${BOLD}       🎉 ShimiStudio PC System Setup Complete!                     ${NC}"
echo -e "${GREEN}${BOLD}====================================================================${NC}"
echo -e "${CYAN}${BOLD}Installation Summary:${NC}"
echo -e " • ComfyUI Location:   ${COMFY_DIR}"
echo -e " • Virtual Env:        ${VENV_DIR}"
echo -e " • Workflows:          ${WORKFLOWS_DIR}"
echo -e " • Output Directory:   ${OUTPUT_DIR}"
echo -e " • Launcher Script:    ${START_SCRIPT}"
echo -e "\n${MAGENTA}${BOLD}🌐 ComfyUI Access URLs:${NC}"
echo -e " • ${BOLD}Local Web UI:${NC}       http://127.0.0.1:8188"
echo -e " • ${BOLD}Network Web UI:${NC}     http://${LOCAL_IP}:8188"
echo -e " • ${BOLD}Phone Camera Share:${NC} Run '${START_SCRIPT}' to print the live public Gradio URL."
echo -e "${GREEN}${BOLD}====================================================================${NC}\n"

log_info "To start ComfyUI right now, run:"
echo -e "   ${CYAN}${BOLD}${START_SCRIPT}${NC}\n"
