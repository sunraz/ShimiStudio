"""
ShimiStudio v2.0 — ComfyUI Workflows Module
ComfyUI API workflow templates for AI video and image production.
"""

import json
import random
import inspect
from typing import Dict, Any, List, Optional

try:
    from config import DEFAULTS
except ImportError:
    DEFAULTS = {
        "negative_prompt": "low quality, blurry, deformed, ugly, bad anatomy, watermark, text",
        "steps": 25,
        "cfg_scale": 7.5,
        "sampler": "euler",
        "scheduler": "normal"
    }

DEFAULT_NEGATIVE = DEFAULTS.get("negative_prompt", "low quality, blurry, deformed, ugly, bad anatomy, watermark, text")


def _get_seed(seed: int) -> int:
    """Helper to convert seed to a valid positive integer if negative or invalid."""
    if seed is None or seed < 0:
        return random.randint(1, 10**14)
    return seed


def build_text_to_image(
    prompt: str,
    negative: str = DEFAULT_NEGATIVE,
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    cfg: float = 7.5,
    seed: int = -1,
    checkpoint: str = "flux1-dev-fp8.safetensors"
) -> Dict[str, Any]:
    """
    1. build_text_to_image
    Node 4: CheckpointLoaderSimple (ckpt_name=checkpoint)
    Node 6: CLIPTextEncode (text=prompt) — positive
    Node 7: CLIPTextEncode (text=negative) — negative
    Node 5: EmptyLatentImage (width, height, batch_size=1)
    Node 3: KSampler (seed, steps, cfg, sampler_name='euler', scheduler='normal', denoise=1.0)
    Node 8: VAEDecode
    Node 9: SaveImage (filename_prefix='ShimiStudio')
    """
    actual_seed = _get_seed(seed)
    return {
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": checkpoint
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["4", 1]
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["4", 1]
            }
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": actual_seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0]
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["3", 0],
                "vae": ["4", 2]
            }
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ShimiStudio",
                "images": ["8", 0]
            }
        }
    }


def build_image_to_video(
    image_path: str,
    video_prompt: str,
    duration: int = 5,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
    seed: int = -1
) -> Dict[str, Any]:
    """
    2. build_image_to_video
    Uses Wan 2.2 Image-to-Video
    LoadImage node for reference image
    VHS_VideoCombine for output
    Frames = duration * fps
    """
    actual_seed = _get_seed(seed)
    frames = int(duration * fps)

    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.1_i2v_720p_14B_bf16.safetensors",
                "weight_dtype": "fp8"
            }
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "umt5_xxl"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "wan_2.1_vae.safetensors"
            }
        },
        "4": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": video_prompt,
                "clip": ["2", 0]
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "low quality, blurry, static",
                "clip": ["2", 0]
            }
        },
        "7": {
            "class_type": "WanI2VLatentBuilder",
            "inputs": {
                "image": ["4", 0],
                "width": width,
                "height": height,
                "length": frames,
                "batch_size": 1
            }
        },
        "8": {
            "class_type": "KSampler",
            "inputs": {
                "seed": actual_seed,
                "steps": 25,
                "cfg": 3.5,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["5", 0],
                "negative": ["6", 0],
                "latent_image": ["7", 0]
            }
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["8", 0],
                "vae": ["3", 0]
            }
        },
        "10": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": fps,
                "loop_count": 0,
                "filename_prefix": "ShimiStudio_I2V",
                "format": "video/h264-mp4",
                "pix_fmt": "yuv420p",
                "crf": 19,
                "save_metadata": True,
                "pingpong": False,
                "save_output": True,
                "images": ["9", 0]
            }
        }
    }


def build_text_to_video(
    prompt: str,
    negative: str = DEFAULT_NEGATIVE,
    duration: int = 5,
    fps: int = 24,
    width: int = 1280,
    height: int = 720,
    seed: int = -1
) -> Dict[str, Any]:
    """
    3. build_text_to_video
    Uses Wan 2.2 Text-to-Video
    EmptyLatentVideo
    KSampler with video model
    Video output node
    """
    actual_seed = _get_seed(seed)
    frames = int(duration * fps)

    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "wan2.1_t2v_1.3B_bf16.safetensors",
                "weight_dtype": "fp8"
            }
        },
        "2": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
                "type": "umt5_xxl"
            }
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": "wan_2.1_vae.safetensors"
            }
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["2", 0]
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["2", 0]
            }
        },
        "6": {
            "class_type": "EmptyLatentVideo",
            "inputs": {
                "width": width,
                "height": height,
                "length": frames,
                "batch_size": 1
            }
        },
        "7": {
            "class_type": "KSampler",
            "inputs": {
                "seed": actual_seed,
                "steps": 25,
                "cfg": 6.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["6", 0]
            }
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["7", 0],
                "vae": ["3", 0]
            }
        },
        "9": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": fps,
                "loop_count": 0,
                "filename_prefix": "ShimiStudio_T2V",
                "format": "video/h264-mp4",
                "pix_fmt": "yuv420p",
                "crf": 19,
                "save_metadata": True,
                "pingpong": False,
                "save_output": True,
                "images": ["8", 0]
            }
        }
    }


