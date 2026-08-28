#!/usr/bin/env python3
"""
ShimiStudio Phone Camera Bridge
================================
Turns a phone's camera into a live input for ComfyUI and Base44 Render Jobs.
No native mobile app required — opens a web browser on any iOS/Android device.

Features:
- Flask web server running on PC (port 5000)
- Mobile-optimized dark theme web page with Hebrew RTL layout
- WebRTC getUserMedia live camera preview with front/back camera toggle
- Instant image capture (POST /capture)
- Continuous frame streaming mode (2-second interval)
- Interactive 3-photo Face ID submission (POST /submit-face-id -> Base44 API)
- Quick text-to-image generate with camera frame reference (POST /submit-generate -> Base44 API)
- Real-time job status polling from render queue (GET /job-status/<job_id>)
- Most recent generated result preview (GET /latest-result)
- Auto-detects PC local IP and displays mobile link
"""

import os
import sys
import time
import json
import base64
import socket
import logging
import argparse
import datetime
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PhoneCameraBridge")

# Configuration & Constants
BASE44_API_URL = os.environ.get(
    'BASE44_API_URL',
    'https://solas-6a095a77.base44.app/functions/shimiStudioAPI'
)
BASE44_API_KEY = os.environ.get('BASE44_API_KEY', os.environ.get('BASE44_TOKEN', ''))

app = Flask(__name__)
CAPTURES_DIR = Path(__file__).resolve().parent / "captures"


def get_local_ip() -> str:
    """Detect local IP address of the PC on the network."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        try:
            ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def call_base44_api(action: str, params: dict = None) -> dict:
    """Helper to execute requests against Base44 shimiStudioAPI backend function."""
    payload = {"action": action}
    if params:
        payload.update(params)

    headers = {"Content-Type": "application/json"}
    if BASE44_API_KEY:
        headers["Authorization"] = f"Bearer {BASE44_API_KEY}"

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE44_API_URL,
        data=data_bytes,
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8") if e.fp else str(e)
        logger.error(f"Base44 API HTTP {e.code}: {err_body}")
        try:
            return json.loads(err_body)
        except Exception:
            return {"error": f"HTTP {e.code}: {e.reason}", "details": err_body}
    except Exception as e:
        logger.error(f"Base44 API Exception: {e}")
        return {"error": str(e)}


def save_base64_image(base64_str: str, prefix: str = "frame") -> tuple[Path, str]:
    """Decode and save a base64 JPEG image string to local captures directory."""
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

    if "," in base64_str:
        header, base64_data = base64_str.split(",", 1)
    else:
        base64_data = base64_str

    img_bytes = base64.b64decode(base64_data)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.jpg"
    file_path = CAPTURES_DIR / filename

    with open(file_path, "wb") as f:
        f.write(img_bytes)

    logger.info(f"💾 Saved capture: {filename} ({len(img_bytes) / 1024:.1f} KB)")
    return file_path, filename


# ============================================================================
# FLASK ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Redirect or serve camera page."""
    return render_camera_page()


@app.route('/camera', methods=['GET'])
def render_camera_page():
    """GET /camera — serves the mobile camera page."""
    pc_ip = get_local_ip()
    port = request.host.split(':')[-1] if ':' in request.host else '5000'
    return render_template_string(MOBILE_HTML_TEMPLATE, pc_ip=pc_ip, port=port)


