#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# ShimiStudio — התקנה אוטומטית (Mac / Linux)
# הורד, הפעל, והמחשב שלך הופך לתחנת כח ✅
# ═══════════════════════════════════════════════════════════════
set -e

# Hebrew messages (fallback to English if terminal doesn't support)
RED='\033[0;32m'
NC='\033[0m'

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     ShimiStudio — התקנה אוטומטית        ║"
echo "║     נא לא לסגור את החלון הזה!           ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ═══ הגדרות שרת ═══
SERVER_URL="https://solas-6a095a77.base44.app/functions/shimiStudioAPI"
APP_ID="6a901f55a4d9a9b76a095a77"
WORKER_TOKEN="shimi_worker_auto"
INSTALL_DIR="$HOME/ShimiStudio"

# ═══ 1. תיקיית התקנה ═══
echo "[1/10] יוצר תיקיית התקנה: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
echo "✓ הושלם"
echo ""

# ═══ 2. בדיקת Python ═══
echo "[2/10] בודק Python..."
if ! command -v python3 &> /dev/null; then
    echo "⚠️ Python לא מותקן. מתקין..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac — Homebrew
        if ! command -v brew &> /dev/null; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        brew install python@3.11
    else
        # Linux
        sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv python3-pip
    fi
fi
PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python $PYVER מותקן"
echo ""

# ═══ 3. סביבה וירטואלית ═══
echo "[3/10] יוצר סביבה וירטואלית..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
echo "✓ הושלם"
echo ""

# ═══ 4. PyTorch ═══
echo "[4/10] מתקין PyTorch עם CUDA... (יכול לקחת דקות)"
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 -q 2>/dev/null || \
pip install torch torchvision torchaudio -q
echo "✓ הושלם"
echo ""

# ═══ 5. ComfyUI ═══
echo "[5/10] מוריד ComfyUI..."
if [ ! -d "ComfyUI" ]; then
    git clone https://github.com/comfyanonymous/ComfyUI.git
else
    echo "✓ ComfyUI כבר קיים"
fi
cd ComfyUI
pip install -r requirements.txt -q
cd ..
echo "✓ הושלם"
echo ""

# ═══ 6. מודלים ═══
echo "[6/10] מוריד מודלים... (יכול לקחת 15-30 דקות)"
mkdir -p ComfyUI/models/checkpoints
mkdir -p ComfyUI/models/diffusion_models

# Flux.1
if [ ! -f "ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors" ]; then
    echo "  מוריד Flux.1..."
    curl -L -o "ComfyUI/models/checkpoints/flux1-dev-fp8.safetensors" \
        "https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors" 2>/dev/null
fi

# Wan 2.1
if [ ! -f "ComfyUI/models/diffusion_models/wan2.1-t2v-1.3B.safetensors" ]; then
    echo "  מוריד Wan 2.1..."
    curl -L -o "ComfyUI/models/diffusion_models/wan2.1-t2v-1.3B.safetensors" \
        "https://huggingface.co/Comfy-Org/Wan_2.1/resolve/main/wan2.1-t2v-1.3B.safetensors" 2>/dev/null
fi

# LTX-Video
if [ ! -f "ComfyUI/models/checkpoints/ltx-video-2b.safetensors" ]; then
    echo "  מוריד LTX-Video..."
    curl -L -o "ComfyUI/models/checkpoints/ltx-video-2b.safetensors" \
        "https://huggingface.co/Lightricks/LTX-Video/resolve/main/ltx-video-2b.safetensors" 2>/dev/null
fi
echo "✓ הושלם"
echo ""

# ═══ 7. Custom Nodes ═══
echo "[7/10] מתקין Custom Nodes..."
cd ComfyUI/custom_nodes
[ ! -d "ComfyUI_IPAdapter_plus" ] && git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git 2>/dev/null
[ ! -d "ComfyUI_ReActor" ] && git clone https://github.com/Gourieff/ComfyUI_ReActor.git 2>/dev/null
[ ! -d "ComfyUI-AnimateDiff-Evolved" ] && git clone https://github.com/kijai/ComfyUI-AnimateDiff-Evolved.git 2>/dev/null
[ ! -d "comfyui_wan" ] && git clone https://github.com/kijai/ComfyUI-Wan.git 2>/dev/null
cd ../..
echo "✓ הושלם"
echo ""

# ═══ 8. Worker ═══
echo "[8/10] מוריד Worker..."
curl -s -L -o "worker.py" "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/worker.py" 2>/dev/null
curl -s -L -o "config.json" "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/config.json" 2>/dev/null
curl -s -L -o "base44_client.py" "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/base44_client.py" 2>/dev/null
curl -s -L -o "comfyui_client.py" "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/comfyui_client.py" 2>/dev/null
curl -s -L -o "workflows.py" "https://raw.githubusercontent.com/sunraz/ShimiStudio/main/workflows.py" 2>/dev/null

# עדכן config עם כתובת השרת
python3 -c "
import json
c = json.load(open('config.json'))
c['base44_url'] = '$SERVER_URL'
c['app_id'] = '$APP_ID'
c['worker_token'] = '$WORKER_TOKEN'
json.dump(c, open('config.json', 'w'), indent=2, ensure_ascii=False)
"
echo "✓ הושלם"
echo ""

# ═══ 9. דרישות ═══
echo "[9/10] מתקין דרישות נוספות..."
pip install requests pillow tqdm watchdog -q
echo "✓ הושלם"
echo ""

# ═══ 10. סקריפט הפעלה ═══
echo "[10/10] יוצר סקריפט הפעלה..."
cat > "$INSTALL_DIR/start_worker.sh" << 'STARTEOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
echo "מפעיל ShimiStudio Worker..."
python worker.py --server=https://solas-6a095a77.base44.app/functions/shimiStudioAPI --token=shimi_worker_auto
STARTEOF
chmod +x "$INSTALL_DIR/start_worker.sh"
echo "✓ הושלם"
echo ""

# ═══ סיום ═══
echo "╔══════════════════════════════════════════╗"
echo "║     התקנה הושלמה! 🎉                    ║"
echo "║                                          ║"
echo "║  המחשב מחובר כתחנת כח ✅                 ║"
echo "║                                          ║"
echo "║  להפעלה: ~/ShimiStudio/start_worker.sh   ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "מפעיל Worker עכשיו..."
sleep 3
exec "$INSTALL_DIR/start_worker.sh"