def build_face_swap(
    source_image: str,
    target_image: str,
    face_id_weight: float = 1.0
) -> Dict[str, Any]:
    """
    4. build_face_swap
    Uses ReActor face swap
    LoadImage for source (face to take)
    LoadImage for target (body/scene)
    ReActorFaceSwap node
    SaveImage output
    """
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": source_image
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": target_image
            }
        },
        "3": {
            "class_type": "ReActorFaceSwap",
            "inputs": {
                "enabled": True,
                "swap_model": "inswapper_128.onnx",
                "facedetection": "retinaface_resnet50",
                "face_restore_model": "GFPGANv1.4.pth",
                "face_restore_visibility": float(face_id_weight),
                "see_coder_visibility": 1.0,
                "input_faces_order": "large-small",
                "source_faces_order": "large-small",
                "face_load_source": "input_image",
                "input_image": ["2", 0],
                "source_image": ["1", 0]
            }
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ShimiStudio_FaceSwap",
                "images": ["3", 0]
            }
        }
    }


def build_face_id(
    reference_image: str,
    prompt: str,
    negative: str = DEFAULT_NEGATIVE,
    width: int = 1024,
    height: int = 1024,
    weight: float = 1.0,
    steps: int = 25,
    cfg: float = 7.5,
    seed: int = -1
) -> Dict[str, Any]:
    """
    5. build_face_id
    Uses IP-Adapter FaceID + InsightFace
    LoadImage for reference face
    IPAdapterModelLoader
    InsightFaceLoader / IPAdapterInsightFaceLoader
    ApplyIPAdapterFaceID / IPAdapterApplyFaceID
    KSampler
    VAEDecode
    SaveImage
    """
    actual_seed = _get_seed(seed)
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            }
        },
        "2": {
            "class_type": "IPAdapterInsightFaceLoader",
            "inputs": {
                "provider": "CPU"
            }
        },
        "3": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {
                "ipadapter_file": "ip-adapter-faceid-plusv2_sdxl.bin"
            }
        },
        "4": {
            "class_type": "LoadImage",
            "inputs": {
                "image": reference_image
            }
        },
        "5": {
            "class_type": "IPAdapterApplyFaceID",
            "inputs": {
                "weight": weight,
                "weight_faceidv2": 1.0,
                "weight_type": "linear",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 1.0,
                "embeds_scaling": "V only",
                "model": ["1", 0],
                "ipadapter": ["3", 0],
                "image": ["4", 0],
                "insightface": ["2", 0]
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            }
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["1", 1]
            }
        },
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "seed": actual_seed,
                "steps": steps,
                "cfg": cfg,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["5", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["8", 0]
            }
        },
        "10": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["9", 0],
                "vae": ["1", 2]
            }
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ShimiStudio_FaceID",
                "images": ["10", 0]
            }
        }
    }


def build_tts_lipsync(
    video_path: str,
    audio_path: str,
    output_dir: str = ""
) -> Dict[str, Any]:
    """
    6. build_tts_lipsync
    Uses Wav2Lip or LatentSync
    LoadVideo
    LoadAudio
    LipSync node
    SaveVideo output
    """
    return {
        "1": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": video_path,
                "force_rate": 0,
                "force_size": "Disabled",
                "custom_width": 512,
                "custom_height": 512,
                "frame_load_cap": 0,
                "skip_first_frames": 0,
                "select_every_nth": 1
            }
        },
        "2": {
            "class_type": "LoadAudio",
            "inputs": {
                "audio": audio_path
            }
        },
        "3": {
            "class_type": "Wav2LipNode",
            "inputs": {
                "images": ["1", 0],
                "audio": ["2", 0],
                "face_restore": "GFPGAN"
            }
        },
        "4": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "frame_rate": 24,
                "loop_count": 0,
                "filename_prefix": "ShimiStudio_LipSync",
                "format": "video/h264-mp4",
                "pix_fmt": "yuv420p",
                "crf": 19,
                "save_metadata": True,
                "pingpong": False,
                "save_output": True,
                "images": ["3", 0],
                "audio": ["2", 0]
            }
        }
    }


