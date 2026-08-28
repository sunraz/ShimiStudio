"""
ShimiStudio Free API Fallback
מערכת rotation של APIs חינמיים כ-fallback כשאין GPU מקומי
נלקח מ-FantasyForge AI ומותאם ל-ShimiStudio
"""

import requests
import base64
import os
import json
import time
from typing import Optional

# ============================================================
# API Providers — סדר עדיפות (מהכי הרבה חינם לפחות)
# ============================================================

API_PROVIDERS = [
    {
        "name": "Airforce",
        "type": "image",
        "daily_limit": 1000,
        "endpoint": "https://api.airforce/v1/images/generations",
        "requires_auth": False,
        "quality": "high",
        "nsfw": True,
        "priority": 1,
    },
    {
        "name": "Pollinations",
        "type": "image",
        "daily_limit": 100,
        "endpoint": "https://image.pollinations.ai/prompt/",
        "requires_auth": False,
        "quality": "medium",
        "nsfw": True,
        "priority": 2,
    },
    {
        "name": "HuggingFace",
        "type": "image",
        "daily_limit": 50,
        "endpoint": "https://api-inference.huggingface.co/models/stable-diffusion-xl-base-1.0",
        "requires_auth": True,
        "auth_key_env": "HF_TOKEN",
        "quality": "medium",
        "nsfw": False,
        "priority": 3,
    },
]

# ============================================================
# Usage tracking (יומי)
# ============================================================

USAGE_FILE = os.path.expanduser("~/.shimistudio/api_usage.json")

def load_usage() -> dict:
    """טוען מונה שימוש יומי"""
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(USAGE_FILE):
        with open(USAGE_FILE, "r") as f:
            data = json.load(f)
        # איפוס יומי
        if data.get("date") != today:
            data = {"date": today, "providers": {}}
    else:
        data = {"date": today, "providers": {}}
    return data

def save_usage(data: dict):
    """שומר מונה שימוש"""
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_available_provider() -> Optional[dict]:
    """מוצא provider זמין עם מכסה יומי"""
    usage = load_usage()
    for provider in sorted(API_PROVIDERS, key=lambda x: x["priority"]):
        name = provider["name"]
        used = usage["providers"].get(name, 0)
        if used < provider["daily_limit"]:
            return provider
    return None

def increment_usage(provider_name: str):
    """מעלה מונה שימוש"""
    usage = load_usage()
    usage["providers"][provider_name] = usage["providers"].get(provider_name, 0) + 1
    save_usage(usage)

# ============================================================
# Image Generation דרך APIs חינמיים
# ============================================================

def generate_image_airforce(prompt: str, negative: str = "", width: int = 1024, height: int = 1024) -> dict:
    """
    Airforce API — 1000 חינם/יום, NSFW, איכות גבוהה
    """
    response = requests.post(
        "https://api.airforce/v1/images/generations",
        json={
            "prompt": prompt,
            "negative_prompt": negative,
            "width": width,
            "height": height,
            "n": 1,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    
    image_url = data.get("data", [{}])[0].get("url", "")
    if not image_url:
        raise ValueError("Airforce: no image URL in response")
    
    return {
        "provider": "Airforce",
        "url": image_url,
        "width": width,
        "height": height,
    }

def generate_image_pollinations(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """
    Pollinations API — 100 חינם/יום, NSFW, איכות בינונית
    URL-based: פשוט וישר מקבל תמונה
    """
    # Pollinations עובד עם URL ישירות
    safe_prompt = requests.utils.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&nsfw=true"
    
    # מוריד את התמונה
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    
    # שומר locally ומחזיר URL
    import tempfile
    import uuid
    
    temp_dir = os.path.join(tempfile.gettempdir(), "shimistudio")
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(response.content)
    
    return {
        "provider": "Pollinations",
        "url": filepath,  # local path
        "width": width,
        "height": height,
    }

def generate_image_huggingface(prompt: str, width: int = 1024, height: int = 1024) -> dict:
    """
    HuggingFace Inference API — 50 חינם/יום
    דורש HF_TOKEN
    """
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN not set")
    
    response = requests.post(
        "https://api-inference.huggingface.co/models/stable-diffusion-xl-base-1.0",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    
    # HF מחזיר binary image
    import tempfile
    import uuid
    
    temp_dir = os.path.join(tempfile.gettempdir(), "shimistudio")
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(temp_dir, filename)
    
    with open(filepath, "wb") as f:
        f.write(response.content)
    
    return {
        "provider": "HuggingFace",
        "url": filepath,
        "width": width,
        "height": height,
    }

# ============================================================
# Main — ניסיון עם rotation
# ============================================================

def generate_image_free(prompt: str, negative: str = "", width: int = 1024, height: int = 1024) -> dict:
    """
    מנסה ליצור תמונה דרך APIs חינמיים עם rotation אוטומטי
    מחזיר את התמונה מה-provider הראשון שמצליח
    """
    usage = load_usage()
    
    for provider in sorted(API_PROVIDERS, key=lambda x: x["priority"]):
        name = provider["name"]
        used = usage["providers"].get(name, 0)
        
        if used >= provider["daily_limit"]:
            continue
        
        try:
            if name == "Airforce":
                result = generate_image_airforce(prompt, negative, width, height)
            elif name == "Pollinations":
                result = generate_image_pollinations(prompt, width, height)
            elif name == "HuggingFace":
                result = generate_image_huggingface(prompt, width, height)
            else:
                continue
            
            increment_usage(name)
            result["remaining_quota"] = provider["daily_limit"] - used - 1
            return result
            
        except Exception as e:
            print(f"⚠️  {name} failed: {e}")
            increment_usage(name)  # ספירת ניסיון גם אם נכשל
            continue
    
    return {
        "error": "All free API providers exhausted",
        "usage": usage,
    }

# ============================================================
# Status
# ============================================================

def get_usage_status() -> dict:
    """מחזיר סטטוס שימוש יומי"""
    usage = load_usage()
    status = {}
    for provider in API_PROVIDERS:
        name = provider["name"]
        used = usage["providers"].get(name, 0)
        status[name] = {
            "used": used,
            "limit": provider["daily_limit"],
            "remaining": provider["daily_limit"] - used,
            "nsfw": provider["nsfw"],
            "quality": provider["quality"],
        }
    return status


if __name__ == "__main__":
    print("=== ShimiStudio Free API Fallback ===\n")
    
    status = get_usage_status()
    print("📊 Daily Usage:")
    for name, info in status.items():
        print(f"  {name}: {info['used']}/{info['limit']} used, {info['remaining']} remaining, NSFW={info['nsfw']}, Quality={info['quality']}")
    
    print("\n📸 Testing Pollinations (free, no auth)...")
    try:
        result = generate_image_pollinations("a cat sitting on a chair", 512, 512)
        print(f"✅ Success: {result['provider']} → {result['url']}")
    except Exception as e:
        print(f"❌ Failed: {e}")
