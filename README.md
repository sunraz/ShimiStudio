# 🎬 ShimiStudio — AI Video & Image Production System

Open-source, local-first AI studio for generating photorealistic images, videos, face swaps, voice cloning, and lip sync.
Built to match xmode.ai quality using **100% open-source models** — zero recurring API costs.

## Architecture

```
Mac (Control Panel)  →  Base44 (Orchestrator)  →  PC (GPU Worker)  ←  Phone (Camera)
     browser              shimiStudioAPI            ComfyUI             browser
                          long-poll + push          worker.py           phone_camera.py
```

- **Mac**: Sends jobs via web interface → Base44 backend function
- **Base44**: `shimiStudioAPI` backend function + `RenderJob` entity (job queue)
- **PC**: Worker daemon claims jobs, runs ComfyUI, uploads results
- **Phone**: Camera frames stream to PC via browser (no app needed)

## Quick Start

### 1. PC Installation (One Click)
```bash
bash install.sh
```
This installs:
- Python 3.11+ + PyTorch CUDA
- ComfyUI + 8 custom nodes
- 25+ AI models (~30GB from HuggingFace, all public, no token needed)

### 2. Pro Pipeline (Optional)
```bash
python upgrade_pipeline.py    # PuLID + ReActor + XTTS + LatentSync + Wav2Lip + DWPose
python civitai_models.py --token YOUR_TOKEN    # Your 9-model CivitAI collection
python studio_pro.py --install-controlnet    # Camera → DWPose → ControlNet
python studio_pro.py --install-kohya    # LoRA trainer (10-30 images)
python studio_pro.py --install-tagger    # NSFW auto-tagger (93%)
```

### 3. Start
```bash
bash start.sh    # ComfyUI on port 8188 + worker daemon
```

### 4. Phone Camera (Optional)
```bash
python phone_camera.py    # Web server on port 7860
# Open http://YOUR_PC_IP:7860 on phone (same WiFi)
```

## Full Pipeline (6 Stages)

| Stage | Model | What it does | VRAM |
|-------|-------|-------------|------|
| 1. Image | Pony Diffusion V6 XL | Generate base image (uncensored SDXL) | 6GB |
| 2. Video | Wan 2.2 I2V 14B | Animate static image | 12GB |
| 3. Face ID | PuLID + IPAdapter | Consistent face from 1-3 photos | 4GB |
| 4. Face Swap | ReActor (inswapper_128) | Swap face in video | 2GB |
| 5. Voice | XTTS v2 | Clone voice from 6s sample (17 languages) | 2GB |
| 6. Lip Sync | LatentSync / Wav2Lip | Sync mouth to audio | 4GB |
| + Upscale | LTX-2.3 Upscaler x2 | Double resolution | 4GB |

## Video Engines (5 options by VRAM)

| Engine | Model | VRAM | Best for |
|--------|-------|------|----------|
| Fast | Wan 2.2 T2V 1.3B GGUF | 4-6GB | Quick previews |
| High | Wan 2.2 T2V 14B FP8 | 16GB | Production quality |
| I2V | Wan 2.2 TI2V 5B FP8 | 12GB | Image to video |
| LTX | LTX-2.3 22B Dev FP8 | 16GB | Cinematic |
| Long | FramePack I2V 14B FP8 | 6GB | Long videos (60s+) |

## Models (25+, all from HuggingFace — no token needed)

### Image
- Pony Diffusion V6 XL (uncensored SDXL)
- Flux.1 dev FP8

### Video
- Wan 2.2 T2V 1.3B / 14B
- Wan 2.2 TI2V 5B I2V
- LTX-Video 2B
- FramePack I2V 14B

### Text + VAE
- T5-XXL FP8 / UMT5-XXL
- Wan 2.1 VAE

### Face
- IP-Adapter FaceID (SD1.5, SDXL, PlusV2)
- PuLID Flux v0.9.1
- ReActor inswapper_128
- InsightFace buffalo_l (5 models)
- GFPGAN v1.4 + CodeFormer

### Voice + Lip Sync
- XTTS v2 (6s sample, 17 languages)
- Kokoro-82M
- LatentSync (ByteDance)
- Wav2Lip UHQ

### AnimateDiff
- SD 1.5 v2 motion
- SDXL v10 beta motion
- TemporalDiff v1

### LoRAs
- LCM LoRA SD 1.5 (4-step fast)
- LTX-2.3 Distilled LoRA
- LTX-2.3 Upscaler x2

### Pose
- DWPose (yolox_l, dw-ll_ucoco_384)
- ControlNet OpenPose SDXL

### CLIP
- CLIP ViT-H-14
- CLIP-L (Flux)

## Custom Nodes (8)

1. ComfyUI-Manager
2. ComfyUI_IPAdapter_plus
3. ComfyUI-ReActor
4. ComfyUI-AnimateDiff-Evolved
5. ComfyUI-WanVideoWrapper
6. ComfyUI-LTXVideo
7. ComfyUI-Workflow-Component
8. ComfyUI-VideoHelperSuite (via Manager)

## Worker Architecture

**No 10-second polling!** The worker uses:
1. **Long-poll**: Worker opens a connection to Base44 that stays open up to 25 seconds. When a job appears, it returns instantly.
2. **Webhook push**: Worker runs a tiny HTTP server on port 5555. When Base44 creates a job, it POSTs to the worker → instant wake-up.

```
Worker calls claim(wait_seconds=25)
    → Base44 holds connection open
    → New job created → returns instantly
    → Worker processes job
    → Worker calls claim again (no sleep!)

OR: Base44 creates job → POST to worker:5555 → worker wakes up
```

## Base44 API (shimiStudioAPI)

| Action | Description |
|--------|-------------|
| `create` | Create a new render job + push notification |
| `claim` | Long-poll for next pending job (up to 25s) |
| `update` | Update job status/progress/output |
| `status` | Get job status |
| `list` | List jobs (with optional filter) |
| `cancel` | Cancel a job |
| `stats` | Queue statistics |
| `register_worker` | Register webhook URL for push |
| `notify` | Manual push notification |

## Files

```
ShimiStudio/
├── install.sh           # One-click installer (Python + ComfyUI + 25+ models)
├── start.sh             # Launcher (ComfyUI + worker)
├── upgrade_pipeline.py  # Pro pipeline (PuLID + ReActor + XTTS + LatentSync + Wav2Lip)
├── civitai_models.py    # CivitAI model downloader (9 models)
├── studio_pro.py        # Advanced tools (LoRA + Camera + Pose + Tagger)
├── worker.py            # Worker daemon (long-poll + webhook push)
├── phone_camera.py      # Phone camera bridge (browser → ComfyUI)
├── config.json          # Configuration
└── workflows/           # 11 ComfyUI workflow templates
    ├── text_to_image.json
    ├── image_to_video.json
    ├── text_to_video.json
    ├── ltx_t2v.json
    ├── wan22_i2v.json       (sub-agent)
    ├── face_id.json
    ├── face_swap.json
    ├── tts_lipsync.json
    ├── camera_capture.json
    ├── full_pipeline.json
    └── full_pipeline_6stage.json  (sub-agent)
```

## VRAM Requirements

| Setup | VRAM | What works |
|-------|------|-----------|
| Minimum | 4-6GB | Wan 2.2 1.3B, Pony SDXL, ReActor |
| Recommended | 8-12GB | + Wan 2.2 I2V 5B, FramePack, XTTS |
| Optimal | 16GB+ | All engines including 14B + LTX-2.3 22B |