def build_upscale(
    image_path: str,
    scale: int = 2,
    model: str = "4x-UltraSharp.pth"
) -> Dict[str, Any]:
    """
    7. build_upscale
    LoadImage
    UpscaleLoader / UpscaleModelLoader
    ImageUpscaleWithModel
    SaveImage
    """
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {
                "model_name": model
            }
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["2", 0],
                "image": ["1", 0]
            }
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ShimiStudio_Upscale",
                "images": ["3", 0]
            }
        }
    }


def build_controlnet_pose(
    image_path: str,
    prompt: str,
    negative: str = DEFAULT_NEGATIVE,
    width: int = 1024,
    height: int = 1024,
    steps: int = 25,
    seed: int = -1
) -> Dict[str, Any]:
    """
    8. build_controlnet_pose
    LoadImage
    DWPoseEstimator (ControlNet preprocessor)
    ControlNetLoader + ApplyControlNet
    KSampler
    SaveImage
    """
    actual_seed = _get_seed(seed)
    return {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            }
        },
        "2": {
            "class_type": "LoadImage",
            "inputs": {
                "image": image_path
            }
        },
        "3": {
            "class_type": "DWPoseEstimator",
            "inputs": {
                "image": ["2", 0],
                "detect_hand": "enable",
                "detect_body": "enable",
                "detect_face": "enable",
                "resolution": 512
            }
        },
        "4": {
            "class_type": "ControlNetLoader",
            "inputs": {
                "control_net_name": "controlnet-openpose-sdxl-1.0.safetensors"
            }
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": prompt,
                "clip": ["1", 1]
            }
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": negative,
                "clip": ["1", 1]
            }
        },
        "7": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["5", 0],
                "negative": ["6", 0],
                "control_net": ["4", 0],
                "image": ["3", 0],
                "strength": 1.0,
                "start_percent": 0.0,
                "end_percent": 1.0
            }
        },
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": width,
                "height": height,
                "batch_size": 1
            }
        },
        "9": {
            "class_type": "KSampler",
            "inputs": {
                "seed": actual_seed,
                "steps": steps,
                "cfg": 7.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["7", 0],
                "negative": ["7", 1],
                "latent_image": ["8", 0]
            }
        },
        "10": {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": ["9", 0],
                "vae": ["1", 2]
            }
        },
        "11": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": "ShimiStudio_ControlNet",
                "images": ["10", 0]
            }
        }
    }


# ============================================================
# Helpers
# ============================================================

def list_workflows() -> List[str]:
    """Returns list of available workflow types."""
    return [
        "text_to_image",
        "image_to_video",
        "text_to_video",
        "face_swap",
        "face_id",
        "tts_lipsync",
        "upscale",
        "controlnet_pose"
    ]


def get_workflow_for_job(job_type: str, **kwargs) -> Dict[str, Any]:
    """
    Dispatches to the corresponding workflow builder function for job_type.
    """
    mapping = {
        "text_to_image": build_text_to_image,
        "t2i": build_text_to_image,
        "image_to_video": build_image_to_video,
        "i2v": build_image_to_video,
        "text_to_video": build_text_to_video,
        "t2v": build_text_to_video,
        "face_swap": build_face_swap,
        "face_id": build_face_id,
        "tts_lipsync": build_tts_lipsync,
        "upscale": build_upscale,
        "controlnet_pose": build_controlnet_pose
    }

    if job_type not in mapping:
        raise ValueError(
            f"Unknown job_type '{job_type}'. Available workflows: {list_workflows()}"
        )

    builder = mapping[job_type]
    sig = inspect.signature(builder)
    valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
    return builder(**valid_kwargs)


if __name__ == "__main__":
    print("=" * 60)
    print("  ShimiStudio Workflows")
    print("=" * 60)
    print("Available Workflows:", list_workflows())
    print("\nSample Workflow (text_to_image):")
    sample = build_text_to_image("A futuristic city in the clouds", negative="blurry")
    print(json.dumps(sample, indent=2))
    print("=" * 60)
