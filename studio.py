#!/usr/bin/env python3
"""
ShimiStudio v2.0 — Main CLI Entry Point
הכניסה הראשית למערכת. כל הפקודות עוברות דרך כאן.
"""

import argparse
import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    print_config, setup_logger, COMFYUI_URL, BASE44_APP_ID,
    WORKER_ID, POLL_INTERVAL, ENGINE_MODE, OUTPUT_DIR, API_KEYS,
)
from style_library import (
    list_styles, list_moods, list_video_styles, list_characters,
    list_prompt_packs, get_prompt_pack, build_image_prompt, build_video_prompt,
)
from comfyui_client import ComfyUIClient
from workflows import (
    build_text_to_image, build_image_to_video, build_text_to_video,
    build_face_swap, build_face_id, build_upscale, build_controlnet_pose,
)
from base44_client import Base44Client
from free_api import generate_image_free, generate_video_free, get_usage_status
from batch_generator import (
    batch_generate_images, batch_generate_videos, run_batch_from_pack,
    list_prompt_packs as list_packs, get_prompt_pack as get_pack,
    PROMPT_PACKS,
)
from pipeline import ProductionPipeline, quick_image, quick_video, quick_face_swap


def cmd_status(args):
    """מצב המערכת"""
    print("=" * 60)
    print("  ShimiStudio v2.0 — System Status")
    print("=" * 60)

    # Config
    print_config()

    # ComfyUI
    print("\n--- ComfyUI ---")
    try:
        client = ComfyUIClient()
        if client.is_running():
            stats = client.get_system_stats()
            print(f"  Status: ✅ Running at {COMFYUI_URL}")
            sys_info = stats.get("data", {}).get("system", {})
            print(f"  GPU: {sys_info.get('devices', [{}])[0].get('name', 'Unknown') if sys_info.get('devices') else 'No GPU'}")
        else:
            print(f"  Status: ❌ Not running (Fallback: Free API)")
    except Exception as e:
        print(f"  Status: ❌ Error: {e}")

    # Base44
    print("\n--- Base44 ---")
    print(f"  App ID: {BASE44_APP_ID}")
    print(f"  Entity: RenderJob")
    try:
        b44 = Base44Client()
        pending = b44.get_pending_jobs(limit=1)
        print(f"  Connection: ✅ ({len(pending)} pending jobs)")
    except Exception as e:
        print(f"  Connection: ❌ {e}")

    # Free APIs
    print("\n--- Free API Providers ---")
    status = get_usage_status()
    for name, info in status.items():
        remaining = info.get("remaining", 0)
        limit = info.get("limit", 0)
        nsfw = "✅" if info.get("nsfw") else "❌"
        print(f"  {name:15s} {remaining:4d}/{limit:4d} remaining  NSFW={nsfw}")

    # API Keys
    print("\n--- API Keys ---")
    for name, key in API_KEYS.items():
        status = "✅" if key else "❌"
        print(f"  {name:15s} {status}")


def cmd_worker(args):
    """הפעלת Worker"""
    from worker import ShimiStudioWorker
    worker = ShimiStudioWorker(worker_id=WORKER_ID)
    print(f"Starting worker {WORKER_ID}...")
    try:
        worker.run()
    except KeyboardInterrupt:
        print("\nWorker stopped.")


def cmd_generate(args):
    """יצירת תמונה"""
    pipeline = ProductionPipeline()
    image_path = pipeline.step_generate_image(
        prompt=args.prompt,
        negative=args.negative or "",
        style=args.style or "photorealistic",
        mood=args.mood or "sensual",
        width=args.width or 1024,
        height=args.height or 1024,
    )
    if image_path:
        print(f"✅ Image saved: {image_path}")
    else:
        print("❌ Generation failed")


def cmd_video(args):
    """יצירת וידאו"""
    pipeline = ProductionPipeline()

    if args.image:
        # Image to video
        video_path = pipeline.step_animate_image(
            image_path=args.image,
            video_prompt=args.prompt,
            duration=args.duration or 5,
            width=args.width or 1280,
            height=args.height or 720,
        )
    else:
        # Text to video (generate image first)
        video_path = quick_video(args.prompt, duration=args.duration or 5)

    if video_path:
        print(f"✅ Video saved: {video_path}")
    else:
        print("❌ Generation failed")


def cmd_face_swap(args):
    """Face Swap"""
    result = quick_face_swap(args.source, args.target)
    if result:
        print(f"✅ Face swap saved: {result}")
    else:
        print("❌ Face swap failed")


def cmd_face_id(args):
    """FaceID"""
    pipeline = ProductionPipeline()
    result = pipeline.step_apply_face_id(
        reference_image=args.reference,
        prompt=args.prompt,
        style=args.style or "photorealistic",
    )
    if result:
        print(f"✅ FaceID image saved: {result}")
    else:
        print("❌ FaceID failed")


