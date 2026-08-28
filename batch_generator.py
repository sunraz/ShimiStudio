"""
ShimiStudio Batch Generator v2.0
Batch generation system for images, videos, composite scenes, and prompt packs.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure local imports resolve
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from style_library import (
    STYLES,
    MOODS,
    VIDEO_STYLES,
    CHARACTERS,
    ASPECT_RATIOS,
    build_image_prompt,
    build_video_prompt,
    build_scene_composition,
    list_styles,
    list_moods,
    list_video_styles,
    list_characters,
)

# ============================================================
# PROMPT PACKS (6 Curated Packs)
# ============================================================

PROMPT_PACKS: Dict[str, Dict[str, Any]] = {
    "portrait_basics": {
        "name": "Portrait Basics",
        "category": "styles",
        "prompts": [
            "Close-up portrait, natural lighting, soft smile",
            "Profile shot, golden hour, wind in hair",
            "Looking over shoulder, soft focus background",
            "Looking directly at camera, confident expression",
            "Candid laugh mid-conversation, natural moment",
        ],
    },
    "fashion_editorial": {
        "name": "Fashion Editorial",
        "category": "styles",
        "prompts": [
            "High fashion editorial, dramatic pose, studio lighting",
            "Vogue style cover, elegant gown, minimal background",
            "Street fashion, urban environment, candid walk",
            "Avant-garde fashion, unusual silhouette, artistic",
            "Lingerie editorial, sensual pose, soft lighting",
        ],
    },
    "lifestyle_candid": {
        "name": "Lifestyle Candid",
        "category": "styles",
        "prompts": [
            "Morning coffee in bed, messy hair, natural light",
            "Cooking in kitchen, apron, candid moment",
            "Reading book on couch, cozy, warm tones",
            "Stretching after workout, gym, sweat glistening",
            "Walking dog in park, casual outfit, sunny day",
        ],
    },
    "xxx_amateur": {
        "name": "XXX Amateur",
        "category": "xxx",
        "prompts": [
            "Amateur phone photo, bedroom, natural lighting, unedited",
            "Mirror selfie in bathroom, casual, raw",
            "Bed photo, morning, messy sheets, natural",
            "Shower photo, steam, wet hair, intimate",
            "Changing room, mid-dress, candid, amateur",
        ],
    },
    "video_candid": {
        "name": "Video Candid",
        "category": "video",
        "prompts": [
            "Walking down street, handheld, candid, 5s",
            "Sitting at cafe, natural conversation, 5s",
            "Dancing in living room, candid phone footage, 10s",
            "Swimming pool, underwater shot, 5s",
            "Sunset beach walk, telephoto, 10s",
        ],
    },
    "xxx_video_amateur": {
        "name": "XXX Video Amateur",
        "category": "xxx_video",
        "prompts": [
            "Amateur bedroom footage, fixed camera, 5s",
            "Shower video, steam, intimate, 5s",
            "Dancing undressing, TikTok style, 10s",
            "Pool undressing, candid, 5s",
            "Gym flirt, mirror selfie video, 10s",
        ],
    },
}


def get_prompt_pack(pack_name: str) -> List[str]:
    """Retrieves list of 5 prompt strings for given pack_name."""
    pack = PROMPT_PACKS.get(pack_name)
    if not pack:
        raise KeyError(f"Prompt pack '{pack_name}' not found. Available: {list(PROMPT_PACKS.keys())}")
    return pack["prompts"]


def list_prompt_packs(category: Optional[str] = None) -> List[dict]:
    """Lists available prompt packs, optionally filtered by category."""
    results = []
    for key, pack in PROMPT_PACKS.items():
        if category and pack.get("category") != category:
            continue
        results.append({
            "id": key,
            "name": pack["name"],
            "category": pack["category"],
            "count": len(pack["prompts"]),
        })
    return results


# ============================================================
# BATCH GENERATION FUNCTIONS
# ============================================================

def batch_generate_images(
    base_prompt: str,
    styles: Optional[List[str]] = None,
    moods: Optional[List[str]] = None,
    faceid_id: Optional[str] = None,
    faceid_weight: float = 1.0,
    aspect_ratio: str = "1:1",
    character: Optional[str] = None,
    count_per_combo: int = 1,
) -> List[dict]:
    """
    Generates job dictionaries for all combinations of styles x moods x count_per_combo.
    Each job: {job_type: 'text_to_image', prompt, negative_prompt, parameters: {width, height, model, style, mood}, priority: 1}
    """
    if not styles:
        styles = ["photorealistic"]
    elif isinstance(styles, str):
        styles = [styles]

    if not moods:
        moods = [None]
    elif isinstance(moods, str):
        moods = [moods]

    jobs = []
    for style in styles:
        for mood in moods:
            for _ in range(count_per_combo):
                prompt_data = build_image_prompt(
                    user_prompt=base_prompt,
                    faceid_id=faceid_id,
                    faceid_weight=faceid_weight,
                    style=style,
                    mood=mood,
                    aspect_ratio=aspect_ratio,
                    character=character,
                )

                jobs.append({
                    "job_type": "text_to_image",
                    "prompt": prompt_data["prompt"],
                    "negative_prompt": prompt_data["negative_prompt"],
                    "parameters": {
                        "width": prompt_data["width"],
                        "height": prompt_data["height"],
                        "model": prompt_data["model"],
                        "style": style,
                        "mood": mood,
                        "faceid_id": faceid_id,
                        "faceid_weight": faceid_weight,
                        "character": character,
                        "aspect_ratio": aspect_ratio,
                    },
                    "priority": 1,
                })

    return jobs


def batch_generate_videos(
    base_image_prompt: str,
    video_styles: Optional[List[str]] = None,
    faceid_id: Optional[str] = None,
    custom_video_prompt: Optional[str] = None,
) -> List[dict]:
    """
    Generates video job dicts for given video styles.
    Each: {job_type: 'image_to_video', prompt: video_prompt, parameters: {image_prompt, duration, aspect_ratio, engine, video_style}, priority: 1}
    """
    if not video_styles:
        video_styles = ["pool_scene"]
    elif isinstance(video_styles, str):
        video_styles = [video_styles]

    jobs = []
    for vstyle in video_styles:
        prompt_data = build_video_prompt(
            image_prompt=base_image_prompt,
            video_style=vstyle,
            faceid_id=faceid_id,
            custom_video_prompt=custom_video_prompt,
        )

        jobs.append({
            "job_type": "image_to_video",
            "prompt": prompt_data["video_prompt"],
            "parameters": {
                "image_prompt": prompt_data["image_prompt"],
                "duration": prompt_data["duration"],
                "aspect_ratio": prompt_data["aspect_ratio"],
                "engine": prompt_data["engine"],
                "video_style": vstyle,
                "faceid_id": faceid_id,
            },
            "priority": 1,
        })

    return jobs


def create_composite_scene(
    face_ids: List[str],
    outfit_ids: Optional[List[str]] = None,
    location_ids: Optional[List[str]] = None,
    action: str = "",
    style: str = "cinematic",
    mood: str = "sensual",
    aspect_ratio: str = "16:9",
) -> dict:
    """
    Returns single composite scene job dict.
    """
    scene_prompt = build_scene_composition(
        face_ids=face_ids,
        outfit_ids=outfit_ids,
        location_ids=location_ids,
        action=action,
    )

    prompt_data = build_image_prompt(
        user_prompt=scene_prompt,
        style=style,
        mood=mood,
        aspect_ratio=aspect_ratio,
    )

    return {
        "job_type": "composite_scene",
        "prompt": prompt_data["prompt"],
        "negative_prompt": prompt_data["negative_prompt"],
        "parameters": {
            "width": prompt_data["width"],
            "height": prompt_data["height"],
            "model": prompt_data["model"],
            "face_ids": face_ids,
            "outfit_ids": outfit_ids,
            "location_ids": location_ids,
            "action": action,
            "style": style,
            "mood": mood,
            "aspect_ratio": aspect_ratio,
        },
        "priority": 1,
    }


def run_batch_from_pack(
    pack_name: str,
    styles: Optional[List[str]] = None,
    moods: Optional[List[str]] = None,
    faceid_id: Optional[str] = None,
    aspect_ratio: str = "1:1",
) -> List[dict]:
    """
    Takes a prompt pack and generates jobs for each prompt in the pack.
    """
    pack_info = PROMPT_PACKS.get(pack_name, {})
    prompts = get_prompt_pack(pack_name)
    category = pack_info.get("category", "styles")

    all_jobs = []
    is_video_pack = category in ("video", "xxx_video")

    for prompt_text in prompts:
        if is_video_pack:
            v_styles = styles if styles else None
            jobs = batch_generate_videos(
                base_image_prompt=prompt_text,
                video_styles=v_styles,
                faceid_id=faceid_id,
            )
        else:
            jobs = batch_generate_images(
                base_prompt=prompt_text,
                styles=styles,
                moods=moods,
                faceid_id=faceid_id,
                aspect_ratio=aspect_ratio,
            )
        all_jobs.extend(jobs)

    return all_jobs


if __name__ == "__main__":
    print("=== ShimiStudio Batch Generator v2.0 ===\n")

    print("📦 Available Prompt Packs:")
    packs = list_prompt_packs()
    for p in packs:
        print(f"  - [{p['id']}] {p['name']} ({p['category']}): {p['count']} prompts")

    print("\n📸 Demo Batch Image Generation:")
    demo_images = batch_generate_images(
        base_prompt="woman sitting on a terrace",
        styles=["photorealistic", "cinematic"],
        moods=["sensual", "romantic"],
        aspect_ratio="16:9",
    )
    print(f"Generated {len(demo_images)} image job(s). First job preview:")
    print(f"  Job Type: {demo_images[0]['job_type']}")
    print(f"  Prompt: {demo_images[0]['prompt'][:80]}...")
    print(f"  Params: {demo_images[0]['parameters']}")

    print("\n🎥 Demo Batch Video Generation:")
    demo_videos = batch_generate_videos(
        base_image_prompt="woman at a pool",
        video_styles=["pool_scene", "conservatory_video"],
    )
    print(f"Generated {len(demo_videos)} video job(s). First job preview:")
    print(f"  Job Type: {demo_videos[0]['job_type']}")
    print(f"  Engine: {demo_videos[0]['parameters']['engine']}")

    print("\n🎬 Demo Composite Scene Creation:")
    composite = create_composite_scene(
        face_ids=["4995297", "4995298"],
        outfit_ids=["bikini_01"],
        location_ids=["pool_01"],
        action="They walk together to the pool and sit down",
    )
    print(f"Composite job: {composite['job_type']}")
    print(f"Prompt: {composite['prompt'][:80]}...")

    print("\n📦 Demo Run Batch From Pack ('portrait_basics'):")
    pack_jobs = run_batch_from_pack(
        pack_name="portrait_basics",
        styles=["photorealistic"],
    )
    print(f"Generated {len(pack_jobs)} job(s) from pack 'portrait_basics'.")