@app.route('/capture', methods=['POST'])
def handle_capture():
    """POST /capture — receives a base64 JPEG frame, saves locally."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        image_data = data.get('image')

        if not image_data:
            return jsonify({"status": "error", "error": "No image data provided"}), 400

        file_path, filename = save_base64_image(image_data, prefix="capture")
        timestamp_str = datetime.datetime.now().isoformat()

        return jsonify({
            "status": "success",
            "message": "Frame captured successfully",
            "filename": filename,
            "filepath": str(file_path),
            "timestamp": timestamp_str
        })
    except Exception as e:
        logger.error(f"Capture error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/submit-face-id', methods=['POST'])
def handle_submit_face_id():
    """POST /submit-face-id — receives 3 face photos, creates a RenderJob via Base44 API."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        images = data.get('images', [])

        if not isinstance(images, list) or len(images) == 0:
            return jsonify({"status": "error", "error": "At least 3 face photos required"}), 400

        # Save local copies
        saved_files = []
        for idx, img_str in enumerate(images, 1):
            file_path, filename = save_base64_image(img_str, prefix=f"face_id_{idx}")
            saved_files.append(filename)

        logger.info(f"👤 Submitting Face ID job with {len(images)} face photos...")

        # Create job via Base44 shimiStudioAPI
        api_res = call_base44_api("create", {
            "job_type": "face_id",
            "face_images": images,
            "created_by_name": "PhoneCameraBridge"
        })

        if "error" in api_res and not api_res.get("job_id"):
            return jsonify({
                "status": "error",
                "error": api_res.get("error"),
                "details": api_res
            }), 500

        return jsonify({
            "status": "created",
            "job_id": api_res.get("job_id"),
            "message": api_res.get("message", "Face ID job added to render queue"),
            "saved_local_files": saved_files
        })
    except Exception as e:
        logger.error(f"Submit Face ID error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/submit-generate', methods=['POST'])
def handle_submit_generate():
    """POST /submit-generate — receives prompt + optional camera frame, creates a job."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        prompt = data.get('prompt', '').strip()
        camera_frame = data.get('image', '').strip()

        if not prompt:
            return jsonify({"status": "error", "error": "Prompt is required"}), 400

        # Save local copy of frame if provided
        if camera_frame:
            save_base64_image(camera_frame, prefix="prompt_ref")

        job_type = "camera_capture" if camera_frame else "text_to_image"

        logger.info(f"✨ Submitting Quick Generate job ({job_type}): '{prompt[:50]}...'")

        api_res = call_base44_api("create", {
            "job_type": job_type,
            "prompt": prompt,
            "reference_image": camera_frame,
            "camera_frames": camera_frame,
            "created_by_name": "PhoneCameraBridge"
        })

        if "error" in api_res and not api_res.get("job_id"):
            return jsonify({
                "status": "error",
                "error": api_res.get("error"),
                "details": api_res
            }), 500

        return jsonify({
            "status": "created",
            "job_id": api_res.get("job_id"),
            "message": api_res.get("message", "Generate job added to render queue")
        })
    except Exception as e:
        logger.error(f"Submit Generate error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/job-status/<job_id>', methods=['GET'])
def handle_job_status(job_id):
    """GET /job-status/<job_id> — returns job status from Base44."""
    try:
        api_res = call_base44_api("status", {"job_id": job_id})
        return jsonify(api_res)
    except Exception as e:
        logger.error(f"Job status error for {job_id}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/latest-result', methods=['GET'])
def handle_latest_result():
    """GET /latest-result — returns the most recent completed job output URL."""
    try:
        api_res = call_base44_api("list", {"status_filter": "completed", "limit": 10})

        if isinstance(api_res, dict) and "jobs" in api_res:
            jobs = api_res.get("jobs", [])
            for job in jobs:
                output_url = job.get("output_url")
                if output_url:
                    return jsonify({
                        "status": "success",
                        "job_id": job.get("id"),
                        "job_type": job.get("job_type"),
                        "output_url": output_url,
                        "completed_at": job.get("completed_at") or job.get("created_date")
                    })

        return jsonify({
            "status": "no_completed_jobs",
            "message": "טרם הושלמו עבודות יצירה בתור",
            "output_url": None
        })
    except Exception as e:
        logger.error(f"Latest result error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


# ============================================================================
# MOBILE HTML TEMPLATE (DARK THEME, RTL HEBREW, RESPONSIVE UI)
# ============================================================================

MOBILE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>ShimiStudio Phone Camera</title>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700;900&family=Heebo:wght@400;500;700&display=swap" rel="stylesheet">

    <style>
        :root {
            --bg-dark: #0b0f19;
            --bg-card: rgba(22, 30, 49, 0.85);
            --bg-card-border: rgba(255, 255, 255, 0.08);
            --accent-purple: #8b5cf6;
            --accent-indigo: #6366f1;
            --accent-blue: #3b82f6;
            --accent-pink: #ec4899;
            --accent-emerald: #10b981;
            --accent-amber: #f59e0b;
            --accent-red: #ef4444;
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --radius-lg: 20px;
            --radius-md: 12px;
            --shadow-glow: 0 0 25px rgba(139, 92, 246, 0.25);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Rubik', 'Heebo', system-ui, -apple-system, sans-serif;
            background-color: var(--bg-dark);
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(236, 72, 153, 0.12) 0%, transparent 40%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 12px;
            padding-bottom: 40px;
            direction: rtl;
        }

        .header {
            text-align: center;
            padding: 12px 8px 16px 8px;
        }

        .header-title {
            font-size: 1.4rem;
            font-weight: 900;
            background: linear-gradient(135deg, #a7f3d0, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .header-subtitle {
            font-size: 0.85rem;
            color: var(--text-sub);
            margin-top: 4px;
        }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--bg-card-border);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: var(--radius-lg);
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        }

        /* Camera Feed Styling */
        .camera-container {
            position: relative;
            width: 100%;
            border-radius: var(--radius-md);
            overflow: hidden;
            background: #000;
            border: 2px solid rgba(139, 92, 246, 0.3);
            box-shadow: var(--shadow-glow);
            aspect-ratio: 4 / 3;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        video {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .camera-overlay {
            position: absolute;
            top: 10px;
            right: 10px;
            left: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            pointer-events: none;
            z-index: 10;
        }

        .live-badge {
            background: rgba(0, 0, 0, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.15);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            color: #fff;
            display: flex;
            align-items: center;
            gap: 6px;
            backdrop-filter: blur(6px);
        }

        .dot-live {
            width: 8px;
            height: 8px;
            background-color: var(--accent-emerald);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-emerald);
            animation: pulse 1.5s infinite;
        }

        .dot-live.continuous {
            background-color: var(--accent-pink);
            box-shadow: 0 0 10px var(--accent-pink);
        }

        @keyframes pulse {
            0% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(0.8); }
            100% { opacity: 1; transform: scale(1); }
        }

        .cam-btn {
            pointer-events: auto;
            background: rgba(0, 0, 0, 0.65);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            backdrop-filter: blur(6px);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .flash-overlay {
            position: absolute;
            inset: 0;
            background: white;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.15s ease-out;
            z-index: 20;
        }

        .flash-overlay.active {
            opacity: 0.85;
        }

        /* Buttons Grid */
        .controls-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 14px;
        }

        .btn {
            font-family: inherit;
            font-size: 0.95rem;
            font-weight: 700;
            padding: 14px 12px;
            border-radius: var(--radius-md);
            border: none;
            color: #ffffff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            min-height: 50px;
            touch-action: manipulation;
        }

        .btn:active {
            transform: scale(0.97);
        }

        .btn-capture {
            background: linear-gradient(135deg, var(--accent-indigo), var(--accent-purple));
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            grid-column: span 1;
        }

        .btn-continuous {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-main);
            grid-column: span 1;
        }

        .btn-continuous.active {
            background: linear-gradient(135deg, var(--accent-pink), #f43f5e);
            border-color: transparent;
            box-shadow: 0 4px 15px rgba(244, 63, 94, 0.4);
            animation: pulse-border 2s infinite;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue));
            width: 100%;
            margin-top: 10px;
            box-shadow: 0 4px 15px rgba(139, 92, 246, 0.35);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-main);
            font-size: 0.85rem;
            padding: 8px 14px;
            min-height: 38px;
        }

        /* Section Headings */
        .section-title {
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
            color: #f1f5f9;
        }

        .section-desc {
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-bottom: 12px;
        }

        /* Face ID Slots */
        .face-slots {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 12px;
        }

        .face-slot {
            aspect-ratio: 1;
            background: rgba(0, 0, 0, 0.4);
            border: 2px dashed rgba(255, 255, 255, 0.2);
            border-radius: var(--radius-md);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            position: relative;
            transition: all 0.2s ease;
        }

        .face-slot.filled {
            border: 2px solid var(--accent-emerald);
        }

        .face-slot img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }

        .face-slot-label {
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-sub);
        }

        /* Quick Generate Form */
        textarea.prompt-input {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: var(--radius-md);
            color: #fff;
            padding: 12px;
            font-family: inherit;
            font-size: 0.9rem;
            resize: none;
            min-height: 70px;
            outline: none;
            direction: rtl;
        }

        textarea.prompt-input:focus {
            border-color: var(--accent-purple);
            box-shadow: 0 0 10px rgba(139, 92, 246, 0.3);
        }

        .checkbox-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
            font-size: 0.85rem;
            color: var(--text-sub);
            cursor: pointer;
        }

        .checkbox-row input {
            width: 18px;
            height: 18px;
            accent-color: var(--accent-purple);
        }

        /* Presets */
        .preset-chips {
            display: flex;
            gap: 6px;
            overflow-x: auto;
            padding: 6px 0;
            margin-top: 6px;
            scrollbar-width: none;
        }

        .preset-chips::-webkit-scrollbar {
            display: none;
        }

        .chip {
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.75rem;
            white-space: nowrap;
            color: #cbd5e1;
            cursor: pointer;
        }

        .chip:active {
            background: var(--accent-purple);
            color: #fff;
        }

        /* Job Status Card */
        .status-box {
            background: rgba(15, 23, 42, 0.6);
            border-radius: var(--radius-md);
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            margin-top: 8px;
        }

        .status-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 700;
        }

        .progress-bar-bg {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }

        .progress-bar-fill {
            height: 100%;
            width: 0%;
            background: linear-gradient(90deg, var(--accent-indigo), var(--accent-purple), var(--accent-pink));
            transition: width 0.3s ease;
        }

        /* Result Display */
        .result-container {
            width: 100%;
            border-radius: var(--radius-md);
            overflow: hidden;
            background: #000;
            margin-top: 8px;
            display: none;
        }

        .result-container img, .result-container video {
            width: 100%;
            max-height: 320px;
            object-fit: contain;
            display: block;
        }

        /* Toast Popup */
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: rgba(30, 41, 59, 0.95);
            border: 1px solid var(--accent-purple);
            color: #fff;
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 0.85rem;
            font-weight: 700;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            z-index: 100;
            white-space: nowrap;
            pointer-events: none;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }
    </style>
</head>
<body>

    <!-- Header -->
    <div class="header">
        <div class="header-title">
            <span>📷 ShimiStudio Camera</span>
        </div>
        <div class="header-subtitle">חיבור מצלמה למערכת ComfyUI & Base44 ({{ pc_ip }})</div>
    </div>

    <!-- Live Camera Card -->
    <div class="card">
        <div class="camera-container">
            <video id="videoPreview" autoplay playsinline muted></video>
            <div class="flash-overlay" id="flashOverlay"></div>
            
            <div class="camera-overlay">
                <div class="live-badge">
                    <div class="dot-live" id="liveDot"></div>
                    <span id="liveStatusText">שידור חי</span>
                </div>
                <button class="cam-btn" onclick="toggleCamera()">
                    🔄 החלף מצלמה
                </button>
            </div>
        </div>

        <canvas id="captureCanvas" style="display:none;"></canvas>

        <!-- Capture Controls -->
        <div class="controls-grid">
            <button class="btn btn-capture" onclick="takeSingleCapture()">
                📸 לכידת תמונה
            </button>
            <button class="btn btn-continuous" id="continuousBtn" onclick="toggleContinuousMode()">
                🔄 מצב רציף (2 ש')
            </button>
        </div>
    </div>

    <!-- Create Face ID Card -->
    <div class="card">
        <div class="section-title">
            <span>👤 יצירת FACE ID אישי</span>
        </div>
        <div class="section-desc">צלם 3 תמונות פנים מזוויות שונות ליצירת פרופיל Face ID</div>

        <div class="face-slots">
            <div class="face-slot" id="faceSlot1">
                <span class="face-slot-label">תמונה 1</span>
            </div>
            <div class="face-slot" id="faceSlot2">
                <span class="face-slot-label">תמונה 2</span>
            </div>
            <div class="face-slot" id="faceSlot3">
                <span class="face-slot-label">תמונה 3</span>
            </div>
        </div>

        <div style="display: flex; gap: 8px;">
            <button class="btn btn-primary" id="btnCaptureFace" onclick="captureFacePhoto()" style="flex: 2; margin-top:0;">
                📸 צלם תמונת פנים (1/3)
            </button>
            <button class="btn btn-secondary" onclick="resetFacePhotos()" style="flex: 1; align-self: center;">
                איפוס
            </button>
        </div>

        <button class="btn btn-primary" id="btnSubmitFaceId" onclick="submitFaceIdJob()" style="display:none; background: linear-gradient(135deg, var(--accent-emerald), #059669);">
            🚀 שלח 3 תמונות ל-Face ID
        </button>
    </div>

    <!-- Quick Generate Card -->
    <div class="card">
        <div class="section-title">
            <span>✨ יצירה מהירה ב-ComfyUI</span>
        </div>

        <textarea id="promptInput" class="prompt-input" placeholder="תיאור לתמונה ב-ComfyUI (למשל: דיוקן סייברפאנק דרמטי בלילה)..."></textarea>

        <div class="preset-chips">
            <div class="chip" onclick="applyPreset('ציור שמן קלאסי של דמות דרמטית, תאורה חמה, 8k')">🎨 ציור שמן</div>
            <div class="chip" onclick="applyPreset('סייברפאנק עתידני עם אורות ניאון בתל אביב, 8k')">🏙️ סייברפאנק</div>
            <div class="chip" onclick="applyPreset('פורטרט צילום ריאליסטי, עדשת 85mm, עומק שדה רדוד')">📸 פורטרט</div>
            <div class="chip" onclick="applyPreset('דמות אנימה יפנית צבעונית בסגנון סטודיו ג'יבלי')">🎌 אנימה</div>
        </div>

        <label class="checkbox-row">
            <input type="checkbox" id="includeCameraFrame" checked>
            <span>הכלל תמונה נוכחית מהמצלמה כתמונת רפרנס</span>
        </label>

        <button class="btn btn-primary" onclick="submitQuickGenerate()">
            🎨 צור תמונה עכשיו
        </button>
    </div>

    <!-- Queue Status Card -->
    <div class="card" id="statusCard" style="display:none;">
        <div class="section-title">
            <span>⚙️ סטטוס עבודה בתור</span>
        </div>

        <div class="status-box">
            <div class="status-header">
                <span id="jobTypeLabel">עבודה במערכת...</span>
                <span id="jobStatusBadge" style="color: var(--accent-amber);">ממתין ⏳</span>
            </div>
            <div style="font-size: 0.75rem; color: var(--text-sub); margin-top: 4px;" id="jobIdLabel">ID: -</div>
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
        </div>
    </div>

    <!-- Latest Result Card -->
    <div class="card">
        <div class="section-title" style="justify-content: space-between;">
            <span>🖼️ תוצאה אחרונה שיוצרה</span>
            <button class="btn btn-secondary" onclick="checkLatestResult()" style="padding: 4px 10px; min-height: 28px; font-size:0.75rem;">
                🔄 רענן
            </button>
        </div>

        <div id="noResultText" style="font-size: 0.85rem; color: var(--text-sub); text-align: center; padding: 12px;">
            טרם הושלמו עבודות. שלח בקשה ליצירה!
        </div>

        <div class="result-container" id="resultContainer">
            <img id="resultImage" src="" alt="תוצאה אחרונה" style="display:none;" />
            <video id="resultVideo" controls autoplay loop muted style="display:none;"></video>
        </div>
    </div>

    <!-- Toast -->
    <div class="toast" id="toast">הודעה</div>

    <!-- JavaScript Logic -->
    <script>
        let currentFacingMode = 'environment';
        let mediaStream = null;
        let continuousInterval = null;
        let frameCount = 0;
        let facePhotos = [];
        let activeJobId = null;
        let statusPollInterval = null;

        const video = document.getElementById('videoPreview');
        const canvas = document.getElementById('captureCanvas');

        // Initialize Camera
        async function initCamera() {
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
            }

            try {
                const constraints = {
                    video: {
                        facingMode: { ideal: currentFacingMode },
                        width: { ideal: 1280 },
                        height: { ideal: 720 }
                    },
                    audio: false
                };

                mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
                video.srcObject = mediaStream;
                await video.play();
                showToast("המצלמה מחוברת בהצלחה");
            } catch (err) {
                console.error("Camera access error:", err);
                // Fallback attempt with simple constraints
                try {
                    mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
                    video.srcObject = mediaStream;
                    await video.play();
                } catch (e) {
                    showToast("שגיאה בגישה למצלמה: " + err.message);
                }
            }
        }

        function toggleCamera() {
            currentFacingMode = (currentFacingMode === 'environment') ? 'user' : 'environment';
            initCamera();
        }

        // Grab current frame as Base64 JPEG
        function getFrameBase64() {
            if (!video.videoWidth) return null;
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL('image/jpeg', 0.85);
        }

        // Visual shutter flash
        function triggerFlash() {
            const flash = document.getElementById('flashOverlay');
            flash.classList.add('active');
            setTimeout(() => flash.classList.remove('active'), 150);
            if (navigator.vibrate) navigator.vibrate(40);
        }

        // Single Capture Action
        async function takeSingleCapture() {
            const base64Data = getFrameBase64();
            if (!base64Data) {
                showToast("המצלמה עדיין טוענת...");
                return;
            }

            triggerFlash();

            try {
                const res = await fetch('/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: base64Data })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    showToast("📸 תמונה נשמרה בשרת: " + data.filename);
                } else {
                    showToast("שגיאה בלכידה: " + (data.error || "לא ידוע"));
                }
            } catch (err) {
                showToast("שגיאה בחיבור לשרת: " + err.message);
            }
        }

        // Toggle Continuous Streaming Mode
        function toggleContinuousMode() {
            const btn = document.getElementById('continuousBtn');
            const dot = document.getElementById('liveDot');
            const text = document.getElementById('liveStatusText');

            if (continuousInterval) {
                clearInterval(continuousInterval);
                continuousInterval = null;
                btn.classList.remove('active');
                btn.innerHTML = '🔄 מצב רציף (2 ש\')';
                dot.classList.remove('continuous');
                text.innerText = 'שידור חי';
                showToast("שידור רציף הופסק");
            } else {
                continuousInterval = setInterval(async () => {
                    const base64Data = getFrameBase64();
                    if (!base64Data) return;
                    frameCount++;
                    btn.innerHTML = `⏹️ עצור שידור (${frameCount})`;

                    try {
                        await fetch('/capture', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ image: base64Data })
                        });
                    } catch (e) {}
                }, 2000);

                btn.classList.add('active');
                dot.classList.add('continuous');
                text.innerText = 'שידור רציף פעיל 🔴';
                showToast("שידור רציף הופעל (כל 2 שניות)");
            }
        }

        // Face ID 3-Photo Capture
        function captureFacePhoto() {
            if (facePhotos.length >= 3) return;

            const base64Data = getFrameBase64();
            if (!base64Data) {
                showToast("המצלמה עדיין טוענת...");
                return;
            }

            triggerFlash();
            facePhotos.push(base64Data);

            const slotIndex = facePhotos.length;
            const slot = document.getElementById(`faceSlot${slotIndex}`);
            slot.classList.add('filled');
            slot.innerHTML = `<img src="${base64Data}" alt="תמונה ${slotIndex}">`;

            const btnCapture = document.getElementById('btnCaptureFace');
            const btnSubmit = document.getElementById('btnSubmitFaceId');

            if (facePhotos.length < 3) {
                btnCapture.innerText = `📸 צלם תמונת פנים (${facePhotos.length + 1}/3)`;
                showToast(`תמונה ${facePhotos.length} מתוך 3 נלכדה`);
            } else {
                btnCapture.style.display = 'none';
                btnSubmit.style.display = 'block';
                showToast("✅ 3 תמונות פנים מוכנות לשליחה!");
            }
        }

        function resetFacePhotos() {
            facePhotos = [];
            for (let i = 1; i <= 3; i++) {
                const slot = document.getElementById(`faceSlot${i}`);
                slot.classList.remove('filled');
                slot.innerHTML = `<span class="face-slot-label">תמונה ${i}</span>`;
            }

            const btnCapture = document.getElementById('btnCaptureFace');
            const btnSubmit = document.getElementById('btnSubmitFaceId');
            btnCapture.style.display = 'block';
            btnCapture.innerText = '📸 צלם תמונת פנים (1/3)';
            btnSubmit.style.display = 'none';
            showToast("איפוס תמונות פנים בוצע");
        }

        async function submitFaceIdJob() {
            if (facePhotos.length < 3) return;

            showToast("שולח 3 תמונות ליצירת Face ID...");

            try {
                const res = await fetch('/submit-face-id', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ images: facePhotos })
                });
                const data = await res.json();

                if (data.status === 'created' && data.job_id) {
                    showToast("🚀 עבודת Face ID נשלחה לתור!");
                    startJobTracking(data.job_id, "Face ID Model");
                    resetFacePhotos();
                } else {
                    showToast("שגיאה ביצירת Face ID: " + (data.error || "לא ידוע"));
                }
            } catch (err) {
                showToast("שגיאה בחיבור: " + err.message);
            }
        }

        // Quick Generate Job
        function applyPreset(text) {
            document.getElementById('promptInput').value = text;
        }

        async function submitQuickGenerate() {
            const prompt = document.getElementById('promptInput').value.trim();
            if (!prompt) {
                showToast("אנא הכנס תיאור (Prompt) ליצירה");
                return;
            }

            const includeFrame = document.getElementById('includeCameraFrame').checked;
            let cameraFrame = null;

            if (includeFrame) {
                cameraFrame = getFrameBase64();
                triggerFlash();
            }

            showToast("שולח בקשת יצירה...");

            try {
                const res = await fetch('/submit-generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: prompt, image: cameraFrame })
                });
                const data = await res.json();

                if (data.status === 'created' && data.job_id) {
                    showToast("🎨 עבודת יצירה נוספה לתור!");
                    startJobTracking(data.job_id, "Quick Generate");
                } else {
                    showToast("שגיאה ביצירת עבודה: " + (data.error || "לא ידוע"));
                }
            } catch (err) {
                showToast("שגיאה בחיבור: " + err.message);
            }
        }

        // Track Active Job Status
        function startJobTracking(jobId, jobTypeName) {
            activeJobId = jobId;

            document.getElementById('statusCard').style.display = 'block';
            document.getElementById('jobTypeLabel').innerText = jobTypeName;
            document.getElementById('jobIdLabel').innerText = "ID: " + jobId;
            document.getElementById('jobStatusBadge').innerText = "ממתין בתור ⏳";
            document.getElementById('jobStatusBadge').style.color = "var(--accent-amber)";
            document.getElementById('progressBar').style.width = "10%";

            if (statusPollInterval) clearInterval(statusPollInterval);

            statusPollInterval = setInterval(async () => {
                if (!activeJobId) return;

                try {
                    const res = await fetch(`/job-status/${activeJobId}`);
                    const data = await res.json();

                    if (data.status) {
                        const st = data.status;
                        const prog = data.progress || 0;

                        if (st === 'pending') {
                            document.getElementById('jobStatusBadge').innerText = "ממתין בתור ⏳";
                            document.getElementById('progressBar').style.width = "20%";
                        } else if (st === 'processing' || st === 'claimed') {
                            document.getElementById('jobStatusBadge').innerText = `בעבודה ⚙️ (${prog}%)`;
                            document.getElementById('jobStatusBadge').style.color = "var(--accent-blue)";
                            document.getElementById('progressBar').style.width = Math.max(30, prog) + "%";
                        } else if (st === 'completed') {
                            document.getElementById('jobStatusBadge').innerText = "הושלם בהצלחה! 🎉";
                            document.getElementById('jobStatusBadge').style.color = "var(--accent-emerald)";
                            document.getElementById('progressBar').style.width = "100%";
                            
                            clearInterval(statusPollInterval);
                            showToast("🎉 היצירה הושלמה בהצלחה!");
                            setTimeout(checkLatestResult, 1000);
                        } else if (st === 'failed') {
                            document.getElementById('jobStatusBadge').innerText = "נכשל ❌";
                            document.getElementById('jobStatusBadge').style.color = "var(--accent-red)";
                            clearInterval(statusPollInterval);
                            showToast("שגיאה בביצוע העבודה: " + (data.error_message || "לא ידוע"));
                        }
                    }
                } catch (e) {}
            }, 2500);
        }

        // Fetch & Render Latest Result
        async function checkLatestResult() {
            try {
                const res = await fetch('/latest-result');
                const data = await res.json();

                if (data.status === 'success' && data.output_url) {
                    document.getElementById('noResultText').style.display = 'none';
                    const container = document.getElementById('resultContainer');
                    const img = document.getElementById('resultImage');
                    const videoRes = document.getElementById('resultVideo');

                    container.style.display = 'block';

                    const url = data.output_url;
                    if (url.endsWith('.mp4') || url.endsWith('.webm')) {
                        img.style.display = 'none';
                        videoRes.style.display = 'block';
                        videoRes.src = url;
                    } else {
                        videoRes.style.display = 'none';
                        img.style.display = 'block';
                        img.src = url;
                    }
                }
            } catch (e) {}
        }

        // Show Toast Overlay
        function showToast(msg) {
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        // Initialize on load
        window.addEventListener('DOMContentLoaded', () => {
            initCamera();
            checkLatestResult();
        });
    </script>
</body>
</html>
"""


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ShimiStudio Phone Camera Bridge — ComfyUI Mobile Camera Server",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--ssl", action="store_true", help="Run server with adhoc HTTPS SSL context")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")

    args = parser.parse_args()

    pc_ip = get_local_ip()
    protocol = "https" if args.ssl else "http"
    camera_url = f"{protocol}://{pc_ip}:{args.port}/camera"
    local_url = f"{protocol}://localhost:{args.port}/camera"

    print("\n" + "=" * 64)
    print("  📷 ShimiStudio Phone Camera Bridge")
    print("  Turn your phone camera into a live input for ComfyUI & Base44")
    print("=" * 64)
    print(f"\n  📱 פתח בדפדפן בטלפון:   \033[1;32m{camera_url}\033[0m")
    print(f"  💻 גישה מקומית ב-PC:     {local_url}\n")
    print("=" * 64 + "\n")

    ssl_context = 'adhoc' if args.ssl else None

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            ssl_context=ssl_context
        )
    except KeyboardInterrupt:
        logger.info("\n👋 Phone Camera Bridge stopped by user.")


if __name__ == '__main__':
    main()


# ============================================================
# PhoneCameraBridge Class (for studio.py compatibility)
# ============================================================

class PhoneCameraBridge:
    """Wrapper class for the Flask phone camera bridge"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.app = app
    
    def start_server(self):
        """Start the Flask server"""
        print(f"Phone Camera Bridge starting on {self.host}:{self.port}")
        print(f"Open on your phone: http://{get_local_ip()}:{self.port}")
        app.run(host=self.host, port=self.port, debug=False)
    
    def stop_server(self):
        """Stop the server"""
        # Flask doesn't have a clean shutdown — Ctrl+C will stop it
        pass
    
    def get_latest_capture(self):
        """Get path to latest captured image"""
        captures = sorted(CAPTURES_DIR.glob("*.jpg"), key=lambda f: f.stat().st_mtime, reverse=True)
        return str(captures[0]) if captures else None