def cmd_batch(args):
    """Batch Generation"""
    if args.pack:
        # Use prompt pack
        jobs = run_batch_from_pack(
            pack_name=args.pack,
            styles=args.styles.split(",") if args.styles else None,
            moods=args.moods.split(",") if args.moods else None,
            faceid_id=args.faceid,
        )
    else:
        # Custom batch
        jobs = batch_generate_images(
            base_prompt=args.prompt or "",
            styles=args.styles.split(",") if args.styles else ["photorealistic"],
            moods=args.moods.split(",") if args.moods else ["sensual"],
            faceid_id=args.faceid,
        )

    print(f"Generated {len(jobs)} jobs:")
    for i, job in enumerate(jobs):
        print(f"  {i+1}. {job.get('job_type')} — {job.get('parameters', {}).get('style', '')} / {job.get('parameters', {}).get('mood', '')}")

    # Submit to Base44 if --submit
    if args.submit:
        b44 = Base44Client()
        for job in jobs:
            try:
                result = b44.create_job(
                    job_type=job["job_type"],
                    prompt=job["prompt"],
                    parameters=job.get("parameters"),
                )
                print(f"  ✅ Submitted: {result.get('id', 'unknown')}")
            except Exception as e:
                print(f"  ❌ Failed: {e}")
    else:
        print("\nUse --submit to send to Base44 queue")


def cmd_pipeline(args):
    """פייפליין מלא"""
    pipeline = ProductionPipeline()
    config = {
        "prompt": args.prompt,
        "style": args.style or "photorealistic",
        "mood": args.mood or "sensual",
        "face_reference": args.face_reference,
        "video_style": args.video_style or "pool_scene",
        "duration": args.duration or 5,
        "voice_text": args.voice_text,
        "voice": args.voice or "en-US-AriaNeural",
        "upscale": args.upscale or 0,
    }
    result = pipeline.run_full_pipeline(config)
    if result.get("success"):
        print(f"\n✅ Pipeline completed: {result['steps_completed']}")
        print(f"   Final output: {result['final_output']}")
    else:
        print(f"\n❌ Pipeline failed: {result.get('error', 'unknown')}")
        print(f"   Steps completed: {result.get('steps_completed', [])}")


def cmd_camera(args):
    """מצלמת פלאפון"""
    from phone_camera import PhoneCameraBridge
    bridge = PhoneCameraBridge(host="0.0.0.0", port=args.port or 5000)
    print(f"Starting phone camera server on port {args.port or 5000}...")
    bridge.start_server()


def cmd_list(args):
    """רשימת סטיילים/מודים/דמויות"""
    type_map = {
        "styles": ("Styles", list_styles),
        "moods": ("Moods", list_moods),
        "video_styles": ("Video Styles", list_video_styles),
        "characters": ("Characters", list_characters),
        "packs": ("Prompt Packs", lambda: [(k, v["name"]) for k, v in PROMPT_PACKS.items()]),
    }

    if args.type in type_map:
        title, func = type_map[args.type]
        print(f"\n{title}:")
        for key, name in func():
            print(f"  {key:20s} → {name}")
    else:
        print("Available types: styles, moods, video_styles, characters, packs")


def cmd_config(args):
    """הגדרות"""
    print_config()


