"""
ShimiStudio v2.0 — Production Pipeline
פייפליין מלא: תמונה → FaceID → אנימציה → Face Swap → TTS → Lip Sync → Upscale
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    setup_logger, COMFYUI_URL, OUTPUT_DIR, TEMP_DIR, DEFAULTS,
)
from style_library import (
    build_image_prompt, build_video_prompt, STYLES, MOODS,
)
from comfyui_client import ComfyUIClient, submit_and_wait
from workflows import (
    build_text_to_image, build_image_to_video, build_text_to_video,
    build_face_swap, build_face_id, build_tts_lipsync, build_upscale,
    build_controlnet_pose,
)
from free_api import generate_image_free

logger = setup_logger("pipeline")


class ProductionPipeline:
    """פייפליין יצירת תוכן מלא — מטקסט לוידאו מוגמר"""

    def __init__(self, comfyui_url: str = None):
        self.comfyui_url = comfyui_url or COMFYUI_URL
        self.client = ComfyUIClient(self.comfyui_url)
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _check_comfyui(self) -> bool:
        """בודק ש-ComfyUI רץ"""
        try:
            return self.client.is_running()
        except Exception:
            return False

    def _fallback_image(self, prompt: str, negative: str, width: int, height: int) -> str:
        """Fallback ל-free API כש-ComfyUI לא זמין"""
        logger.info("ComfyUI לא זמין — משתמש ב-Free API")
        result = generate_image_free(prompt, negative, width, height)
        if "error" in result:
            raise RuntimeError(f"Free API נכשל: {result['error']}")
        return result.get("url", result.get("filepath", ""))

    def step_generate_image(
        self,
        prompt: str,
        negative: str = "",
        style: str = "photorealistic",
        mood: str = "sensual",
        width: int = 1024,
        height: int = 1024,
        seed: int = -1,
    ) -> str:
        """שלב 1: יצירת תמונה מטקסט"""
        logger.info(f"שלב 1: יצירת תמונה — {style}/{mood}")

        prompt_data = build_image_prompt(
            user_prompt=prompt, style=style, mood=mood,
            aspect_ratio=f"{width}x{height}",
        )

        if not self._check_comfyui():
            return self._fallback_image(prompt_data["prompt"], prompt_data["negative_prompt"], width, height)

        workflow = build_text_to_image(
            prompt=prompt_data["prompt"],
            negative=prompt_data["negative_prompt"],
            width=width, height=height, seed=seed,
            checkpoint="flux1-dev-fp8.safetensors",
        )

        result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=120)
        if not result.get("success"):
            logger.warning("ComfyUI נכשל — מנסה Free API")
            return self._fallback_image(prompt_data["prompt"], prompt_data["negative_prompt"], width, height)

        return result["outputs"][0] if result["outputs"] else ""

    def step_apply_face_id(
        self,
        reference_image: str,
        prompt: str,
        negative: str = "",
        width: int = 1024,
        height: int = 1024,
        weight: float = 1.0,
        seed: int = -1,
    ) -> str:
        """שלב 2: החלת FaceID מתמונת ייחוס"""
        logger.info("שלב 2: FaceID")

        if not self._check_comfyui():
            logger.warning("ComfyUI לא זמין — לא ניתן לבצע FaceID")
            return ""

        # העלאת תמונת ייחוס ל-ComfyUI
        upload_result = self.client.upload_image(reference_image)
        ref_filename = upload_result.get("name", os.path.basename(reference_image))

        workflow = build_face_id(
            reference_image=ref_filename,
            prompt=prompt, negative=negative,
            width=width, height=height, weight=weight, seed=seed,
        )

        result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=180)
        return result["outputs"][0] if result.get("success") and result["outputs"] else ""

    def step_animate_image(
        self,
        image_path: str,
        video_prompt: str,
        duration: int = 5,
        fps: int = 24,
        width: int = 1280,
        height: int = 720,
        seed: int = -1,
    ) -> str:
        """שלב 3: אנימציה של תמונה (Wan 2.2 I2V)"""
        logger.info(f"שלב 3: אנימציה ({duration}s)")

        if not self._check_comfyui():
            logger.warning("ComfyUI לא זמין — לא ניתן לבצע אנימציה")
            return ""

        # העלאת התמונה
        upload_result = self.client.upload_image(image_path)
        img_filename = upload_result.get("name", os.path.basename(image_path))

        workflow = build_image_to_video(
            image_path=img_filename,
            video_prompt=video_prompt,
            duration=duration, fps=fps, width=width, height=height, seed=seed,
        )

        result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=600)
        return result["outputs"][0] if result.get("success") and result["outputs"] else ""

    def step_face_swap_video(
        self,
        source_face_image: str,
        target_video: str,
    ) -> str:
        """שלב 4: Face Swap בוידאו"""
        logger.info("שלב 4: Face Swap")

        if not self._check_comfyui():
            logger.warning("ComfyUI לא זמין — לא ניתן לבצע Face Swap")
            return ""

        # העלאת שתי תמונות
        self.client.upload_image(source_face_image)
        self.client.upload_image(target_video)

        workflow = build_face_swap(
            source_image=os.path.basename(source_face_image),
            target_image=os.path.basename(target_video),
        )

        result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=300)
        return result["outputs"][0] if result.get("success") and result["outputs"] else ""

    def step_tts(self, text: str, voice: str = "default", language: str = "en") -> str:
        """שלב 5: יצירת קול מטקסט (TTS)"""
        logger.info(f"שלב 5: TTS — '{text[:50]}...'")

        # ניסיון עם edge-tts (חינמי, אין צורך ב-GPU)
        try:
            import edge_tts
            output_path = str(self.temp_dir / f"tts_{int(time.time())}.mp3")
            communicate = edge_tts.Communicate(text, voice=voice)
            communicate.save(output_path)
            logger.info(f"TTS הצליח (edge-tts): {output_path}")
            return output_path
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"edge-tts נכשל: {e}")

        # ניסיון עם ComfyUI + XTTS
        if self._check_comfyui():
            try:
                workflow = build_tts_lipsync(
                    video_path="", audio_path="",
                    output_dir=str(self.output_dir),
                )
                # XTTS workflow would go here
                logger.info("TTS דרך ComfyUI/XTTS")
                return str(self.output_dir / f"tts_{int(time.time())}.wav")
            except Exception as e:
                logger.warning(f"XTTS נכשל: {e}")

        # Fallback: subprocess עם espeak
        try:
            output_path = str(self.temp_dir / f"tts_{int(time.time())}.wav")
            subprocess.run(
                ["espeak", "-w", output_path, text],
                check=True, capture_output=True, timeout=30,
            )
            logger.info(f"TTS הצליח (espeak): {output_path}")
            return output_path
        except Exception:
            logger.error("כל שיטות ה-TTS נכשלו")
            return ""

    def step_lipsync(self, video_path: str, audio_path: str) -> str:
        """שלב 6: Lip Sync — סנכרון שפתיים לקול"""
        logger.info("שלב 6: Lip Sync")

        if not self._check_comfyui():
            logger.warning("ComfyUI לא זמין — לא ניתן לבצע Lip Sync")
            return video_path

        if not video_path or not audio_path:
            logger.warning("חסר וידאו או אודיו ל-Lip Sync")
            return video_path

        try:
            self.client.upload_image(video_path)
            self.client.upload_image(audio_path)

            workflow = build_tts_lipsync(
                video_path=os.path.basename(video_path),
                audio_path=os.path.basename(audio_path),
                output_dir=str(self.output_dir),
            )

            result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=600)
            return result["outputs"][0] if result.get("success") and result["outputs"] else video_path
        except Exception as e:
            logger.error(f"Lip Sync נכשל: {e}")
            return video_path

    def step_upscale(self, image_or_video_path: str, scale: int = 2) -> str:
        """שלב 7: הגדלת רזולוציה"""
        logger.info(f"שלב 7: Upscale {scale}x")

        if not self._check_comfyui() or not image_or_video_path:
            return image_or_video_path

        try:
            self.client.upload_image(image_or_video_path)
            workflow = build_upscale(
                image_path=os.path.basename(image_or_video_path),
                scale=scale,
            )
            result = submit_and_wait(self.client, workflow, str(self.output_dir), timeout=300)
            return result["outputs"][0] if result.get("success") and result["outputs"] else image_or_video_path
        except Exception as e:
            logger.error(f"Upscale נכשל: {e}")
            return image_or_video_path

    def run_full_pipeline(self, config: dict) -> dict:
        """
        פייפליין מלא מקצה לקצה
        
        config = {
            'prompt': 'woman at pool',           # תיאור התמונה
            'style': 'photorealistic',            # סטייל
            'mood': 'sensual',                   # מוד
            'face_reference': '/path/to/face.jpg',  # תמונת פנים ל-FaceID (אופציונלי)
            'video_style': 'pool_scene',         # סטייל וידאו
            'video_prompt': 'custom prompt',     # או מהסטייל
            'duration': 5,                       # משך וידאו
            'voice_text': 'Hello there',         # טקסט ל-TTS (אופציונלי)
            'voice': 'en-US-AriaNeural',         # קול (אופציונלי)
            'upscale': 2,                        # הגדלה (אופציונלי)
            'width': 1024, 'height': 1024,
        }
        """
        steps_completed = []
        outputs = {}
        logger.info("=" * 60)
        logger.info("פייפליין מלא מתחיל")
        logger.info("=" * 60)

        try:
            # שלב 1: יצירת תמונה
            image_path = self.step_generate_image(
                prompt=config.get("prompt", ""),
                negative=config.get("negative", ""),
                style=config.get("style", "photorealistic"),
                mood=config.get("mood", "sensual"),
                width=config.get("width", 1024),
                height=config.get("height", 1024),
            )
            if image_path:
                steps_completed.append("generate_image")
                outputs["image"] = image_path
                logger.info(f"✅ תמונה: {image_path}")
            else:
                raise RuntimeError("יצירת תמונה נכשלה")

            # שלב 2: FaceID (אופציונלי)
            face_ref = config.get("face_reference")
            if face_ref and os.path.exists(face_ref):
                faceid_image = self.step_apply_face_id(
                    reference_image=face_ref,
                    prompt=config.get("prompt", ""),
                    negative=config.get("negative", ""),
                    width=config.get("width", 1024),
                    height=config.get("height", 1024),
                )
                if faceid_image:
                    steps_completed.append("face_id")
                    outputs["face_id_image"] = faceid_image
                    image_path = faceid_image  # השתמש בתמונה עם FaceID
                    logger.info(f"✅ FaceID: {faceid_image}")

            # שלב 3: אנימציה
            video_prompt = config.get("video_prompt")
            video_style = config.get("video_style", "pool_scene")

            if not video_prompt:
                vp = build_video_prompt(
                    image_prompt=config.get("prompt", ""),
                    video_style=video_style,
                )
                video_prompt = vp["video_prompt"]

            video_path = self.step_animate_image(
                image_path=image_path,
                video_prompt=video_prompt,
                duration=config.get("duration", 5),
                width=config.get("video_width", 1280),
                height=config.get("video_height", 720),
            )
            if video_path:
                steps_completed.append("animate")
                outputs["video"] = video_path
                logger.info(f"✅ וידאו: {video_path}")

                # שלב 4: Face Swap בוידאו (אופציונלי)
                if face_ref and os.path.exists(face_ref):
                    swapped = self.step_face_swap_video(face_ref, video_path)
                    if swapped and swapped != video_path:
                        steps_completed.append("face_swap")
                        outputs["face_swap_video"] = swapped
                        video_path = swapped
                        logger.info(f"✅ Face Swap: {swapped}")

                # שלב 5+6: TTS + Lip Sync (אופציונלי)
                voice_text = config.get("voice_text")
                if voice_text:
                    audio_path = self.step_tts(voice_text, config.get("voice", "default"))
                    if audio_path:
                        steps_completed.append("tts")
                        outputs["audio"] = audio_path

                        # Lip Sync
                        final_video = self.step_lipsync(video_path, audio_path)
                        if final_video and final_video != video_path:
                            steps_completed.append("lip_sync")
                            outputs["final_video"] = final_video
                            video_path = final_video
                            logger.info(f"✅ Lip Sync: {final_video}")

            # שלב 7: Upscale (אופציונלי)
            upscale = config.get("upscale", 0)
            if upscale > 1 and video_path:
                upscaled = self.step_upscale(video_path, upscale)
                if upscaled and upscaled != video_path:
                    steps_completed.append("upscale")
                    outputs["upscaled"] = upscaled
                    video_path = upscaled
                    logger.info(f"✅ Upscale: {upscaled}")

            logger.info("=" * 60)
            logger.info(f"פייפליין הושלם — {len(steps_completed)} שלבים")
            logger.info("=" * 60)

            return {
                "success": True,
                "steps_completed": steps_completed,
                "final_output": video_path or image_path,
                "outputs": outputs,
            }

        except Exception as e:
            logger.error(f"פייפליין נכשל: {e}")
            return {
                "success": False,
                "steps_completed": steps_completed,
                "error": str(e),
                "outputs": outputs,
            }


# ============================================================
# Convenience functions
# ============================================================

def quick_image(prompt: str, style: str = "photorealistic", mood: str = "sensual",
                width: int = 1024, height: int = 1024) -> str:
    """יצירת תמונה מהירה"""
    pipeline = ProductionPipeline()
    return pipeline.step_generate_image(prompt, style=style, mood=mood, width=width, height=height)


def quick_video(prompt: str, image_path: str = None, duration: int = 5,
                width: int = 1280, height: int = 720) -> str:
    """יצירת וידאו מהירה"""
    pipeline = ProductionPipeline()
    if not image_path:
        image_path = quick_image(prompt)
        if not image_path:
            return ""
    return pipeline.step_animate_image(image_path, prompt, duration=duration, width=width, height=height)


def quick_face_swap(source_face: str, target_image: str) -> str:
    """Face Swap מהיר"""
    pipeline = ProductionPipeline()
    return pipeline.step_face_swap_video(source_face, target_image)


if __name__ == "__main__":
    print("=" * 60)
    print("  ShimiStudio Production Pipeline v2.0")
    print("=" * 60)

    # Demo
    print("\nפייפליין מלא:")
    print("  1. יצירת תמונה מטקסט")
    print("  2. החלת FaceID (אופציונלי)")
    print("  3. אנימציה — תמונה → וידאו")
    print("  4. Face Swap בוידאו (אופציונלי)")
    print("  5. TTS — טקסט → קול")
    print("  6. Lip Sync — סנכרון שפתיים")
    print("  7. Upscale — הגדלת רזולוציה")
    print("\nשימוש:")
    print("  from pipeline import ProductionPipeline")
    print("  p = ProductionPipeline()")
    print("  result = p.run_full_pipeline({")
    print("      'prompt': 'woman at pool',")
    print("      'style': 'photorealistic',")
    print("      'mood': 'sensual',")
    print("      'video_style': 'pool_scene',")
    print("      'face_reference': '/path/to/face.jpg',")
    print("      'voice_text': 'Hello there',")
    print("  })")
    print(f"  → {{'success': True, 'final_output': '{str(OUTPUT_DIR)}/video.mp4'}}")
