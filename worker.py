"""
ShimiStudio Worker v2.1
Main worker daemon for local-first AI video and image production.
Added: lora_training, realtime_avatar support.
"""

import os
import sys
import time
import json
import traceback
from pathlib import Path
from typing import Dict, Any, Optional

from config import *
from base44_client import Base44Client
from comfyui_client import ComfyUIClient, submit_and_wait
from workflows import (
    get_workflow_for_job,
    build_text_to_image,
    build_image_to_video,
    build_text_to_video,
    build_face_swap,
    build_face_id,
    build_upscale,
    build_controlnet_pose,
    build_tts_lipsync,
)
from style_library import build_image_prompt, build_video_prompt
from free_api import generate_image_free, generate_video_free
from batch_generator import (
    batch_generate_images,
    batch_generate_videos,
    create_composite_scene,
)

# Try importing LoRA trainer (optional — only needed for lora_training jobs)
try:
    from lora_trainer import process_lora_training_job
    LORA_AVAILABLE = True
except ImportError:
    LORA_AVAILABLE = False


class ShimiStudioWorker:
    """
    Main worker process for processing RenderJobs from Base44.
    Supports: text_to_image, image_to_video, text_to_video, face_swap, face_id,
              upscale, controlnet_pose, tts_lipsync, lora_training, realtime_avatar.
    """

    def __init__(
        self,
        worker_id: str = WORKER_ID,
        comfyui_url: str = COMFYUI_URL,
    ):
        self.worker_id = worker_id or WORKER_ID
        self.comfyui_url = comfyui_url or COMFYUI_URL
        self.base44_client = Base44Client(app_id=BASE44_APP_ID, entity_name=BASE44_ENTITY)
        self.comfyui = ComfyUIClient(self.comfyui_url)
        self.logger = setup_logger("worker")
        self.running = False

    def check_comfyui(self) -> bool:
        """Verifies if ComfyUI server is reachable."""
        return self.comfyui.is_running()

    def process_job(self, job: dict) -> bool:
        """
        Processes a single job dictionary from Base44 queue.
        Dispatches according to job_type, handles ComfyUI/Free API execution,
        uploads result, and updates Base44 status.
        """
        job_id = job.get("id") or job.get("_id")
        if not job_id:
            self.logger.error("Cannot process job without an 'id' field")
            return False

        job_type = job.get("job_type", "text_to_image")
        prompt = job.get("prompt", "")
        negative_prompt = job.get("negative_prompt", "")

        # Parse parameters if formatted as string
        parameters = job.get("parameters", {})
        if isinstance(parameters, str):
            try:
                parameters = json.loads(parameters)
            except Exception:
                parameters = {}

        self.logger.info(f"Processing job [{job_id}] type={job_type}, prompt='{prompt[:50]}...'")

        try:
            output_filepath = None
            result_type = "image"

            # ── LoRA Training ──────────────────────────────────
            if job_type == "lora_training":
                if not LORA_AVAILABLE:
                    raise RuntimeError(
                        "lora_trainer.py not available. Install training deps: "
                        "pip install peft diffusers accelerate safetensors"
                    )
                self.logger.info(f"Starting LoRA training for '{prompt}' with {len(job.get('face_images', []))} images")
                self.base44_client.update_progress(job_id, 10)

                result = process_lora_training_job(job)
                if result.get("success"):
                    output_url = result.get("lora_url") or result.get("output_url", "")
                    self.base44_client.complete_job(
                        job_id=job_id,
                        output_url=output_url,
                        result_type="lora",
                    )
                    self.logger.info(f"LoRA training completed: {output_url}")
                    return True
                else:
                    raise RuntimeError(result.get("error", "LoRA training failed"))

            # ── Realtime Avatar (streaming — no batch output) ──
            elif job_type == "realtime_avatar":
                result_type = "video"
                if not self.check_comfyui():
                    raise RuntimeError("ComfyUI is required for realtime_avatar but is not running.")
                # Realtime avatar is a streaming pipeline, not a batch job.
                # The worker reports it as completed with a placeholder URL.
                # The actual streaming happens via WebRTC connection to ComfyUI.
                self.logger.info("Realtime avatar job — streaming mode")
                self.base44_client.update_progress(job_id, 50)
                # Mark as completed — the actual streaming is handled by phone_camera.py
                self.base44_client.complete_job(
                    job_id=job_id,
                    output_url="realtime_stream_active",
                    result_type="stream",
                )
                self.logger.info("Realtime avatar stream started")
                return True

            # 1. Batch jobs handling
            if job_type == "batch_image":
                styles = parameters.get("styles")
                moods = parameters.get("moods")
                faceid_id = parameters.get("faceid_id")
                aspect_ratio = parameters.get("aspect_ratio", "1:1")
                character = parameters.get("character")
                sub_jobs = batch_generate_images(
                    base_prompt=prompt,
                    styles=styles,
                    moods=moods,
                    faceid_id=faceid_id,
                    aspect_ratio=aspect_ratio,
                    character=character,
                )
                created_count = 0
                for sj in sub_jobs:
                    self.base44_client.create_job(**sj)
                    created_count += 1
                self.base44_client.complete_job(
                    job_id=job_id,
                    output_url=f"Successfully created {created_count} image jobs",
                    result_type="batch",
                )
                return True

            elif job_type == "batch_video":
                video_styles = parameters.get("video_styles")
                faceid_id = parameters.get("faceid_id")
                custom_video_prompt = parameters.get("custom_video_prompt")
                sub_jobs = batch_generate_videos(
                    base_image_prompt=prompt,
                    video_styles=video_styles,
                    faceid_id=faceid_id,
                    custom_video_prompt=custom_video_prompt,
                )
                created_count = 0
                for sj in sub_jobs:
                    self.base44_client.create_job(**sj)
                    created_count += 1
                self.base44_client.complete_job(
                    job_id=job_id,
                    output_url=f"Successfully created {created_count} video jobs",
                    result_type="batch",
                )
                return True

            elif job_type == "composite_scene":
                face_ids = parameters.get("face_ids", [])
                outfit_ids = parameters.get("outfit_ids")
                location_ids = parameters.get("location_ids")
                action = parameters.get("action", "")
                style = parameters.get("style", "cinematic")
                mood = parameters.get("mood", "sensual")
                aspect_ratio = parameters.get("aspect_ratio", "16:9")
                scene_job = create_composite_scene(
                    face_ids=face_ids,
                    outfit_ids=outfit_ids,
                    location_ids=location_ids,
                    action=action,
                    style=style,
                    mood=mood,
                    aspect_ratio=aspect_ratio,
                )
                created = self.base44_client.create_job(**scene_job)
                created_id = created.get("id") if isinstance(created, dict) else "composite_created"
                self.base44_client.complete_job(
                    job_id=job_id,
                    output_url=f"Created composite scene job: {created_id}",
                    result_type="composite",
                )
                return True

            # 2. Individual job handlers
            comfy_running = self.check_comfyui()

            if job_type == "text_to_image":
                width = parameters.get("width", 1024)
                height = parameters.get("height", 1024)

                if (ENGINE_MODE in ("auto", "free_api")) and not comfy_running:
                    self.logger.info("ComfyUI not running. Falling back to free API for text_to_image...")
                    free_res = generate_image_free(
                        prompt=prompt,
                        negative=negative_prompt,
                        width=width,
                        height=height,
                    )
                    if isinstance(free_res, dict) and "error" in free_res:
                        raise RuntimeError(f"Free API image generation failed: {free_res['error']}")
                    output_filepath = free_res.get("url") if isinstance(free_res, dict) else free_res
                else:
                    wf = build_text_to_image(prompt=prompt, negative_prompt=negative_prompt, parameters=parameters)
                    output_filepath = self.comfyui.submit_and_wait(wf)

            elif job_type == "image_to_video":
                result_type = "video"
                reference_image = job.get("reference_image") or parameters.get("reference_image", "")
                if comfy_running:
                    wf = build_image_to_video(prompt=prompt, reference_image=reference_image, parameters=parameters)
                    output_filepath = self.comfyui.submit_and_wait(wf)
                else:
                    self.logger.info("ComfyUI not running. Falling back to free video API...")
                    free_res = generate_video_free(prompt=prompt, image_url=reference_image)
                    if isinstance(free_res, dict) and "error" in free_res:
                        raise RuntimeError(f"Free video API generation failed: {free_res['error']}")
                    output_filepath = free_res.get("url") if isinstance(free_res, dict) else free_res

            elif job_type == "text_to_video":
                result_type = "video"
                if comfy_running:
                    wf = build_text_to_video(prompt=prompt, negative_prompt=negative_prompt, parameters=parameters)
                    output_filepath = self.comfyui.submit_and_wait(wf)
                else:
                    self.logger.info("ComfyUI not running. Falling back to free video API...")
                    free_res = generate_video_free(prompt=prompt)
                    if isinstance(free_res, dict) and "error" in free_res:
                        raise RuntimeError(f"Free video API generation failed: {free_res['error']}")
                    output_filepath = free_res.get("url") if isinstance(free_res, dict) else free_res

            elif job_type == "face_swap":
                reference_image = job.get("reference_image") or parameters.get("reference_image", "")
                face_swap_target = job.get("face_swap_target") or parameters.get("face_swap_target", "")
                if not comfy_running:
                    raise RuntimeError("ComfyUI is required for face_swap but is not running.")
                wf = build_face_swap(reference_image=reference_image, face_swap_target=face_swap_target, parameters=parameters)
                output_filepath = self.comfyui.submit_and_wait(wf)

            elif job_type == "face_id":
                face_images = job.get("face_images") or parameters.get("face_images", [])
                if isinstance(face_images, str):
                    try:
                        face_images = json.loads(face_images)
                    except Exception:
                        face_images = [face_images]
                if not comfy_running:
                    raise RuntimeError("ComfyUI is required for face_id but is not running.")
                wf = build_face_id(prompt=prompt, face_images=face_images, parameters=parameters)
                output_filepath = self.comfyui.submit_and_wait(wf)

            elif job_type == "upscale":
                reference_image = job.get("reference_image") or parameters.get("reference_image", "")
                if not comfy_running:
                    raise RuntimeError("ComfyUI is required for upscale but is not running.")
                wf = build_upscale(reference_image=reference_image, parameters=parameters)
                output_filepath = self.comfyui.submit_and_wait(wf)

            elif job_type == "controlnet_pose":
                reference_image = job.get("reference_image") or parameters.get("reference_image", "")
                if not comfy_running:
                    raise RuntimeError("ComfyUI is required for controlnet_pose but is not running.")
                wf = build_controlnet_pose(prompt=prompt, reference_image=reference_image, parameters=parameters)
                output_filepath = self.comfyui.submit_and_wait(wf)

            elif job_type == "tts_lipsync":
                result_type = "video"
                voice_text = job.get("voice_text") or parameters.get("voice_text", prompt)
                reference_image = job.get("reference_image") or parameters.get("reference_image", "")
                if not comfy_running:
                    raise RuntimeError("ComfyUI is required for tts_lipsync but is not running.")
                wf = build_tts_lipsync(voice_text=voice_text, reference_image=reference_image, parameters=parameters)
                output_filepath = self.comfyui.submit_and_wait(wf)

            else:
                raise ValueError(f"Unknown or unsupported job_type: {job_type}")

            # 3. Handle generated output upload and completion
            if not output_filepath:
                raise RuntimeError(f"Job processing produced no output filepath for job [{job_id}]")

            self.base44_client.update_progress(job_id, 90)

            # If output is already a remote URL (e.g. from free API), use directly; else upload
            if str(output_filepath).startswith("http://") or str(output_filepath).startswith("https://"):
                output_url = str(output_filepath)
            else:
                output_url = self.base44_client.upload_output(str(output_filepath))

            self.base44_client.complete_job(
                job_id=job_id,
                output_url=output_url,
                result_type=result_type,
            )
            self.logger.info(f"Job [{job_id}] completed successfully -> {output_url}")
            return True

        except Exception as e:
            err_msg = str(e)
            self.logger.error(f"Job [{job_id}] failed: {err_msg}")
            self.logger.debug(traceback.format_exc())
            try:
                self.base44_client.fail_job(job_id=job_id, error_message=err_msg)
            except Exception as update_err:
                self.logger.error(f"Failed to set job status to failed: {update_err}")
            return False

    def run(self):
        """
        Main worker loop. Continuously checks pending jobs from Base44,
        claims them, executes them, and handles graceful shutdown on interrupt.
        """
        self.running = True
        self.logger.info(f"ShimiStudio Worker [{self.worker_id}] starting...")
        self.logger.info(f"ComfyUI URL: {self.comfyui_url} | Engine Mode: {ENGINE_MODE} | Poll Interval: {POLL_INTERVAL}s")
        if LORA_AVAILABLE:
            self.logger.info("LoRA training: available")
        else:
            self.logger.info("LoRA training: not available (install peft diffusers accelerate to enable)")

        while self.running:
            try:
                # If engine mode explicitly mandates comfyui, check it
                if ENGINE_MODE == "comfyui" and not self.check_comfyui():
                    self.logger.warning("ComfyUI server is unreachable (ENGINE_MODE='comfyui'). Waiting...")
                    time.sleep(POLL_INTERVAL)
                    continue

                pending_jobs = self.base44_client.get_pending_jobs(limit=5)
                if not pending_jobs:
                    time.sleep(POLL_INTERVAL)
                    continue

                self.logger.info(f"Fetched {len(pending_jobs)} pending job(s)")
                for job in pending_jobs:
                    if not self.running:
                        break

                    job_id = job.get("id") or job.get("_id")
                    if not job_id:
                        continue

                    claimed_job = self.base44_client.claim_job(job_id=job_id, worker_id=self.worker_id)
                    if claimed_job:
                        job_to_process = claimed_job if isinstance(claimed_job, dict) and "job_type" in claimed_job else job
                        self.process_job(job_to_process)

            except KeyboardInterrupt:
                self.logger.info("KeyboardInterrupt received. Shutting down worker...")
                self.stop()
                break
            except Exception as e:
                self.logger.error(f"Error in worker main loop: {e}")
                time.sleep(POLL_INTERVAL)

    def stop(self):
        """Stops the worker daemon."""
        self.logger.info(f"Stopping ShimiStudio Worker [{self.worker_id}]...")
        self.running = False


if __name__ == "__main__":
    worker = ShimiStudioWorker()
    try:
        worker.run()
    except KeyboardInterrupt:
        worker.stop()
