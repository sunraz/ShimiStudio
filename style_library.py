"""
ShimiStudio Style Library v2.0
נבנה מתוך ניתוח xmode.ai + FantasyForge AI

כל סטייל מכיל:
- image_prompt: תיאור התמונה הבסיסי
- video_prompt: תיאור הוידאו המפורט (identity lock + camera + lighting + action + audio)
- faceid_weight: משקל ה-FaceID (0.0-1.0)
- negative_prompt: מה לא לכלול
- model: איזה מנוע להשתמש (xSD = Flux.1, xSD Pro = Flux.1 + refiner)
"""

# ============================================================
# קטגוריות (מבנה xmode.ai)
# ============================================================

CATEGORIES = {
    "styles": "סטיילים רגילים — פורטרטים, אופנה, סצנות יומיומיות",
    "xxx": "תוכן מפורש — NSFW",
    "video": "סטיילי וידאו — תנועה, פעולה, סצנות",
    "xxx_video": "וידאו מפורש — NSFW video",
}

# ============================================================
# סטיילים (מ-FantasyForge + xmode)
# ============================================================

STYLES = {
    # === סטיילים בסיסיים ===
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
        "negative": "flat lighting, snapshot, amateur, low quality",
        "model": "flux",
    },
    "anime": {
        "name": "Anime",
        "category": "styles",
        "image_prompt": "anime style, cel shading, vibrant colors, detailed eyes, studio quality",
        "negative": "photorealistic, 3D, oil painting, blurry",
        "model": "flux",
    },
    "oil_painting": {
        "name": "Oil Painting",
        "category": "styles",
        "image_prompt": "oil painting, thick brush strokes, canvas texture, classical art style, rich colors",
        "negative": "photorealistic, digital, anime, sharp edges",
        "model": "flux",
    },
    "watercolor": {
        "name": "Watercolor",
        "category": "styles",
        "image_prompt": "watercolor painting, soft edges, flowing colors, paper texture, delicate",
        "negative": "photorealistic, sharp, digital, harsh lines",
        "model": "flux",
    },
    "fantasy": {
        "name": "Fantasy",
        "category": "styles",
        "image_prompt": "fantasy art, magical atmosphere, ethereal lighting, detailed environment, digital painting",
        "negative": "photorealistic, mundane, plain, boring",
        "model": "flux",
    },
    "artistic": {
        "name": "Artistic",
        "category": "styles",
        "image_prompt": "artistic photography, creative composition, expressive, fine art",
        "negative": "snapshot, amateur, plain, boring",
        "model": "flux",
    },
    "sketch": {
        "name": "Sketch",
        "category": "styles",
        "image_prompt": "pencil sketch, detailed line work, cross hatching, artistic drawing",
        "negative": "photorealistic, color, digital, 3D",
        "model": "flux",
    },

    # === סטיילים אמיתיים (מ-xmode.ai) ===
    "amateur_phone": {
        "name": "Amateur Phone Photo",
        "category": "styles",
        "image_prompt": "amateur phone photo, natural lighting, slightly unedited, realistic skin texture, casual snapshot",
        "negative": "professional, studio lighting, airbrushed, perfect",
        "model": "flux",
    },
    "mirror_selfie": {
        "name": "Mirror Selfie",
        "category": "styles",
        "image_prompt": "mirror selfie, phone in hand, bathroom or bedroom mirror, casual pose, natural lighting",
        "negative": "professional, studio, posed, formal",
        "model": "flux",
    },
    "gym_mirror": {
        "name": "Gym Mirror Selfie",
        "category": "styles",
        "image_prompt": "sweaty skin, tight compression leggings and crop top, amateur selfie in gym mirror, natural gym lighting, glistening skin texture, holding phone, public gym with equipment and mirrored walls",
        "negative": "professional, studio, clean, perfect lighting",
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
# מודים / טונים (מ-FantasyForge)
# ============================================================

MOODS = {
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
# סטיילי וידאו (מ-xmode.ai — המבנה המלא)
# ============================================================

VIDEO_STYLES = {
    # === Video (רגיל) ===
    "pool_scene": {
        "name": "Pool Scene",
        "category": "video",
        "image_prompt": "Distant shot of a swimming pool",
        "video_prompt": """Image_1 is the woman. Lock her face, body, hair, and identity to Image_1. Do not change how she looks.

Single continuous 5-second take, photoreal, candid voyeur holiday footage, 16:9, no cuts.

Long-lens telephoto from a distance across a busy public hotel pool, shot from behind a white balcony rail and an out-of-focus potted palm. Harsh midday sun, heat haze, mild handheld iPhone wobble. She never looks at the camera.

She is wearing a bikini.

[0–5s] She climbs the pool ladder in the shallow end, water sheeting off her, then takes two steps onto the hot stone toward a white sunlounger. Slow clumsy zoom. End as she reaches the chair.

Audio: distant splashes, muffled pool chatter, no music, no captions.
Candid only — no posing, no slow-mo, no beauty light.""",
        "duration": 5,
        "aspect_ratio": "16:9",
        "engine": "wan22_i2v",
    },
    "gym_scene": {
        "name": "Gym Scene",
        "category": "video",
        "image_prompt": "she has sweaty skin, wearing tight skinny compression leggings and tiny crop top, taking amateur selfie in gym mirror, natural gym lighting with soft shadows, photorealistic real-life photo, detailed glistening skin texture and sweat droplets, sharp fabric details, high resolution, holding an iphone, public gym with gym equipment and mirrored walls with a black floor",
        "video_prompt": """Use the person from the reference image as the only character. Keep their face, body, and identity consistent with the reference. Do not change their appearance.

She poses showing off her gym gains, flexing for the mirror camera. Natural gym movements, no acting.

Audio: music plays on the gym speaker system, gym chatter, weights clinking.""",
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
    "tiktok_dance": {
        "name": "TikTok Dance",
        "category": "video",
        "image_prompt": "iphone shot of a woman, medium closeup wearing a bikini, she is facing the viewer, amateur exposure and lighting, dark room background, neutral pose with arms by her side",
        "video_prompt": """Use the person from the reference image as the only character. Keep their face, body, and identity consistent with the reference. Do not change their appearance.

She performs a sexy TikTok style dance routine, pouting. 

Image 1 defines the woman's identity and appearance. 
Video 1 is used ONLY as a motion and camera reference, no likeness from video.

Audio: upbeat music, no voice.""",
        "duration": 10,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
    "conservatory_video": {
        "name": "Conservatory Video",
        "category": "video",
        "image_prompt": "amateur slightly low-angle phone photo in a conservatory, she is facing away looking over her shoulder, standing in front of patio doors and a dying houseplant, grey daylight, high ISO grain, unedited snapshot",
        "video_prompt": """Use the person from the reference image as the only character. Keep their face, body, and identity consistent with the reference. Do not change their appearance.

She turns slowly to face the camera, then walks toward it. Natural movement, no posing.

Audio: quiet ambient room tone, no music.""",
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },

    # === XXX Video (מפורש) ===
    "xxx_pool": {
        "name": "Pool XXX",
        "category": "xxx_video",
        "image_prompt": "Distant shot of a swimming pool",
        "video_prompt": """Image_1 is the woman. Lock her face, body, hair, and identity to Image_1. Do not change how she looks.

Single continuous 5-second take, photoreal, candid voyeur holiday footage, 16:9, no cuts.

Long-lens telephoto from a distance across a busy public hotel pool. Harsh midday sun, heat haze, mild handheld iPhone wobble. She never looks at the camera.

She is wearing a bikini. She removes her bikini top while walking.

[0–5s] She climbs the pool ladder, water sheeting off her, takes steps toward a sunlounger. End as she reaches the chair.

Audio: distant splashes, muffled pool chatter, no music.""",
        "duration": 5,
        "aspect_ratio": "16:9",
        "engine": "wan22_i2v",
    },
    "xxx_conservatory": {
        "name": "Conservatory XXX",
        "category": "xxx_video",
        "image_prompt": "amateur slightly low-angle phone photo in a conservatory, she is facing away looking over her shoulder, wearing only an unbuttoned cardigan, standing in front of patio doors, camera close, grey daylight, high ISO grain, unedited snapshot",
        "video_prompt": """Use the person from the reference image as the only character. Keep their face, body, and identity consistent with the reference. Do not change their appearance.

She spreads her ass cheeks and shows off her anus and naked pussy and pubes, fixed angle and no cuts or edits, no music.""",
        "duration": 5,
        "aspect_ratio": "9:16",
        "engine": "wan22_i2v",
    },
}

# ============================================================
# דמויות / Personas (מ-FantasyForge AI)
# ============================================================

CHARACTERS = {
    "luna": {
        "name": "Luna",
        "title": "Mystical Dreamer",
        "description": "An ethereal and sensual character who loves creating dreamy, romantic content with magical vibes.",
        "personality": "Dreamy, romantic, mystical, playful, confident",
        "default_style": "ethereal",
        "default_mood": "sensual",
        "system_prompt": """You are Luna, a mystical and ethereal character who creates beautiful, sensual content. 
You have a dreamy personality and love exploring romantic and magical themes. 
You're playful, confident, and always ready to create stunning visual content.
You speak with poetic flair and enthusiasm about creating content.""",
        "appearance": {
            "height": "5'7\"",
            "build": "Slim and graceful",
            "hair_color": "Silver-white",
            "eye_color": "Violet",
        },
    },
    "scarlett": {
        "name": "Scarlett",
        "title": "Bold & Passionate",
        "description": "A confident and daring character who creates bold, passionate, and explicit content without hesitation.",
        "personality": "Bold, passionate, confident, flirty, uninhibited",
        "default_style": "cinematic",
        "default_mood": "playful",
        "system_prompt": """You are Scarlett, a bold and passionate character who creates daring, explicit content.
You're confident, flirty, and completely uninhibited in your creative expression.
You love pushing boundaries and creating content that's unapologetically sensual and explicit.""",
        "appearance": {
            "height": "5'9\"",
            "build": "Curvy and athletic",
            "hair_color": "Deep red",
            "eye_color": "Emerald green",
        },
    },
    "jade": {
        "name": "Jade",
        "title": "Artistic Visionary",
        "description": "A creative and artistic character who specializes in unique, experimental, and avant-garde content creation.",
        "personality": "Artistic, creative, experimental, intellectual, adventurous",
        "default_style": "fantasy",
        "default_mood": "bold",
        "system_prompt": """You are Jade, an artistic and visionary character who creates experimental and avant-garde content.
You're creative, intellectual, and love exploring new artistic boundaries.
You appreciate unique perspectives and unconventional approaches to content creation.""",
        "appearance": {
            "height": "5'6\"",
            "build": "Lean and graceful",
            "hair_color": "Emerald green",
            "eye_color": "Amber",
        },
    },
    "aria": {
        "name": "Aria",
        "title": "Sensual Enchantress",
        "description": "A seductive and enchanting character who creates intimate, sensual, and captivating content experiences.",
        "personality": "Seductive, enchanting, sensual, mysterious, captivating",
        "default_style": "photorealistic",
        "default_mood": "romantic",
        "system_prompt": """You are Aria, a seductive and enchanting character who creates intimate and sensual content.
You're mysterious, captivating, and excel at creating deeply sensual experiences.
You understand the art of seduction and create content that's both beautiful and explicit.""",
        "appearance": {
            "height": "5'8\"",
            "build": "Curvaceous and sensual",
            "hair_color": "Black",
            "eye_color": "Deep brown",
        },
    },
}

# ============================================================
# Aspect Ratios + Durations
# ============================================================

ASPECT_RATIOS = {
    "1:1": {"width": 1024, "height": 1024, "label": "Square"},
    "16:9": {"width": 1280, "height": 720, "label": "Landscape"},
    "9:16": {"width": 720, "height": 1280, "label": "Portrait"},
    "4:3": {"width": 1024, "height": 768, "label": "Classic"},
    "3:4": {"width": 768, "height": 1024, "label": "Tall"},
}

DURATIONS = [5, 10, 15, 30]

# ============================================================
# Free API Providers (מ-FantasyForge — fallback ללא GPU)
# ============================================================

FREE_API_PROVIDERS = {
    "airforce": {
        "name": "Airforce",
        "type": "image",
        "daily_limit": 1000,
        "endpoint": "https://api.airforce/v1/images/generations",
        "requires_auth": False,
        "quality": "high",
        "nsfw_support": True,
    },
    "pollinations": {
        "name": "Pollinations",
        "type": "image",
        "daily_limit": 100,
        "endpoint": "https://api.pollinations.ai/v1/images",
        "requires_auth": False,
        "quality": "medium",
        "nsfw_support": True,
    },
    "huggingface": {
        "name": "Hugging Face",
        "type": "image",
        "daily_limit": 50,
        "endpoint": "https://api-inference.huggingface.co/models",
        "requires_auth": True,
        "quality": "medium",
        "nsfw_support": True,
    },
}

# ============================================================
# Prompt Builder — בונה prompt מלא מרכיבים
# ============================================================

def build_image_prompt(
    user_prompt: str,
    faceid_id: str = None,
    faceid_weight: float = 1.0,
    style: str = None,
    mood: str = None,
    aspect_ratio: str = "1:1",
    character: str = None,
) -> dict:
    """
    בונה image prompt מלא במבנה xmode.ai
    
    Returns:
        {
            "prompt": ה-prompt המלא,
            "negative_prompt": מה לא לכלול,
            "aspect_ratio": "1:1",
            "width": 1024,
            "height": 1024,
            "model": "flux",
        }
    """
    parts = []
    negative_parts = []
    
    # FaceID (מבנה xmode)
    if faceid_id:
        parts.append(f"<faceid:{faceid_id}:{faceid_weight}>")
    
    # Character appearance
    if character and character in CHARACTERS:
        char = CHARACTERS[character]
        appearance = char.get("appearance", {})
        if appearance.get("hair_color"):
            parts.append(f"hair color: {appearance['hair_color']}")
        if appearance.get("eye_color"):
            parts.append(f"eye color: {appearance['eye_color']}")
        if appearance.get("build"):
            parts.append(f"body type: {appearance['build']}")
    
    # User prompt
    parts.append(user_prompt)
    
    # Style
    if style and style in STYLES:
        s = STYLES[style]
        parts.append(s["image_prompt"])
        if s.get("negative"):
            negative_parts.append(s["negative"])
    
    # Mood
    if mood and mood in MOODS:
        parts.append(MOODS[mood]["modifier"])
    
    # Aspect ratio
    ar = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["1:1"])
    
    full_prompt = ", ".join(parts)
    full_negative = ", ".join(negative_parts) if negative_parts else "low quality, blurry, deformed"
    
    return {
        "prompt": full_prompt,
        "negative_prompt": full_negative,
        "aspect_ratio": aspect_ratio,
        "width": ar["width"],
        "height": ar["height"],
        "model": STYLES.get(style, {}).get("model", "flux"),
    }


def build_video_prompt(
    image_prompt: str,
    video_style: str = None,
    faceid_id: str = None,
    custom_video_prompt: str = None,
) -> dict:
    """
    בונה video prompt מלא במבנה xmode.ai
    
    Returns:
        {
            "image_prompt": תיאור התמונה,
            "video_prompt": תיאור הוידאו המפורט,
            "duration": 5,
            "aspect_ratio": "16:9",
            "engine": "wan22_i2v",
        }
    """
    if video_style and video_style in VIDEO_STYLES:
        style = VIDEO_STYLES[video_style]
        return {
            "image_prompt": image_prompt or style["image_prompt"],
            "video_prompt": custom_video_prompt or style["video_prompt"],
            "duration": style.get("duration", 5),
            "aspect_ratio": style.get("aspect_ratio", "16:9"),
            "engine": style.get("engine", "wan22_i2v"),
        }
    
    # Custom video prompt (ללא סטייל מוגדר)
    if custom_video_prompt:
        return {
            "image_prompt": image_prompt,
            "video_prompt": custom_video_prompt,
            "duration": 5,
            "aspect_ratio": "16:9",
            "engine": "wan22_i2v",
        }
    
    # Default — identity lock בלבד
    identity = f"Image_1 is the woman. Lock her face, body, hair, and identity to Image_1. Do not change how she looks.\n\n"
    return {
        "image_prompt": image_prompt,
        "video_prompt": identity + "Single continuous 5-second take, photoreal, natural movement, no cuts.\n\nAudio: ambient sound, no music.",
        "duration": 5,
        "aspect_ratio": "16:9",
        "engine": "wan22_i2v",
    }


def build_scene_composition(face_ids: list, outfit_ids: list = None, location_ids: list = None, action: str = "") -> str:
    """
    בונה סצנה מורכבת ממספר FaceIDs (מבנה xmode.ai scene composition)
    
    Example:
        face_ids = ["4995297"]
        outfit_ids = ["outfit_001"]
        location_ids = ["loc_pool"]
        action = "She walks to the pool"
    """
    parts = []
    
    # Faces
    for i, fid in enumerate(face_ids):
        parts.append(f"Image_{i+1} defines person {i+1}'s identity and appearance.")
    
    # Outfits
    if outfit_ids:
        for outfit in outfit_ids:
            parts.append(f"Outfit reference: {outfit}.")
    
    # Locations
    if location_ids:
        for loc in location_ids:
            parts.append(f"Location reference: {loc}.")
    
    # Action
    if action:
        parts.append(action)
    
    parts.append("Maintain identity consistency across all references. Do not change anyone's appearance.")
    
    return "\n\n".join(parts)


# ============================================================
# פונקציות עזר
# ============================================================

def list_styles(category: str = None) -> list:
    """מחזיר רשימת סטיילים לפי קטגוריה"""
    if category:
        return [(k, v["name"]) for k, v in STYLES.items() if v.get("category") == category]
    return [(k, v["name"]) for k, v in STYLES.items()]


def list_video_styles(category: str = None) -> list:
    """מחזיר רשימת סטיילי וידאו לפי קטגוריה"""
    if category:
        return [(k, v["name"]) for k, v in VIDEO_STYLES.items() if v.get("category") == category]
    return [(k, v["name"]) for k, v in VIDEO_STYLES.items()]


def list_moods() -> list:
    """מחזיר רשימת מודים"""
    return [(k, v["name"]) for k, v in MOODS.items()]


def list_characters() -> list:
    """מחזיר רשימת דמויות"""
    return [(k, v["name"]) for k, v in CHARACTERS.items()]


if __name__ == "__main__":
    # Demo
    print("=== ShimiStudio Style Library v2.0 ===\n")
    
    print("📸 Image Styles:")
    for k, name in list_styles():
        print(f"  - {k}: {name}")
    
    print(f"\n🎨 Moods:")
    for k, name in list_moods():
        print(f"  - {k}: {name}")
    
    print(f"\n🎥 Video Styles:")
    for k, name in list_video_styles():
        print(f"  - {k}: {name}")
    
    print(f"\n👤 Characters:")
    for k, name in list_characters():
        print(f"  - {k}: {name}")
    
    print("\n=== Demo: Build Image Prompt ===")
    result = build_image_prompt(
        user_prompt="woman standing in a park",
        faceid_id="4995297",
        faceid_weight=1.0,
        style="cinematic",
        mood="sensual",
        aspect_ratio="16:9",
    )
    print(f"Prompt: {result['prompt']}")
    print(f"Negative: {result['negative_prompt']}")
    print(f"Size: {result['width']}x{result['height']}")
    
    print("\n=== Demo: Build Video Prompt ===")
    vresult = build_video_prompt(
        image_prompt="woman at a pool",
        video_style="pool_scene",
    )
    print(f"Image: {vresult['image_prompt']}")
    print(f"Video:\n{vresult['video_prompt']}")
    print(f"Duration: {vresult['duration']}s")
    print(f"Engine: {vresult['engine']}")
    
    print("\n=== Demo: Scene Composition ===")
    scene = build_scene_composition(
        face_ids=["4995297", "4995298"],
        outfit_ids=["bikini_01"],
        location_ids=["pool_01"],
        action="She walks to the pool and sits on the edge",
    )
    print(scene)
