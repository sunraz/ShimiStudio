"""
ShimiStudio Batch Generator v2.0
מערכת Bulk Generation — נלקח מ-xmode.ai
מאפשר יצירה של מספר סטיילים/מודים במכה אחת
"""

import json
import os
import sys
import time
import requests
from typing import List, Optional

# Import style library
sys.path.insert(0, os.path.dirname(__file__))
from style_library import (
    STYLES, MOODS, VIDEO_STYLES, CHARACTERS,
    ASPECT_RATIOS, DURATIONS,
    build_image_prompt, build_video_prompt, build_scene_composition,
    list_styles, list_moods, list_video_styles, list_characters,
)

# ============================================================
# Batch Image Generation
# ============================================================

def batch_generate_images(
    base_prompt: str,
    styles: List[str] = None,
    moods: List[str] = None,
    faceid_id: str = None,
    faceid_weight: float = 1.0,
    aspect_ratio: str = "1:1",
    character: str = None,
    count_per_combo: int = 1,
) -> List[dict]:
    """
    יוצר מספר תמונות בכל שילובי סטייל × מוד
    
    דוגמה:
        batch_generate_images(
            base_prompt="woman in a park",
            styles=["photorealistic", "cinematic", "anime"],
            moods=["sensual", "playful"],
            faceid_id="4995297",
        )
        → יוצר 6 תמונות (3 סטיילים × 2 מודים)
    """
    if not styles:
        styles = ["photorealistic"]
    if not moods:
        moods = ["sensual"]
    
    jobs = []
    
    for style in styles:
        for mood in moods:
            for i in range(count_per_combo):
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
                    },
                    "priority": 1,
                })
    
    return jobs

# ============================================================
# Batch Video Generation
# ============================================================

def batch_generate_videos(
    base_image_prompt: str,
    video_styles: List[str] = None,
    faceid_id: str = None,
    custom_video_prompt: str = None,
) -> List[dict]:
    """
    יוצר מספר וידאו בסטיילים שונים
    
    דוגמה:
        batch_generate_videos(
            base_image_prompt="woman at a pool",
            video_styles=["pool_scene", "gym_scene", "tiktok_dance"],
            faceid_id="4995297",
        )
    """
    if not video_styles:
        video_styles = ["pool_scene"]
    
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
            },
            "priority": 1,
        })
    
    return jobs

# ============================================================
# Scene Composition — מספר FaceIDs בסצנה אחת
# ============================================================

def create_composite_scene(
    face_ids: List[str],
    outfit_ids: List[str] = None,
    location_ids: List[str] = None,
    action: str = "",
    style: str = "cinematic",
    mood: str = "sensual",
    aspect_ratio: str = "16:9",
) -> dict:
    """
    יוצר סצנה מורכבת עם מספר FaceIDs (מבנה xmode.ai)
    
    דוגמה:
        create_composite_scene(
            face_ids=["4995297", "4995298"],
            outfit_ids=["bikini_01", "swimsuit_01"],
            location_ids=["pool_01"],
            action="They walk together to the pool",
        )
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
        "job_type": "text_to_image",
        "prompt": prompt_data["prompt"],
        "negative_prompt": prompt_data["negative_prompt"],
        "parameters": {
            "width": prompt_data["width"],
            "height": prompt_data["height"],
            "model": prompt_data["model"],
            "face_ids": face_ids,
            "outfit_ids": outfit_ids,
            "location_ids": location_ids,
            "composite_scene": True,
        },
        "priority": 1,
    }

# ============================================================
# Prompt Pack — חבילות prompts מוכנות (מ-xmode "200+ curated prompts")
# ============================================================

PROMPT_PACKS = {
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
    """מחזיר חבילת prompts"""
    pack = PROMPT_PACKS.get(pack_name)
    if not pack:
        return []
    return pack["prompts"]

def list_prompt_packs(category: str = None) -> List[dict]:
    """מחזיר רשימת חבילות prompts"""
    if category:
        return [{"name": k, **v} for k, v in PROMPT_PACKS.items() if v.get("category") == category]
    return [{"name": k, **v} for k, v in PROMPT_PACKS.items()]

# ============================================================
# CLI Interface
# ============================================================

def interactive_menu():
    """תפריט אינטראקטיבי לבחירת סטיילים ויצירה"""
    print("=" * 60)
    print("  ShimiStudio v2.0 — Batch Generator")
    print("=" * 60)
    
    print("\n📸 Image Styles:")
    for k, name in list_styles("styles"):
        print(f"  {k:20s} → {name}")
    
    print("\n🎨 Moods:")
    for k, name in list_moods():
        print(f"  {k:20s} → {name}")
    
    print("\n🎥 Video Styles:")
    for k, name in list_video_styles():
        print(f"  {k:20s} → {name}")
    
    print("\n👤 Characters:")
    for k, name in list_characters():
        print(f"  {k:20s} → {name}")
    
    print("\n📦 Prompt Packs:")
    for pack in list_prompt_packs():
        print(f"  {pack['name']:20s} → {len(pack['prompts'])} prompts ({pack['category']})")
    
    print("\n" + "=" * 60)
    print("\nדוגמת שימוש:")
    print("  from batch_generator import batch_generate_images")
    print("  jobs = batch_generate_images(")
    print('      base_prompt="woman in a park",')
    print('      styles=["photorealistic", "cinematic"],')
    print('      moods=["sensual", "playful"],')
    print('      faceid_id="4995297",')
    print("  )")
    print(f"  → יוצר {2*2} jobs")


if __name__ == "__main__":
    interactive_menu()
    
    # Demo
    print("\n" + "=" * 60)
    print("  Demo: Batch Image Generation")
    print("=" * 60)
    
    jobs = batch_generate_images(
        base_prompt="woman standing in a park",
        styles=["photorealistic", "cinematic", "anime"],
        moods=["sensual", "playful"],
        faceid_id="4995297",
    )
    
    print(f"\nנוצרו {len(jobs)} jobs:")
    for i, job in enumerate(jobs):
        print(f"\n  Job {i+1}:")
        print(f"    Style: {job['parameters']['style']}")
        print(f"    Mood: {job['parameters']['mood']}")
        print(f"    Size: {job['parameters']['width']}x{job['parameters']['height']}")
        print(f"    Prompt: {job['prompt'][:80]}...")
    
    print("\n" + "=" * 60)
    print("  Demo: Batch Video Generation")
    print("=" * 60)
    
    vjobs = batch_generate_videos(
        base_image_prompt="woman at a pool",
        video_styles=["pool_scene", "gym_scene", "tiktok_dance"],
        faceid_id="4995297",
    )
    
    print(f"\nנוצרו {len(vjobs)} video jobs:")
    for i, job in enumerate(vjobs):
        print(f"\n  Video Job {i+1}:")
        print(f"    Style: {job['parameters']['video_style']}")
        print(f"    Duration: {job['parameters']['duration']}s")
        print(f"    Engine: {job['parameters']['engine']}")
    
    print("\n" + "=" * 60)
    print("  Demo: Composite Scene")
    print("=" * 60)
    
    scene = create_composite_scene(
        face_ids=["4995297", "4995298"],
        outfit_ids=["bikini_01"],
        location_ids=["pool_01"],
        action="They walk together to the pool and sit on the edge",
    )
    print(f"\n  Scene prompt: {scene['prompt'][:100]}...")
    print(f"  Face IDs: {scene['parameters']['face_ids']}")
    print(f"  Composite: {scene['parameters']['composite_scene']}")
