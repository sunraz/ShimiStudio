"""
ShimiStudio Free API Rotation System
Free API rotation system for image and video generation when local GPU resources are unavailable.
"""

import json
import os
import tempfile
import time
import urllib.parse
import uuid
from typing import Dict, List, Optional, Any
import requests


# ============================================================
# 1. API_PROVIDERS (7 Providers Sorted by Priority)
# ============================================================

API_PROVIDERS: List[Dict[str, Any]] = [
    {
        "name": "airforce",
        "type": "image",
        "daily_limit": 1000,
        "endpoint": "https://api.airforce/v1/images/generations",
        "requires_auth": False,
        "quality": "high",
        "nsfw": True,
        "priority": 1,
    },
    {
        "name": "pollinations",
        "type": "image",
        "daily_limit": 100,
        "endpoint": "https://image.pollinations.ai/prompt/",
        "requires_auth": False,
        "quality": "medium",
        "nsfw": True,
        "priority": 2,
    },
    {
        "name": "huggingface",
        "type": "image",
        "daily_limit": 50,
        "endpoint": "https://api-inference.huggingface.co/models",
        "requires_auth": True,
        "auth_key_env": "HF_TOKEN",
        "quality": "medium",
        "nsfw": True,
        "priority": 3,
    },
    {
        "name": "deepai",
        "type": "image",
        "daily_limit": 5,
        "endpoint": "https://api.deepai.org/api/generator.php",
        "requires_auth": True,
        "auth_key_env": "DEEPAI_API_KEY",
        "quality": "high",
        "nsfw": True,
        "priority": 4,
    },
    {
        "name": "pika",
        "type": "video",
        "daily_limit": 10,
        "endpoint": "https://api.pika.art/v1/videos",
        "requires_auth": True,
        "auth_key_env": "PIKA_API_KEY",
        "quality": "high",
        "nsfw": True,
        "priority": 5,
    },
    {
        "name": "runway",
        "type": "video",
        "daily_limit": 5,
        "endpoint": "https://api.runwayml.com/v1/generations",
        "requires_auth": True,
        "auth_key_env": "RUNWAY_API_KEY",
        "quality": "high",
        "nsfw": True,
        "priority": 6,
    },
    {
        "name": "synthesia",
        "type": "video",
        "daily_limit": 3,
        "endpoint": "https://api.synthesia.io/v1/videos",
        "requires_auth": True,
        "auth_key_env": "SYNTHESIA_API_KEY",
        "quality": "high",
        "nsfw": False,
        "priority": 7,
    },
]


# ============================================================
# 2. USAGE TRACKING
# ============================================================

USAGE_FILE = os.path.expanduser("~/.shimistudio/api_usage.json")


