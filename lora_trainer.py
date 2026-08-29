#!/usr/bin/env python3
"""
ShimiStudio — LoRA Trainer v1.0
================================
מאמן LoRA מתמונות של דמות — מייצר קובץ .safetensors שניתן לטעון ב-ComfyUI.

תהליך:
  1. מוריד תמונות מ-Base44
  2. מכין תיקיית אימון (resizes, captions)
  3. מאמן LoRA באמצעות diffusers + peft
  4. שומר קובץ .safetensors
  5. מעלה ל-Base44

תלויות:
  pip install diffusers transformers accelerate peft torch safetensors
  pip install pillow datasets

שימוש דרך Worker:
  job_type = "lora_training"
  parameters = {
    "image_urls": ["url1", "url2", ...],  # 5-20 תמונות
    "character_name": "לונה",
    "steps": 1500,
    "learning_rate": 1e-4,
    "resolution": 512
  }
"""

import os
import sys
import json
import time
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("LoRATrainer")


class LoRATrainer:
    """
    מאמן LoRA מתמונות — מייצר דמות עקבית לשימוש ב-ComfyUI.
    
    תהליך האימון:
    1. הורדת תמונות הדמות מ-Base44
    2. הכנת dataset (resize, caption)
    3. אימון LoRA עם diffusers + peft
    4. שמירת קובץ .safetensors
    5. העלאה ל-Base44
    """
    
    def __init__(
        self,
        output_dir: str = "./lora_output",
        base_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.base_model = base_model
        self.training_dir = self.output_dir / "training_data"
        self.lora_dir = self.output_dir / "loras"
        self.training_dir.mkdir(parents=True, exist_ok=True)
        self.lora_dir.mkdir(parents=True, exist_ok=True)
        
        self.character_name: str = "character"
        self.steps: int = 1500
        self.learning_rate: float = 1e-4
        self.resolution: int = 512
        self.batch_size: int = 1
        self.lora_rank: int = 32
        
        logger.info("✅ מאמן LoRA מוכן")
    
    def download_images(self, image_urls: List[str]) -> List[Path]:
        """הורדת תמונות מ-Base44 לתיקיית אימון"""
        logger.info(f"⬇️ מוריד {len(image_urls)} תמונות...")
        local_paths = []
        
        for i, url in enumerate(image_urls):
            try:
                ext = ".png" if ".png" in url else ".jpg"
                filepath = self.training_dir / f"image_{i:03d}{ext}"
                
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                local_paths.append(filepath)
                logger.info(f"  ✅ תמונה {i+1}/{len(image_urls)}: {filepath.name} ({len(response.content)/1024:.1f}KB)")
                
            except Exception as e:
                logger.error(f"  ❌ שגיאה בהורדת תמונה {i+1}: {e}")
        
        logger.info(f"✅ הורדו {len(local_paths)} תמונות")
        return local_paths
    
    def prepare_dataset(self, image_paths: List[Path], character_name: str):
        """
        הכנת dataset לאימון:
        - Resize לרזולוציית אימון
        - יצירת קפציות caption לכל תמונה
        - יצירת קובץ metadata.json
        """
        from PIL import Image
        
        logger.info(f"📦 מכין dataset עבור '{character_name}'...")
        
        captions = []
        for img_path in image_paths:
            try:
                # Resize
                img = Image.open(img_path).convert("RGB")
                img = img.resize((self.resolution, self.resolution), Image.LANCZOS)
                img.save(img_path)
                
                # Caption — כל תמונה מקבלת caption עם שם הדמות
                caption = f"a photo of {character_name}, {character_name} character, detailed face, high quality"
                caption_path = img_path.with_suffix(".txt")
                with open(caption_path, 'w', encoding='utf-8') as f:
                    f.write(caption)
                captions.append(caption)
                
            except Exception as e:
                logger.error(f"  ❌ שגיאה בהכנת {img_path.name}: {e}")
        
        # קובץ metadata
        metadata = {
            "character_name": character_name,
            "num_images": len(image_paths),
            "resolution": self.resolution,
            "captions": captions,
        }
        metadata_path = self.training_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Dataset מוכן: {len(image_paths)} תמונות ברזולוציית {self.resolution}px")
    
    def train_lora(
        self,
        image_urls: List[str],
        character_name: str = "character",
        steps: int = 1500,
        learning_rate: float = 1e-4,
        resolution: int = 512,
        lora_rank: int = 32,
    ) -> Dict[str, Any]:
        """
        הפעלת אימון LoRA מלא.
        
        Args:
            image_urls: רשימת URLs של תמונות הדמות (5-20 תמונות)
            character_name: שם הדמות (משמש ב-captions)
            steps: מספר צעדי אימון (1500 = ברירת מחדל, 800 = מהיר)
            learning_rate: קצב למידה
            resolution: רזולוציית אימון
            lora_rank: דרגת LoRA (32 = ברירת מחדל, 16 = מהיר/קל)
        
        Returns:
            dict עם: success, lora_path, lora_url, training_time, steps
        """
        self.character_name = character_name
        self.steps = steps
        self.learning_rate = learning_rate
        self.resolution = resolution
        self.lora_rank = lora_rank
        
        start_time = time.time()
        
        # 1. הורדת תמונות
        image_paths = self.download_images(image_urls)
        if len(image_paths) < 3:
            return {"success": False, "error": f"נדרשות לפחות 3 תמונות, התקבלו {len(image_paths)}"}
        
        # 2. הכנת dataset
        self.prepare_dataset(image_paths, character_name)
        
        # 3. אימון LoRA
        lora_path = self._run_training()
        if not lora_path:
            return {"success": False, "error": "אימון נכשל"}
        
        training_time = time.time() - start_time
        
        # 4. העלאה ל-Base44
        lora_url = self._upload_lora(lora_path)
        
        logger.info(f"🎉 אימון הושלם! זמן: {training_time/60:.1f} דקות")
        logger.info(f"📦 קובץ LoRA: {lora_path}")
        if lora_url:
            logger.info(f"☁️ הועלה ל: {lora_url}")
        
        return {
            "success": True,
            "lora_path": str(lora_path),
            "lora_url": lora_url,
            "training_time_seconds": round(training_time),
            "training_time_minutes": round(training_time / 60, 1),
            "steps": steps,
            "num_images": len(image_paths),
            "character_name": character_name,
            "lora_rank": lora_rank,
            "resolution": resolution,
        }
    
    def _run_training(self) -> Optional[Path]:
        """
        הרצת סקריפט אימון LoRA.
        משתמש ב-diffusers + peft או ב-kohya_ss.
        """
        
        # נסה קודם kohya_ss (אם מותקן)
        kohya_script = Path(__file__).parent / "train_lora_kohya.py"
        if kohya_script.exists():
            return self._train_with_kohya(kohya_script)
        
        # אחרת — diffusers + peft
        return self._train_with_diffusers()
    
    def _train_with_diffusers(self) -> Optional[Path]:
        """אימון LoRA באמצעות diffusers + peft"""
        try:
            import torch
            from diffusers import StableDiffusionXLPipeline, DDPMScheduler
            from peft import LoraConfig, get_peft_model
            from transformers import AutoTokenizer, CLIPTextModel
            from PIL import Image
            from torch.utils.data import Dataset, DataLoader
            import safetensors.torch
            
            logger.info("🏋️ מתחיל אימון LoRA (diffusers + peft)...")
            logger.info(f"  מודל בסיס: {self.base_model}")
            logger.info(f"  תמונות: {len(list(self.training_dir.glob('*.jpg')))} + {len(list(self.training_dir.glob('*.png')))}")
            logger.info(f"  צעדים: {self.steps}")
            logger.info(f"  דרגה: {self.lora_rank}")
            logger.info(f"  רזולוציה: {self.resolution}")
            
            # טעינת מודל בסיס
            logger.info("⏳ טוען מודל בסיס...")
            pipeline = StableDiffusionXLPipeline.from_pretrained(
                self.base_model,
                torch_dtype=torch.float16,
                variant="fp16",
            ).to("cuda")
            
            # הכנת LoRA
            lora_config = LoraConfig(
                r=self.lora_rank,
                lora_alpha=self.lora_rank * 2,
                target_modules=["to_q", "to_k", "to_v", "to_out.0"],
                lora_dropout=0.05,
            )
            
            # החלת LoRA על UNet
            unet = pipeline.unet
            unet_lora = get_peft_model(unet, lora_config)
            unet_lora.train()
            
            # Dataset פשוט
            class CharacterDataset(Dataset):
                def __init__(self, training_dir, resolution, character_name, tokenizer_1, tokenizer_2):
                    self.images = list(training_dir.glob("*.jpg")) + list(training_dir.glob("*.png"))
                    self.resolution = resolution
                    self.character_name = character_name
                    self.tokenizer_1 = tokenizer_1
                    self.tokenizer_2 = tokenizer_2
                    self.transform = __import__('torchvision.transforms', fromlist=['transforms']).transforms.Compose([
                        __import__('torchvision.transforms', fromlist=['transforms']).transforms.Resize((resolution, resolution)),
                        __import__('torchvision.transforms', fromlist=['transforms']).transforms.ToTensor(),
                        __import__('torchvision.transforms', fromlist=['transforms']).transforms.Normalize([0.5], [0.5]),
                    ])
                
                def __len__(self):
                    return len(self.images)
                
                def __getitem__(self, idx):
                    img = Image.open(self.images[idx]).convert("RGB")
                    img = self.transform(img)
                    caption = f"a photo of {self.character_name}, detailed face, high quality"
                    tokens_1 = self.tokenizer_1(caption, padding="max_length", max_length=77, truncation=True, return_tensors="pt")
                    tokens_2 = self.tokenizer_2(caption, padding="max_length", max_length=77, truncation=True, return_tensors="pt")
                    return {
                        "pixel_values": img,
                        "input_ids_1": tokens_1.input_ids.squeeze(),
                        "input_ids_2": tokens_2.input_ids.squeeze(),
                    }
            
            # Tokenizers
            tokenizer_1 = pipeline.tokenizer
            tokenizer_2 = pipeline.tokenizer_2
            
            dataset = CharacterDataset(self.training_dir, self.resolution, self.character_name, tokenizer_1, tokenizer_2)
            dataloader = DataLoader(dataset, batch_size=self.batch_size, shuffle=True)
            
            # Optimizer
            optimizer = torch.optim.AdamW(unet_lora.parameters(), lr=self.learning_rate)
            scheduler = DDPMScheduler.from_pretrained(self.base_model, subfolder="scheduler")
            
            # אימון
            step = 0
            vae = pipeline.vae
            text_encoder_1 = pipeline.text_encoder
            text_encoder_2 = pipeline.text_encoder_2
            
            logger.info("🏃 מתחיל אימון...")
            
            while step < self.steps:
                for batch in dataloader:
                    if step >= self.steps:
                        break
                    
                    pixel_values = batch["pixel_values"].to("cuda", dtype=torch.float16)
                    
                    # Encode images through VAE
                    with torch.no_grad():
                        latents = vae.encode(pixel_values).latent_dist.sample()
                        latents = latents * vae.config.scaling_factor
                    
                    # Noise
                    noise = torch.randn_like(latents)
                    timesteps = torch.randint(0, scheduler.config.num_train_timesteps, (latents.shape[0],), device="cuda").long()
                    noisy_latents = scheduler.add_noise(latents, noise, timesteps)
                    
                    # Text embeddings
                    with torch.no_grad():
                        enc_1 = text_encoder_1(batch["input_ids_1"].to("cuda"))[0]
                        enc_2 = text_encoder_2(batch["input_ids_2"].to("cuda"))[0]
                        encoder_hidden_states = torch.cat([enc_1, enc_2], dim=-1)
                    
                    # Predict noise
                    noise_pred = unet_lora(noisy_latents, timesteps, encoder_hidden_states=encoder_hidden_states).sample
                    
                    # Loss
                    loss = torch.nn.functional.mse_loss(noise_pred, noise)
                    
                    # Backward
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    
                    step += 1
                    
                    if step % 100 == 0:
                        logger.info(f"  צעד {step}/{self.steps} | loss: {loss.item():.4f}")
                    
                    if step >= self.steps:
                        break
            
            # שמירת LoRA
            lora_filename = f"{self.character_name.lower().replace(' ', '_')}_lora.safetensors"
            lora_path = self.lora_dir / lora_filename
            
            # חילוץ משקלי LoRA בלבד
            lora_state_dict = {}
            for name, param in unet_lora.named_parameters():
                if "lora_" in name:
                    lora_state_dict[name] = param.data.cpu().clone()
            
            safetensors.torch.save_file(lora_state_dict, str(lora_path))
            
            logger.info(f"✅ LoRA נשמר: {lora_path} ({lora_path.stat().st_size/1024/1024:.1f}MB)")
            
            # ניקוי
            del pipeline, unet_lora
            torch.cuda.empty_cache()
            
            return lora_path
            
        except ImportError as e:
            logger.error(f"❌ חסרות תלויות: {e}")
            logger.error("התקן: pip install diffusers transformers accelerate peft safetensors torchvision")
            return None
        except Exception as e:
            logger.error(f"❌ שגיאת אימון: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _train_with_kohya(self, script_path: Path) -> Optional[Path]:
        """אימון באמצעות kohya_ss (אם מותקן)"""
        lora_filename = f"{self.character_name.lower().replace(' ', '_')}_lora.safetensors"
        lora_path = self.lora_dir / lora_filename
        
        cmd = [
            "python", str(script_path),
            "--train_data_dir", str(self.training_dir),
            "--output_dir", str(self.lora_dir),
            "--output_name", lora_filename.replace(".safetensors", ""),
            "--resolution", str(self.resolution),
            "--max_train_steps", str(self.steps),
            "--learning_rate", str(self.learning_rate),
            "--network_dim", str(self.lora_rank),
            "--network_alpha", str(self.lora_rank * 2),
        ]
        
        logger.info(f"🏋️ מריץ kohya_ss: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if lora_path.exists():
            logger.info(f"✅ LoRA נשמר: {lora_path}")
            return lora_path
        else:
            logger.error(f"❌ kohya_ss נכשל: {result.stderr[-500:]}")
            return None
    
    def _upload_lora(self, lora_path: Path) -> Optional[str]:
        """העלאת קובץ LoRA ל-0x0.st או catbox.moe"""
        try:
            logger.info(f"☁️ מעלה LoRA: {lora_path.name}...")
            
            # נסה 0x0.st
            with open(lora_path, 'rb') as f:
                response = requests.post(
                    "https://0x0.st",
                    files={"file": (lora_path.name, f)},
                    timeout=300
                )
            
            if response.status_code == 200 and response.text.strip().startswith("http"):
                url = response.text.strip()
                logger.info(f"✅ הועלה: {url}")
                return url
            
            # Fallback: catbox.moe
            logger.info("⚠️ 0x0.st נכשל, מנסה catbox.moe...")
            with open(lora_path, 'rb') as f:
                response = requests.post(
                    "https://catbox.moe/user/api.php",
                    data={"reqtype": "fileupload", "json": "1"},
                    files={"fileToUpload": (lora_path.name, f)},
                    timeout=300
                )
            
            if response.status_code == 200:
                result = response.json()
                if "url" in result:
                    logger.info(f"✅ הועלה: {result['url']}")
                    return result["url"]
            
            logger.error("❌ העלאה נכשלה")
            return None
            
        except Exception as e:
            logger.error(f"❌ שגיאת העלאה: {e}")
            return None


# ═══════════════════════════════════════════════════════════════
# פונקציית עזר ל-Worker
# ═══════════════════════════════════════════════════════════════

def process_lora_training_job(job_data: dict) -> dict:
    """
    עיבוד עבודת lora_training מה-Worker.
    
    Args:
        job_data: נתוני RenderJob
            - face_images: רשימת URLs של תמונות (5-20)
            - prompt: שם הדמות (משמש ב-captions)
            - parameters: steps, learning_rate, resolution, lora_rank
    
    Returns:
        dict עם: success, lora_url, training_time
    """
    image_urls = job_data.get("face_images", [])
    if isinstance(image_urls, str):
        try:
            image_urls = json.loads(image_urls)
        except:
            image_urls = [image_urls]
    
    character_name = job_data.get("prompt", "character") or "character"
    params = job_data.get("parameters", {})
    
    if len(image_urls) < 3:
        return {
            "success": False,
            "error": f"נדרשות לפחות 3 תמונות, התקבלו {len(image_urls)}"
        }
    
    trainer = LoRATrainer()
    result = trainer.train_lora(
        image_urls=image_urls,
        character_name=character_name,
        steps=params.get("steps", 1500),
        learning_rate=params.get("learning_rate", 1e-4),
        resolution=params.get("resolution", 512),
        lora_rank=params.get("lora_rank", 32),
    )
    
    return result


def generate_with_lora(
    prompt: str,
    lora_url: str,
    lora_strength: float = 0.8,
    width: int = 512,
    height: int = 512,
    steps: int = 25,
    cfg: float = 7.0,
    comfyui_url: str = "http://127.0.0.1:8188",
) -> dict:
    """
    יצירת תמונה עם LoRA מאומן.
    
    Args:
        prompt: פרומפט היצירה
        lora_url: URL של קובץ ה-LoRA
        lora_strength: עוצמת ה-LoRA (0.0-1.0)
    
    Returns:
        dict עם: success, output_b64
    """
    from comfyui_client import ComfyUIClient
    
    client = ComfyUIClient(comfyui_url)
    
    # הורדת LoRA
    import tempfile
    lora_path = Path(tempfile.gettempdir()) / f"lora_{int(time.time())}.safetensors"
    response = requests.get(lora_url, timeout=60)
    with open(lora_path, 'wb') as f:
        f.write(response.content)
    
    # העלאה ל-ComfyUI
    client.upload_image(str(lora_path))
    lora_name = lora_path.name
    
    # Workflow עם LoRA
    workflow = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "flux1-dev-fp8.safetensors"}
        },
        "2": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": lora_name,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["1", 0],
                "clip": ["1", 1]
            }
        },
        "3": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["2", 1]
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "deformed, blurry, bad quality, distorted",
                "clip": ["2", 1]
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(time.time()) % (2**32),
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["2", 0],
                "positive": ["3", 0],
                "negative": ["4", 0],
                "latent_image": ["5", 0]
            }
        },
        "7": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
        },
        "8": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "LoRAGen_Shimi", "images": ["7", 0]}
        }
    }
    
    prompt_id = client.queue_prompt(workflow)
    output = client.wait_for_result(prompt_id, timeout=120)
    output_b64 = client.get_output_image_b64(prompt_id) if output else None
    
    # ניקוי
    lora_path.unlink(missing_ok=True)
    
    return {
        "success": output_b64 is not None,
        "output_b64": output_b64,
        "lora_strength": lora_strength,
    }


if __name__ == "__main__":
    print("╔══════════════════════════════════════════╗")
    print("║  ShimiStudio — LoRA Trainer v1.0         ║")
    print("╚══════════════════════════════════════════╝")
    print()
    print("מאמן LoRA מתמונות של דמות:")
    print("  1. העלה 5-20 תמונות של הדמות")
    print("  2. המערכת מאמנת LoRA (15-45 דקות)")
    print("  3. קובץ .safetensors נשמר ומועלה")
    print("  4. ה-LoRA זמין ליצירה ב-ComfyUI")
    print()
    print("דרך Worker:")
    print("  job_type = 'lora_training'")
    print("  face_images = ['url1', 'url2', ...]")
    print("  prompt = 'שם הדמות'")
    print()
    print("יצירה עם LoRA:")
    print("  generate_with_lora(prompt, lora_url, lora_strength=0.8)")
