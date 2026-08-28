"""
ShimiStudio Style Library v2.0
Core library for style, character, mood, and video prompt building.
"""

from typing import Dict, List, Optional, Any


# ============================================================
# 1. CATEGORIES
# ============================================================

CATEGORIES: Dict[str, str] = {
    "styles": "Standard image styles — portraits, fashion, everyday scenes",
    "xxx": "Explicit content — NSFW image styles",
    "video": "Video styles — motion, action, scenes",
    "xxx_video": "Explicit video content — NSFW video scenes",
}


# ============================================================
# 2. STYLES (12 Core Image Styles)
# ============================================================

STYLES: Dict[str, Dict[str, Any]] = {
    "photorealistic": {
        "name": "Photorealistic",
        "category": "styles",
        "image_prompt": "photorealistic, high detail, natural lighting, sharp focus, 8K",
        "negative": "cartoon, anime, painting, sketch, low quality, blurry",
        "model": "flux",
    },
    "cinematic": {
        "name": "Cinematic",
        "category": "styles",
        "image_prompt": "cinematic shot, dramatic lighting, shallow depth of field, film grain, color graded, anamorphic",
        "negative": "flat lighting, snapshot, amateur",
        "model": "flux",
    },
    "anime": {
        "name": "Anime",
        "category": "styles",
        "image_prompt": "anime style, cel shading, vibrant colors, detailed eyes, studio quality",
        "negative": "photorealistic, 3D, oil painting",
        "model": "flux",
    },
    "oil_painting": {
        "name": "Oil Painting",
        "category": "styles",
        "image_prompt": "oil painting, thick brush strokes, canvas texture, classical art style",
        "negative": "photorealistic, digital, anime",
        "model": "flux",
    },
    "watercolor": {
        "name": "Watercolor",
        "category": "styles",
        "image_prompt": "watercolor painting, soft edges, flowing colors, paper texture",
        "negative": "photorealistic, sharp, digital",
        "model": "flux",
    },
    "fantasy": {
        "name": "Fantasy",
        "category": "styles",
        "image_prompt": "fantasy art, magical atmosphere, ethereal lighting, detailed environment",
        "negative": "photorealistic, mundane, plain",
        "model": "flux",
    },
    "artistic": {
        "name": "Artistic",
        "category": "styles",
        "image_prompt": "artistic photography, creative composition, expressive, fine art",
        "negative": "snapshot, amateur, plain",
        "model": "flux",
    },
    "sketch": {
        "name": "Sketch",
        "category": "styles",
        "image_prompt": "pencil sketch, detailed line work, cross hatching, artistic drawing",
        "negative": "photorealistic, color, digital",
        "model": "flux",
    },
    "amateur_phone": {
        "name": "Amateur Phone Photo",
        "category": "styles",
        "image_prompt": "amateur phone photo, natural lighting, slightly unedited, realistic skin texture, casual snapshot",
        "negative": "professional, studio lighting, airbrushed",
        "model": "flux",
    },
    "mirror_selfie": {
        "name": "Mirror Selfie",
        "category": "styles",
        "image_prompt": "mirror selfie, phone in hand, bathroom or bedroom mirror, casual pose, natural lighting",
        "negative": "professional, studio, posed",
        "model": "flux",
    },
    "gym_mirror": {
        "name": "Gym Mirror Selfie",
        "category": "styles",
        "image_prompt": "sweaty skin, tight compression leggings and crop top, amateur selfie in gym mirror, natural gym lighting, glistening skin texture, holding phone, public gym with equipment and mirrored walls",
        "negative": "professional, studio, clean",
        "model": "flux",
    },
    "conservatory": {
        "name": "Conservatory",
        "category": "styles",
        "image_prompt": "amateur slightly low-angle phone photo in a conservatory, facing away looking over shoulder, standing in front of patio doors, grey daylight, high ISO grain, unedited snapshot",
        "negative": "professional, studio, perfect lighting",
        "model": "flux",
    },
}


# ============================================================
# 3. MOODS (8 Mood Modifiers)
# ============================================================