def load_usage() -> dict:
    """Loads daily API usage tracking from ~/.shimistudio/api_usage.json, resetting daily."""
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(USAGE_FILE):
        try:
            with open(USAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("date") == today:
                return data
        except Exception:
            pass
    return {"date": today, "providers": {}}


def save_usage(data: dict) -> None:
    """Saves daily API usage tracking data."""
    try:
        os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
        with open(USAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Failed to save usage data to {USAGE_FILE}: {e}")


def get_available_provider(provider_type: str = "image") -> Optional[dict]:
    """Finds the highest-priority available API provider for the given type ('image' or 'video')."""
    usage = load_usage()
    sorted_providers = sorted(API_PROVIDERS, key=lambda p: p["priority"])

    for provider in sorted_providers:
        if provider["type"] != provider_type:
            continue

        name = provider["name"]
        used = usage["providers"].get(name, 0)
        if used >= provider["daily_limit"]:
            continue

        if provider.get("requires_auth"):
            auth_env = provider.get("auth_key_env")
            if auth_env and not os.getenv(auth_env):
                continue

        return provider

    return None


def increment_usage(name: str) -> None:
    """Increments the daily usage counter for the given provider."""
    usage = load_usage()
    usage["providers"][name] = usage["providers"].get(name, 0) + 1
    save_usage(usage)


def _save_bytes_to_temp(content: bytes, ext: str = "png") -> str:
    """Helper function to save downloaded binary content to a temp directory and return local path."""
    temp_dir = os.path.join(tempfile.gettempdir(), "shimistudio")
    os.makedirs(temp_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return filepath


# ============================================================
# 3. INDIVIDUAL GENERATION FUNCTIONS
# ============================================================

def generate_image_airforce(
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """Generate image via Airforce API (1000/day, high quality, NSFW, priority 1)."""
    endpoint = "https://api.airforce/v1/images/generations"
    payload = {
        "prompt": prompt,
        "negative_prompt": negative,
        "width": width,
        "height": height,
        "n": 1,
    }

    response = requests.post(endpoint, json=payload, timeout=90)
    response.raise_for_status()
    data = response.json()

    img_url = None
    if isinstance(data, dict):
        if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            img_url = data["data"][0].get("url")
        elif "url" in data:
            img_url = data["url"]

    if not img_url:
        raise ValueError(f"Airforce API response missing image URL: {data}")

    # Download image to local temp directory
    dl_resp = requests.get(img_url, timeout=90)
    dl_resp.raise_for_status()
    filepath = _save_bytes_to_temp(dl_resp.content, "png")

    return {
        "provider": "airforce",
        "url": filepath,
        "width": width,
        "height": height,
    }


def generate_image_pollinations(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """Generate image via Pollinations API (100/day, medium quality, NSFW, priority 2). URL-based."""
    safe_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&nsfw=true"

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    filepath = _save_bytes_to_temp(response.content, "png")

    return {
        "provider": "pollinations",
        "url": filepath,
        "width": width,
        "height": height,
    }


def generate_image_huggingface(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """Generate image via HuggingFace Inference API (50/day, medium quality, NSFW, priority 3). Requires HF_TOKEN."""
    token = os.getenv("HF_TOKEN")
    if not token:
        raise ValueError("HF_TOKEN environment variable is not set")

    endpoint = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": width,
            "height": height,
        },
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()

    filepath = _save_bytes_to_temp(response.content, "png")

    return {
        "provider": "huggingface",
        "url": filepath,
        "width": width,
        "height": height,
    }


def generate_image_deepai(
    prompt: str,
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """Generate image via DeepAI API (5/day, high quality, NSFW, priority 4). Requires DEEPAI_API_KEY."""
    token = os.getenv("DEEPAI_API_KEY")
    if not token:
        raise ValueError("DEEPAI_API_KEY environment variable is not set")

    endpoint = "https://api.deepai.org/api/generator.php"
    headers = {"api-key": token}
    data = {
        "text": prompt,
        "width": str(width),
        "height": str(height),
    }

    response = requests.post(endpoint, headers=headers, data=data, timeout=90)
    response.raise_for_status()
    res_data = response.json()

    img_url = res_data.get("output_url")
    if not img_url:
        raise ValueError(f"DeepAI response missing output_url: {res_data}")

    dl_resp = requests.get(img_url, timeout=90)
    dl_resp.raise_for_status()
    filepath = _save_bytes_to_temp(dl_resp.content, "png")

    return {
        "provider": "deepai",
        "url": filepath,
        "width": width,
        "height": height,
    }


def generate_video_pika(prompt: str, duration: int = 5) -> dict:
    """Generate video via Pika API (10/day, high quality, NSFW, priority 5). Requires PIKA_API_KEY."""
    token = os.getenv("PIKA_API_KEY")
    if not token:
        raise ValueError("PIKA_API_KEY environment variable is not set")

    endpoint = "https://api.pika.art/v1/videos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "duration": duration,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    res_data = response.json()

    vid_url = res_data.get("video_url") or res_data.get("url")
    if not vid_url:
        raise ValueError(f"Pika API response missing video URL: {res_data}")

    dl_resp = requests.get(vid_url, timeout=120)
    dl_resp.raise_for_status()
    filepath = _save_bytes_to_temp(dl_resp.content, "mp4")

    return {
        "provider": "pika",
        "url": filepath,
        "duration": duration,
    }


def generate_video_runway(prompt: str, duration: int = 5) -> dict:
    """Generate video via Runway API (5/day, high quality, NSFW, priority 6). Requires RUNWAY_API_KEY."""
    token = os.getenv("RUNWAY_API_KEY")
    if not token:
        raise ValueError("RUNWAY_API_KEY environment variable is not set")

    endpoint = "https://api.runwayml.com/v1/generations"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "promptText": prompt,
        "duration": duration,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    res_data = response.json()

    output = res_data.get("output")
    vid_url = output[0] if isinstance(output, list) and len(output) > 0 else res_data.get("url")

    if not vid_url:
        raise ValueError(f"Runway API response missing video URL: {res_data}")

    dl_resp = requests.get(vid_url, timeout=120)
    dl_resp.raise_for_status()
    filepath = _save_bytes_to_temp(dl_resp.content, "mp4")

    return {
        "provider": "runway",
        "url": filepath,
        "duration": duration,
    }


def generate_video_synthesia(prompt: str, duration: int = 5) -> dict:
    """Generate video via Synthesia API (3/day, high quality, NSFW=False, priority 7). Requires SYNTHESIA_API_KEY."""
    token = os.getenv("SYNTHESIA_API_KEY")
    if not token:
        raise ValueError("SYNTHESIA_API_KEY environment variable is not set")

    endpoint = "https://api.synthesia.io/v1/videos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "script": prompt,
        "test": True,
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    res_data = response.json()

    vid_url = res_data.get("download_url") or res_data.get("url")
    if not vid_url:
        raise ValueError(f"Synthesia API response missing video URL: {res_data}")

    dl_resp = requests.get(vid_url, timeout=120)
    dl_resp.raise_for_status()
    filepath = _save_bytes_to_temp(dl_resp.content, "mp4")

    return {
        "provider": "synthesia",
        "url": filepath,
        "duration": duration,
    }


# ============================================================
# 4. MAIN ROTATION FUNCTIONS
# ============================================================

def generate_image_free(
    prompt: str,
    negative: str = "",
    width: int = 1024,
    height: int = 1024,
) -> dict:
    """
    Attempts image generation across free API providers in priority order.
    Falls back to the next available provider on failure.
    """
    usage = load_usage()
    image_providers = [p for p in API_PROVIDERS if p["type"] == "image"]
    image_providers.sort(key=lambda p: p["priority"])

    errors = []

    for provider in image_providers:
        name = provider["name"]
        used = usage["providers"].get(name, 0)

        if used >= provider["daily_limit"]:
            continue

        if provider.get("requires_auth"):
            auth_env = provider.get("auth_key_env")
            if auth_env and not os.getenv(auth_env):
                continue

        try:
            if name == "airforce":
                res = generate_image_airforce(prompt, negative, width, height)
            elif name == "pollinations":
                res = generate_image_pollinations(prompt, width, height)
            elif name == "huggingface":
                res = generate_image_huggingface(prompt, width, height)
            elif name == "deepai":
                res = generate_image_deepai(prompt, width, height)
            else:
                continue

            increment_usage(name)
            remaining = provider["daily_limit"] - (used + 1)
            res["remaining_quota"] = remaining
            return res

        except Exception as e:
            print(f"⚠️  Provider '{name}' failed: {e}. Falling back to next provider...")
            errors.append(f"{name}: {e}")
            increment_usage(name)
            continue

    raise RuntimeError(f"All available free image API providers failed or exhausted: {'; '.join(errors)}")


def generate_video_free(prompt: str, duration: int = 5) -> dict:
    """
    Attempts video generation across free API providers in priority order.
    Falls back to the next available provider on failure.
    """
    usage = load_usage()
    video_providers = [p for p in API_PROVIDERS if p["type"] == "video"]
    video_providers.sort(key=lambda p: p["priority"])

    errors = []

    for provider in video_providers:
        name = provider["name"]
        used = usage["providers"].get(name, 0)

        if used >= provider["daily_limit"]:
            continue

        if provider.get("requires_auth"):
            auth_env = provider.get("auth_key_env")
            if auth_env and not os.getenv(auth_env):
                continue

        try:
            if name == "pika":
                res = generate_video_pika(prompt, duration)
            elif name == "runway":
                res = generate_video_runway(prompt, duration)
            elif name == "synthesia":
                res = generate_video_synthesia(prompt, duration)
            else:
                continue

            increment_usage(name)
            remaining = provider["daily_limit"] - (used + 1)
            res["remaining_quota"] = remaining
            return res

        except Exception as e:
            print(f"⚠️  Video Provider '{name}' failed: {e}. Falling back...")
            errors.append(f"{name}: {e}")
            increment_usage(name)
            continue

    raise RuntimeError(f"All available free video API providers failed or exhausted: {'; '.join(errors)}")


# ============================================================
# 5. STATUS
# ============================================================

def get_usage_status() -> dict:
    """Returns a status dict showing usage, limits, remaining quotas, and properties for all providers."""
    usage = load_usage()
    status = {}

    for provider in API_PROVIDERS:
        name = provider["name"]
        used = usage["providers"].get(name, 0)
        limit = provider["daily_limit"]
        status[name] = {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "nsfw": provider["nsfw"],
            "quality": provider["quality"],
            "type": provider["type"],
            "priority": provider["priority"],
            "requires_auth": provider.get("requires_auth", False),
        }

    return status


if __name__ == "__main__":
    print("=== ShimiStudio Free API Rotation System ===\n")

    status = get_usage_status()
    print("📊 Current Usage Status:")
    for name, info in status.items():
        auth_str = "(Requires Auth)" if info["requires_auth"] else "(No Auth)"
        print(
            f"  - [{info['priority']}] {name:12s} ({info['type']}): {info['used']}/{info['limit']} used "
            f"({info['remaining']} remaining) | Quality={info['quality']} | NSFW={info['nsfw']} {auth_str}"
        )

    print("\n📸 Testing Pollinations Image Provider...")
    try:
        res = generate_image_pollinations("a majestic lion in the sunset", width=512, height=512)
        print(f"✅ Success via {res['provider']}: saved to {res['url']} ({res['width']}x{res['height']})")
    except Exception as e:
        print(f"❌ Pollinations test failed: {e}")
