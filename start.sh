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
echo -e "${GREEN}2. Network Access (Same Wi-Fi):${NC}    http://$(hostname -I | awk '{print $1}'):8188"
echo -e "${GREEN}3. Mobile / Camera Access (Share):${NC} A public Gradio/Tunnel link will be generated below!"
echo -e "${CYAN}--------------------------------------------------------------------${NC}\n"

echo -e "${GREEN}🚀 Launching ComfyUI server... (Port: 8188, Listen: 0.0.0.0, Share: Enabled)${NC}\n"

# 4. Launch ComfyUI with public share enabled
python main.py --listen 0.0.0.0 --port 8188 --share