MOODS: Dict[str, Dict[str, str]] = {
    "sensual": {
        "name": "Sensual",
        "modifier": "sensual atmosphere, soft warm lighting, intimate mood, seductive pose",
    },
    "romantic": {
        "name": "Romantic",
        "modifier": "romantic atmosphere, golden hour lighting, soft bokeh, dreamy mood",
    },
    "bold": {
        "name": "Bold",
        "modifier": "bold composition, strong contrast, confident pose, dramatic shadows",
    },
    "ethereal": {
        "name": "Ethereal",
        "modifier": "ethereal glow, soft diffused lighting, dreamy atmosphere, magical feel",
    },
    "dark": {
        "name": "Dark",
        "modifier": "dark moody atmosphere, low key lighting, deep shadows, mysterious",
    },
    "playful": {
        "name": "Playful",
        "modifier": "playful energy, bright colors, fun pose, cheerful mood",
    },
    "intimate": {
        "name": "Intimate",
        "modifier": "intimate setting, warm dim lighting, close framing, personal feel",
    },
    "passionate": {
        "name": "Passionate",
        "modifier": "passionate energy, intense expression, dynamic pose, warm tones",
    },
}


# ============================================================
# 4. VIDEO_STYLES (6 Core Video Styles)
# ============================================================

VIDEO_STYLES: Dict[str, Dict[str, Any]] = {
    "pool_scene": {
        "name": "Pool Scene",
        "category": "video",
        "image_prompt": "Distant shot of a swimming pool",
        "video_prompt": (
            "Image_1 is the woman. Lock her face, body, hair, and identity to Image_1. Do not change how she looks.\n\n"
            "Single continuous 5-second take, photoreal, candid voyeur holiday footage, 16:9, no cuts.\n\n"
            "Long-lens telephoto from a distance across a busy public hotel pool, shot from behind a white balcony rail "
            "and an out-of-focus potted palm. Harsh midday sun, heat haze, mild handheld iPhone wobble. She never looks at the camera.\n\n"
            "She is wearing a bikini.\n\n"
            "[0–5s] She climbs the pool ladder in the shallow end, water sheeting off her, then takes two steps onto the hot stone "
            "toward a white sunlounger. Slow clumsy zoom. End as she reaches the chair.\n\n"
            "Audio: distant splashes, muffled pool chatter, no music, no captions.\n"
            "Candid only — no posing, no slow-mo, no beauty light."
        ),
        "duration": 5,
        "aspect_ratio": "16:9",
        "engine": "wan22_i2v",
    },
    "gym_scene": {
        "name": "Gym Scene",
        "category": "video",
        "image_prompt": (
            "she has sweaty skin, wearing tight skinny compression leggings and tiny crop top, taking amateur selfie in gym mirror, "
            "natural gym lighting with soft shadows, photorealistic real-life photo, detailed glistening skin texture and sweat droplets, "
            "holding an iphone, public gym with gym equipment and mirrored walls with a black floor"
        ),
        "video_prompt": (
            "Use the person from the reference image as the only character. Keep their face, body, and identity consistent with "
            "the reference. Do not change their appearance.\n\n"
            "She poses showing off her gym gains, flexing for the mirror camera. Natural gym movements, no acting.\n\n"
            "Audio: music plays on the gym speaker system, gym chatter, weights clinking."
        ),
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
    "tiktok_dance": {
        "name": "TikTok Dance",
        "category": "video",
        "image_prompt": (
            "iphone shot of a woman, medium closeup wearing a bikini, she is facing the viewer, amateur exposure and lighting, "
            "dark room background, neutral pose with arms by her side"
        ),
        "video_prompt": (
            "Use the person from the reference image as the only character. Keep their face, body, and identity consistent with "
            "the reference. Do not change their appearance.\n\n"
            "She performs a sexy TikTok style dance routine, pouting. Image 1 defines the woman's identity and appearance. "
            "Video 1 is used ONLY as a motion and camera reference, no likeness from video.\n\n"
            "Audio: upbeat music, no voice."
        ),
        "duration": 10,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
    "conservatory_video": {
        "name": "Conservatory Video",
        "category": "video",
        "image_prompt": (
            "amateur slightly low-angle phone photo in a conservatory, facing away looking over shoulder, standing in front of patio doors, "
            "grey daylight, high ISO grain, unedited snapshot"
        ),
        "video_prompt": (
            "Use the person from the reference image as the only character. Keep their face, body, and identity consistent with "
            "the reference. Do not change their appearance.\n\n"
            "She turns slowly to face the camera, then walks toward it. Natural movement, no posing.\n\n"
            "Audio: quiet ambient room tone, no music."
        ),
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
    "xxx_pool": {
        "name": "Pool XXX",
        "category": "xxx_video",
        "image_prompt": "Distant shot of a swimming pool",
        "video_prompt": (
            "Image_1 is the woman. Lock her face, body, hair, and identity to Image_1. Do not change how she looks.\n\n"
            "Single continuous 5-second take, photoreal, candid voyeur holiday footage, 16:9, no cuts.\n\n"
            "Long-lens telephoto from a distance across a busy public hotel pool. Harsh midday sun, heat haze, mild handheld iPhone wobble. "
            "She never looks at the camera.\n\n"
            "She is wearing a bikini. She removes her bikini top while walking.\n\n"
            "[0–5s] She climbs the pool ladder, water sheeting off her, takes steps toward a sunlounger. End as she reaches the chair.\n\n"
            "Audio: distant splashes, muffled pool chatter, no music."
        ),
        "duration": 5,
        "aspect_ratio": "16:9",
        "engine": "wan22_i2v",
    },
    "xxx_conservatory": {
        "name": "Conservatory XXX",
        "category": "xxx_video",
        "image_prompt": (
            "amateur slightly low-angle phone photo in a conservatory, facing away looking over shoulder, wearing only an unbuttoned cardigan, "
            "standing in front of patio doors, camera close, grey daylight, high ISO grain, unedited snapshot"
        ),
        "video_prompt": (
            "Use the person from the reference image as the only character. Keep their face, body, and identity consistent with "
            "the reference. Do not change their appearance.\n\n"
            "She spreads her ass cheeks and shows off her anus and naked pussy and pubes, fixed angle and no cuts or edits, no music."
        ),
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
}


# ============================================================
# 5. CHARACTERS (6 Core AI Personas)
# ============================================================

CHARACTERS: Dict[str, Dict[str, Any]] = {
    "luna": {
        "name": "Luna",
        "title": "Mystical Dreamer",
        "description": "A dreamy and ethereal persona with glowing skin and a mystical presence.",
        "personality": "dreamy, romantic, mystical, playful, confident",
        "default_style": "ethereal",
        "default_mood": "sensual",
        "system_prompt": "You are Luna, a mystical dreamer who loves soft warm lighting and ethereal aesthetics.",
        "appearance": {
            "height": "5'7\"",
            "build": "slim and graceful",
            "hair_color": "silver-white",
            "eye_color": "violet",
            "features": "ethereal presence, glowing skin, mystical aura",
        },
    },
    "scarlett": {
        "name": "Scarlett",
        "title": "Bold & Passionate",
        "description": "A bold and passionate beauty with deep red hair and striking emerald eyes.",
        "personality": "bold, passionate, confident, flirty, uninhibited",
        "default_style": "cinematic",
        "default_mood": "playful",
        "system_prompt": "You are Scarlett, a bold and passionate personality who projects confidence and flair.",
        "appearance": {
            "height": "5'9\"",
            "build": "curvy and athletic",
            "hair_color": "deep red",
            "eye_color": "emerald green",
            "features": "bold presence, confident smile, striking beauty",
        },
    },
    "jade": {
        "name": "Jade",
        "title": "Artistic Visionary",
        "description": "An adventurous artistic visionary with emerald green hair and artistic tattoos.",
        "personality": "artistic, creative, experimental, intellectual, adventurous",
        "default_style": "fantasy",
        "default_mood": "bold",
        "system_prompt": "You are Jade, an artistic visionary who loves creative compositions and bold aesthetics.",
        "appearance": {
            "height": "5'6\"",
            "build": "lean and graceful",
            "hair_color": "emerald green",
            "eye_color": "amber",
            "features": "artistic tattoos, creative style, unique presence",
        },
    },
    "aria": {
        "name": "Aria",
        "title": "Sensual Enchantress",
        "description": "A seductive enchantress with black hair and deep brown eyes, radiating elegance.",
        "personality": "seductive, enchanting, sensual, mysterious, captivating",
        "default_style": "photorealistic",
        "default_mood": "romantic",
        "system_prompt": "You are Aria, a sensual enchantress with a sultry presence and captivating gaze.",
        "appearance": {
            "height": "5'8\"",
            "build": "curvaceous and sensual",
            "hair_color": "black",
            "eye_color": "deep brown",
            "features": "sultry presence, captivating gaze, sensual elegance",
        },
    },
    "nova": {
        "name": "Nova",
        "title": "Futuristic Innovator",
        "description": "A futuristic tech-savvy innovator with silver hair and cyber blue eyes.",
        "personality": "innovative, bold, tech-savvy, confident, uninhibited",
        "default_style": "cinematic",
        "default_mood": "bold",
        "system_prompt": "You are Nova, a futuristic innovator combining tech aesthetics with bold confidence.",
        "appearance": {
            "height": "5'7\"",
            "build": "athletic and sleek",
            "hair_color": "silver with neon accents",
            "eye_color": "cyber blue",
            "features": "futuristic style, tech aesthetic, bold presence",
        },
    },
    "venus": {
        "name": "Venus",
        "title": "Goddess of Pleasure",
        "description": "A divine beauty with golden blonde hair and ocean blue eyes radiating a goddess presence.",
        "personality": "divine, luxurious, pleasure-seeking, confident, uninhibited",
        "default_style": "photorealistic",
        "default_mood": "sensual",
        "system_prompt": "You are Venus, the goddess of pleasure, radiating divine beauty and warmth.",
        "appearance": {
            "height": "5'9\"",
            "build": "voluptuous and divine",
            "hair_color": "golden blonde",
            "eye_color": "ocean blue",
            "features": "divine beauty, radiant glow, goddess presence",
        },
    },
}


# ============================================================
# 6. ASPECT RATIOS & 7. DURATIONS
# ============================================================

ASPECT_RATIOS: Dict[str, Dict[str, int]] = {
    "1:1": {"width": 1024, "height": 1024},
    "16:9": {"width": 1280, "height": 720},
    "9:16": {"width": 720, "height": 1280},
    "4:3": {"width": 1024, "height": 768},
    "3:4": {"width": 768, "height": 1024},
}

DURATIONS: List[int] = [5, 10, 15, 30]


# ============================================================
# 8. PROMPT PACKS
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


# ============================================================
# 9. Core Functions
# ============================================================

def build_image_prompt(
    user_prompt: str = "",
    faceid_id: Optional[str] = None,
    faceid_weight: float = 1.0,
    style: Optional[str] = None,
    mood: Optional[str] = None,
    aspect_ratio: str = "1:1",
    character: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a structured dictionary containing full image prompt, negative prompt,
    dimensions, and target model based on style, mood, character, and parameters.
    """
    prompt_parts: List[str] = []

    # Handle character defaults and description
    char_data = CHARACTERS.get(character.lower()) if character and character.lower() in CHARACTERS else None
    if char_data:
        app = char_data.get("appearance", {})
        char_desc = (
            f"{char_data['name']} ({app.get('hair_color', '')} hair, "
            f"{app.get('eye_color', '')} eyes, {app.get('build', '')})"
        )
        prompt_parts.append(char_desc)
        if not style:
            style = char_data.get("default_style")
        if not mood:
            mood = char_data.get("default_mood")

    # Add style prompt
    style_data = STYLES.get(style) if style and style in STYLES else None
    if style_data and style_data.get("image_prompt"):
        prompt_parts.append(style_data["image_prompt"])

    # Add mood modifier
    mood_data = MOODS.get(mood) if mood and mood in MOODS else None
    if mood_data and mood_data.get("modifier"):
        prompt_parts.append(mood_data["modifier"])

    # Add FaceID trigger tag
    if faceid_id:
        prompt_parts.append(f"[FaceID: {faceid_id}, weight: {faceid_weight}]")

    # Add user prompt
    if user_prompt:
        prompt_parts.append(user_prompt)

    final_prompt = ", ".join(prompt_parts) if prompt_parts else user_prompt
    negative_prompt = style_data.get("negative", "") if style_data else ""
    model = style_data.get("model", "flux") if style_data else "flux"

    ar_info = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["1:1"])
    width = ar_info["width"]
    height = ar_info["height"]

    return {
        "prompt": final_prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": aspect_ratio,
        "width": width,
        "height": height,
        "model": model,
    }


def build_video_prompt(
    image_prompt: str = "",
    video_style: Optional[str] = None,
    faceid_id: Optional[str] = None,
    custom_video_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Builds a structured video generation request containing image_prompt, video_prompt,
    duration, aspect_ratio, and engine.
    """
    vstyle_data = VIDEO_STYLES.get(video_style) if video_style and video_style in VIDEO_STYLES else None

    base_img_prompt = image_prompt
    if not base_img_prompt and vstyle_data:
        base_img_prompt = vstyle_data.get("image_prompt", "")

    v_prompt = custom_video_prompt
    if not v_prompt and vstyle_data:
        v_prompt = vstyle_data.get("video_prompt", "")
    if not v_prompt:
        v_prompt = base_img_prompt

    if faceid_id and f"FaceID: {faceid_id}" not in v_prompt:
        v_prompt = f"[FaceID: {faceid_id}]\n{v_prompt}"

    duration = vstyle_data.get("duration", 5) if vstyle_data else 5
    aspect_ratio = vstyle_data.get("aspect_ratio", "16:9") if vstyle_data else "16:9"
    engine = vstyle_data.get("engine", "wan22_i2v") if vstyle_data else "wan22_i2v"

    return {
        "image_prompt": base_img_prompt,
        "video_prompt": v_prompt,
        "duration": duration,
        "aspect_ratio": aspect_ratio,
        "engine": engine,
    }


def build_scene_composition(
    face_ids: List[str],
    outfit_ids: Optional[List[str]] = None,
    location_ids: Optional[List[str]] = None,
    action: str = "",
) -> str:
    """
    Builds a composite scene prompt from multiple face IDs, outfits, locations, and actions.
    """
    parts: List[str] = []
    if face_ids:
        faces_str = ", ".join([f"Person {i+1} (FaceID: {fid})" for i, fid in enumerate(face_ids)])
        parts.append(f"Characters: {faces_str}")
    if outfit_ids:
        parts.append("Outfits: " + ", ".join(outfit_ids))
    if location_ids:
        parts.append("Locations: " + ", ".join(location_ids))
    if action:
        parts.append(f"Action: {action}")
    return ". ".join(parts)


def list_styles(category: Optional[str] = None) -> List[tuple]:
    """Returns a list of (key, name) tuples for image styles, optionally filtered by category."""
    if category:
        return [(k, v["name"]) for k, v in STYLES.items() if v.get("category") == category]
    return [(k, v["name"]) for k, v in STYLES.items()]


def list_video_styles(category: Optional[str] = None) -> List[tuple]:
    """Returns a list of (key, name) tuples for video styles, optionally filtered by category."""
    if category:
        return [(k, v["name"]) for k, v in VIDEO_STYLES.items() if v.get("category") == category]
    return [(k, v["name"]) for k, v in VIDEO_STYLES.items()]


def list_moods() -> List[tuple]:
    """Returns a list of (key, name) tuples for available moods."""
    return [(k, v["name"]) for k, v in MOODS.items()]


def list_characters() -> List[tuple]:
    """Returns a list of (key, name) tuples for available AI characters."""
    return [(k, v["name"]) for k, v in CHARACTERS.items()]


def list_prompt_packs(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns prompt packs, optionally filtered by category."""
    if category:
        return [{"pack_key": k, **v} for k, v in PROMPT_PACKS.items() if v.get("category") == category]
    return [{"pack_key": k, **v} for k, v in PROMPT_PACKS.items()]


def get_prompt_pack(pack_name: str) -> List[str]:
    """Retrieves list of prompt strings for a given prompt pack name."""
    pack = PROMPT_PACKS.get(pack_name)
    if not pack:
        return []
    return pack.get("prompts", [])


if __name__ == "__main__":
    print("=== ShimiStudio Style Library v2.0 Demo ===\n")

    print("🎨 Available Image Styles:")
    for key, name in list_styles():
        print(f"  - {key}: {name}")

    print("\n🎭 Available Moods:")
    for key, name in list_moods():
        print(f"  - {key}: {name}")

    print("\n🎥 Available Video Styles:")
    for key, name in list_video_styles():
        print(f"  - {key}: {name}")

    print("\n👤 Available Characters:")
    for key, name in list_characters():
        print(f"  - {key}: {name}")

    print("\n📦 Prompt Packs:")
    for pack in list_prompt_packs():
        print(f"  - {pack['name']} ({pack['category']}): {len(pack['prompts'])} prompts")

    print("\n⚙️ Testing build_image_prompt:")
    demo_img = build_image_prompt(
        user_prompt="walking through autumn park",
        style="cinematic",
        mood="romantic",
        character="luna",
        aspect_ratio="16:9",
    )
    print(f"Prompt: {demo_img['prompt']}")
    print(f"Negative: {demo_img['negative_prompt']}")
    print(f"Dimensions: {demo_img['width']}x{demo_img['height']} ({demo_img['aspect_ratio']})")

    print("\n🎥 Testing build_video_prompt:")
    demo_vid = build_video_prompt(
        image_prompt="",
        video_style="pool_scene",
        faceid_id="face_12345",
    )
    print(f"Engine: {demo_vid['engine']}, Duration: {demo_vid['duration']}s, Ratio: {demo_vid['aspect_ratio']}")
    print(f"Video Prompt Snippet:\n{demo_vid['video_prompt'][:150]}...")
