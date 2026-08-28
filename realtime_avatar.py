#!/usr/bin/env python3
"""
ShimiStudio — Realtime Avatar Engine v1.0
==========================================
מקבל פריימים חיים ממצלמת הטלפון, מחליף פנים ותנועה בזמן אמת.

צינור עיבוד:
  פריים חי → DWPose (תנועה) → ControlNet → IP-Adapter (פנים) → ReActor (החלפה) → תוצאה

שימוש:
  1. כחלק מה-Worker (מקבל עבודות מסוג "realtime_avatar")
  2. כשרת עצמאי (לזמן אמת מלא)

תלויות:
  - ComfyUI פעיל על localhost:8188
  - מודלים: Flux.1, inswapper_128.onnx, ip-adapter-faceid-plusv2_sdxl.bin
  - Custom Nodes: DWPose, IPAdapter, ReActor, ControlNet
"""

import os
import sys
import time
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import COMFYUI_URL, OUTPUT_DIR
from comfyui_client import ComfyUIClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("RealtimeAvatar")


class RealtimeAvatarEngine:
    """
    מנוע אווטאר חי — מעבד פריימים בזמן אמת.
    
    צינור:
    1. קבלת פריים ממצלמה (base64/JPEG)
    2. טעינת פני דמות נבחרת
    3. טעינת תמונת מטרה (אופציונלי)
    4. DWPose → זיהוי תנועת גוף מהפריים
    5. ControlNet → הפעלת תנועה על מודל
    6. IP-Adapter FaceID → הזרקת זהות פנים
    7. KSampler → יצירת תמונה
    8. ReActor → החלפת פנים סופית
    9. החזרת תוצאה
    """
    
    def __init__(self, comfyui_url: str = COMFYUI_URL):
        self.client = ComfyUIClient(comfyui_url)
        self.workflow_path = Path(__file__).parent / "workflows" / "realtime_avatar.json"
        self.workflow = None
        self.face_image_b64: Optional[str] = None
        self.target_image_b64: Optional[str] = None
        self.prompt: str = "photorealistic woman, beautiful, detailed"
        self.negative_prompt: str = "deformed, blurry, bad quality, distorted"
        self.width: int = 512
        self.height: int = 512
        self.steps: int = 15  # נמוך = מהיר יותר לזמן אמת
        self.cfg: float = 7.0
        self.seed: int = -1
        
        # סטטיסטיקה
        self.frames_processed = 0
        self.avg_latency_ms = 0
        self.last_latency_ms = 0
        
        self._load_workflow()
        logger.info("✅ מנוע אווטאר חי מוכן")
    
    def _load_workflow(self):
        """טוען את ה-workflow מקובץ JSON"""
        with open(self.workflow_path, 'r', encoding='utf-8') as f:
            self.workflow = json.load(f)
        logger.info(f"✅ Workflow נטען: {self.workflow_path.name}")
    
    def set_character(self, face_image_path: str, target_image_path: str = None):
        """
        הגדרת הדמות — הפנים שיוחלפו, ואופציונלי תמונת מטרה.
        
        Args:
            face_image_path: נתיב לתמונת הפנים של הדמות הנבחרת
            target_image_path: נתיד לתמונת מטרה (רקע/תלבושת)
        """
        with open(face_image_path, 'rb') as f:
            self.face_image_b64 = base64.b64encode(f.read()).decode()
        
        if target_image_path and os.path.exists(target_image_path):
            with open(target_image_path, 'rb') as f:
                self.target_image_b64 = base64.b64encode(f.read()).decode()
        
        logger.info(f"✅ דמות הוגדרה: {face_image_path}")
    
    def set_character_from_b64(self, face_b64: str, target_b64: str = None):
        """הגדרת דמות מ-base64"""
        self.face_image_b64 = face_b64
        self.target_image_b64 = target_b64
        logger.info("✅ דמות הוגדרה מ-base64")
    
    def set_outfit(self, prompt: str):
        """הגדרת תלבושת/סגנון דרך פרומפט"""
        self.prompt = prompt
        logger.info(f"✅ תלבושת/פרומפט: {prompt[:80]}")
    
    def set_quality(self, width: int = 512, height: int = 512, steps: int = 15):
        """
        הגדרת איכות — פשרה בין מהירות לאיכות.
        
        זמן אמת (מהיר): 512x512, 10-15 steps → ~50-100ms לפריים
        איכות גבוהה: 768x768, 25-30 steps → ~200-400ms לפריים
        """
        self.width = width
        self.height = height
        self.steps = steps
        logger.info(f"✅ איכות: {width}x{height}, {steps} steps")
    
    def process_frame(self, frame_b64: str) -> Dict[str, Any]:
        """
        עיבוד פריים יחיד — הליבה של המנוע.
        
        Args:
            frame_b64: פריים מהמצלמה ב-base64 JPEG
            
        Returns:
            dict עם: success, output_b64, latency_ms, frame_number
        """
        if not self.face_image_b64:
            return {"success": False, "error": "דמות לא הוגדרה"}
        
        start_time = time.time()
        
        try:
            # בניית ה-workflow עם הפרמטרים הנוכחיים
            wf = self._build_workflow(frame_b64)
            
            # שליחה ל-ComfyUI
            client_id = f"realtime_avatar_{int(time.time())}"
            prompt_id = self.client.queue_prompt(wf, client_id)
            
            # המתנה לתוצאה
            output = self.client.wait_for_result(prompt_id, timeout=30)
            
            if not output:
                return {"success": False, "error": "לא התקבלה תוצאה מ-ComfyUI"}
            
            # קריאת התמונה
            output_b64 = self.client.get_output_image_b64(prompt_id)
            
            latency = (time.time() - start_time) * 1000
            self.frames_processed += 1
            self.last_latency_ms = latency
            self.avg_latency_ms = (
                (self.avg_latency_ms * (self.frames_processed - 1) + latency) 
                / self.frames_processed
            )
            
            return {
                "success": True,
                "output_b64": output_b64,
                "latency_ms": round(latency),
                "frame_number": self.frames_processed,
                "avg_latency_ms": round(self.avg_latency_ms),
                "fps": round(1000 / latency, 1) if latency > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ שגיאה בעיבוד פריים: {e}")
            return {"success": False, "error": str(e)}
    
    def _build_workflow(self, frame_b64: str) -> dict:
        """בניית workflow עם הפרמטרים הנוכחיים"""
        import copy
        wf = copy.deepcopy(self.workflow)
        
        # החלפת placeholders
        replacements = {
            "__SOURCE_FRAME__": frame_b64,
            "__FACE_IMAGE__": self.face_image_b64,
            "__TARGET_IMAGE__": self.target_image_b64 or frame_b64,
            "__PROMPT__": self.prompt,
            "__NEGATIVE_PROMPT__": self.negative_prompt,
            "__WIDTH__": self.width,
            "__HEIGHT__": self.height,
            "__STEPS__": self.steps,
            "__CFG__": self.cfg,
            "__SEED__": self.seed if self.seed >= 0 else int(time.time()) % (2**32),
        }
        
        def replace_values(obj):
            if isinstance(obj, dict):
                return {k: replace_values(v) for k, v in obj.items()}
            elif isinstance(obj, str):
                for placeholder, value in replacements.items():
                    if obj == placeholder:
                        return value
                return obj
            else:
                return obj
        
        return replace_values(wf)
    
    def get_stats(self) -> Dict[str, Any]:
        """סטטיסטיקת ביצועים"""
        return {
            "frames_processed": self.frames_processed,
            "avg_latency_ms": round(self.avg_latency_ms),
            "last_latency_ms": round(self.last_latency_ms),
            "avg_fps": round(1000 / self.avg_latency_ms, 1) if self.avg_latency_ms > 0 else 0,
            "comfyui_url": COMFYUI_URL,
            "quality": f"{self.width}x{self.height} @ {self.steps} steps",
            "character_set": self.face_image_b64 is not None,
        }
    
    # ═══════════════════════════════════════════════════════════════
    # מצב אווטאר מהיר — Face Swap בלבד (בלי ControlNet)
    # יותר מהיר: ~30-50ms לפריים = 20-30 FPS
    # ═══════════════════════════════════════════════════════════════
    
    def process_frame_fast(self, frame_b64: str) -> Dict[str, Any]:
        """
        מצב מהיר — Face Swap בלבד.
        מתאים ל-GPU חלש יותר או כשרוצים FPS גבוה.
        """
        if not self.face_image_b64:
            return {"success": False, "error": "דמות לא הוגדרה"}
        
        start_time = time.time()
        
        try:
            # Workflow פשוט: ReActor בלבד
            fast_wf = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {"image": frame_b64}
                },
                "2": {
                    "class_type": "LoadImage",
                    "inputs": {"image": self.face_image_b64}
                },
                "3": {
                    "class_type": "ReActorFaceSwap",
                    "inputs": {
                        "enabled": True,
                        "swap_model": "inswapper_128.onnx",
                        "facedetection": "retinaface_resnet50",
                        "face_restore_model": "GFPGANv1.4.pth",
                        "face_restore_visibility": 1.0,
                        "see_coder_visibility": 1.0,
                        "input_faces_order": "large-small",
                        "source_faces_order": "large-small",
                        "face_load_source": "input_image",
                        "input_image": ["1", 0],
                        "source_image": ["2", 0]
                    }
                },
                "4": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "RealtimeAvatar_Fast",
                        "images": ["3", 0]
                    }
                }
            }
            
            client_id = f"realtime_fast_{int(time.time())}"
            prompt_id = self.client.queue_prompt(fast_wf, client_id)
            output = self.client.wait_for_result(prompt_id, timeout=15)
            output_b64 = self.client.get_output_image_b64(prompt_id) if output else None
            
            latency = (time.time() - start_time) * 1000
            self.frames_processed += 1
            self.last_latency_ms = latency
            self.avg_latency_ms = (
                (self.avg_latency_ms * (self.frames_processed - 1) + latency)
                / self.frames_processed
            )
            
            return {
                "success": True,
                "output_b64": output_b64,
                "latency_ms": round(latency),
                "frame_number": self.frames_processed,
                "mode": "fast"
            }
        except Exception as e:
            logger.error(f"❌ שגיאה במצב מהיר: {e}")
            return {"success": False, "error": str(e)}
    
    def stop(self):
        """עצירת המנוע"""
        logger.info("⏹️ מנוע אווטאר חי נעצר")
        logger.info(f"סה\"כ פריימים: {self.frames_processed} | "
                    f"latency ממוצע: {self.avg_latency_ms:.0f}ms")