def cmd_test(args):
    """בדיקות מערכת"""
    print("=" * 60)
    print("  ShimiStudio v2.0 — System Tests")
    print("=" * 60)

    tests_passed = 0
    tests_failed = 0

    def test(name, condition, detail=""):
        nonlocal tests_passed, tests_failed
        if condition:
            print(f"  ✅ {name}")
            tests_passed += 1
        else:
            print(f"  ❌ {name} — {detail}")
            tests_failed += 1

    # Test 1: Config
    try:
        from config import BASE_DIR
        test("Config module", True)
    except Exception as e:
        test("Config module", False, str(e))

    # Test 2: Style library
    try:
        from style_library import STYLES, MOODS, CHARACTERS
        test(f"Style library ({len(STYLES)} styles)", len(STYLES) >= 12)
        test(f"Moods ({len(MOODS)})", len(MOODS) >= 8)
        test(f"Characters ({len(CHARACTERS)})", len(CHARACTERS) >= 6)
    except Exception as e:
        test("Style library", False, str(e))

    # Test 3: Workflows
    try:
        wf = build_text_to_image("test", "negative")
        test("Text-to-image workflow", isinstance(wf, dict) and len(wf) > 0)
    except Exception as e:
        test("Text-to-image workflow", False, str(e))

    try:
        wf = build_image_to_video("test.png", "video prompt")
        test("Image-to-video workflow", isinstance(wf, dict) and len(wf) > 0)
    except Exception as e:
        test("Image-to-video workflow", False, str(e))

    # Test 4: Free APIs
    try:
        status = get_usage_status()
        test(f"Free API providers ({len(status)})", len(status) >= 3)
    except Exception as e:
        test("Free API providers", False, str(e))

    # Test 5: ComfyUI
    try:
        client = ComfyUIClient()
        running = client.is_running()
        test("ComfyUI connection", running, f"Run ComfyUI at {COMFYUI_URL}")
    except Exception as e:
        test("ComfyUI connection", False, str(e))

    # Test 6: Base44
    try:
        b44 = Base44Client()
        jobs = b44.get_pending_jobs(limit=1)
        test("Base44 connection", True)
    except Exception as e:
        test("Base44 connection", False, str(e))

    # Test 7: Pipeline
    try:
        p = ProductionPipeline()
        test("Pipeline module", True)
    except Exception as e:
        test("Pipeline module", False, str(e))

    print(f"\n{'=' * 60}")
    print(f"  Results: {tests_passed} passed, {tests_failed} failed")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        description="ShimiStudio v2.0 — Local AI Content Production",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  status        Show system status
  worker        Start the job worker
  generate      Generate a single image
  video         Generate video from image or text
  face-swap     Face swap between two images
  face-id       Generate image with FaceID
  batch         Batch generation
  pipeline      Full production pipeline
  camera        Start phone camera server
  list          List available styles/moods/characters
  config        Show configuration
  test          Run system tests
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status
    subparsers.add_parser("status", help="Show system status")

    # Worker
    subparsers.add_parser("worker", help="Start the job worker")

    # Generate
    gen = subparsers.add_parser("generate", help="Generate a single image")
    gen.add_argument("--prompt", "-p", required=True, help="Image prompt")
    gen.add_argument("--negative", "-n", default="", help="Negative prompt")
    gen.add_argument("--style", "-s", default="photorealistic", help="Style")
    gen.add_argument("--mood", "-m", default="sensual", help="Mood")
    gen.add_argument("--width", type=int, default=1024)
    gen.add_argument("--height", type=int, default=1024)

    # Video
    vid = subparsers.add_parser("video", help="Generate video")
    vid.add_argument("--prompt", "-p", required=True, help="Video prompt")
    vid.add_argument("--image", "-i", help="Source image (for I2V)")
    vid.add_argument("--duration", type=int, default=5)
    vid.add_argument("--width", type=int, default=1280)
    vid.add_argument("--height", type=int, default=720)

    # Face Swap
    fs = subparsers.add_parser("face-swap", help="Face swap")
    fs.add_argument("--source", required=True, help="Source face image")
    fs.add_argument("--target", required=True, help="Target image/video")

    # Face ID
    fid = subparsers.add_parser("face-id", help="Generate with FaceID")
    fid.add_argument("--reference", required=True, help="Reference face image")
    fid.add_argument("--prompt", "-p", required=True)
    fid.add_argument("--style", "-s", default="photorealistic")

    # Batch
    bat = subparsers.add_parser("batch", help="Batch generation")
    bat.add_argument("--prompt", "-p", help="Base prompt")
    bat.add_argument("--pack", help="Prompt pack name")
    bat.add_argument("--styles", help="Comma-separated styles")
    bat.add_argument("--moods", help="Comma-separated moods")
    bat.add_argument("--faceid", help="FaceID ID")
    bat.add_argument("--submit", action="store_true", help="Submit to Base44")

    # Pipeline
    pip = subparsers.add_parser("pipeline", help="Full production pipeline")
    pip.add_argument("--prompt", "-p", required=True)
    pip.add_argument("--style", "-s", default="photorealistic")
    pip.add_argument("--mood", "-m", default="sensual")
    pip.add_argument("--face-reference", help="Face reference image")
    pip.add_argument("--video-style", default="pool_scene")
    pip.add_argument("--duration", type=int, default=5)
    pip.add_argument("--voice-text", help="TTS text")
    pip.add_argument("--voice", default="en-US-AriaNeural")
    pip.add_argument("--upscale", type=int, default=0)

    # Camera
    cam = subparsers.add_parser("camera", help="Start phone camera server")
    cam.add_argument("--port", type=int, default=5000)

    # List
    lst = subparsers.add_parser("list", help="List available options")
    lst.add_argument("--type", "-t", default="styles", choices=["styles", "moods", "video_styles", "characters", "packs"])

    # Config
    subparsers.add_parser("config", help="Show configuration")

    # Test
    subparsers.add_parser("test", help="Run system tests")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "status": cmd_status,
        "worker": cmd_worker,
        "generate": cmd_generate,
        "video": cmd_video,
        "face-swap": cmd_face_swap,
        "face-id": cmd_face_id,
        "batch": cmd_batch,
        "pipeline": cmd_pipeline,
        "camera": cmd_camera,
        "list": cmd_list,
        "config": cmd_config,
        "test": cmd_test,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