# ═══════════════════════════════════════════════════════════════
# פונקציית עזר ל-Worker — עיבוד עבודת realtime_avatar
# ═══════════════════════════════════════════════════════════════

def process_realtime_avatar_job(job_data: dict, comfyui_url: str = COMFYUI_URL) -> dict:
    """
    עיבוד עבודת realtime_avatar מה-Worker.
    
    Args:
        job_data: נתוני העבודה מ-RenderJob
            - face_images: base64 של תמונת הפנים
            - camera_frames: base64 של הפריים החי
            - face_swap_target: base64 של תמונת מטרה (אופציונלי)
            - prompt: תיאור התלבושת/סגנון
            - parameters: width, height, steps, mode (fast/full)
        comfyui_url: כתובת ComfyUI
    
    Returns:
        dict עם output_b64 וסטטוס
    """
    engine = RealtimeAvatarEngine(comfyui_url)
    
    # הגדרת דמות
    face_b64 = job_data.get("face_images", "")
    target_b64 = job_data.get("face_swap_target", "")
    engine.set_character_from_b64(face_b64, target_b64 if target_b64 else None)
    
    # הגדרת תלבושת
    prompt = job_data.get("prompt", "photorealistic, detailed")
    engine.set_outfit(prompt)
    
    # הגדרת איכות
    params = job_data.get("parameters", {})
    mode = params.get("mode", "fast")  # fast = Face Swap only, full = + ControlNet
    
    if mode == "fast":
        engine.set_quality(
            width=params.get("width", 512),
            height=params.get("height", 512),
            steps=params.get("steps", 10)
        )
    else:
        engine.set_quality(
            width=params.get("width", 512),
            height=params.get("height", 512),
            steps=params.get("steps", 20)
        )
    
    # עיבוד פריים
    frame_b64 = job_data.get("camera_frames", "")
    if not frame_b64:
        return {"success": False, "error": "לא התקבל פריים מהמצלמה"}
    
    if mode == "fast":
        result = engine.process_frame_fast(frame_b64)
    else:
        result = engine.process_frame(frame_b64)
    
    engine.stop()
    return result


if __name__ == "__main__":
    # בדיקה
    print("╔══════════════════════════════════════════╗")
    print("║  ShimiStudio — Realtime Avatar Engine    ║")
    print("╚══════════════════════════════════════════╝")
    print()
    print("מצבי עבודה:")
    print("  fast = Face Swap בלבד (~30-50ms/פריים)")
    print("  full = Face Swap + ControlNet + IP-Adapter (~100-200ms/פריים)")
    print()
    print("שימוש:")
    print("  1. הגדר דמות: engine.set_character('face.jpg')")
    print("  2. הגדר תלבושת: engine.set_outfit('bikini on beach')")
    print("  3. עבד פריים: result = engine.process_frame_fast(frame_b64)")
    print()
    print("לשילוב ב-Worker: process_realtime_avatar_job(job_data)")
