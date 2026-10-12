# Shimi GPU worker v2 (Sun approval 12/10) — anchor image-to-video support
# Base: shimi-dev-physics.py (range fix verified 12/10). New: WanImageToVideoPipeline when job has "image".
import os, json, sys, traceback, gc, time, subprocess
subprocess.run(['pip', 'uninstall', '-y', '-q', 'torchao'])
subprocess.run(['pip', 'install', '-q', '-U', 'diffusers>=0.33.0', 'transformers', 'accelerate', 'imageio', 'safetensors'])

import torch

QUEUE = json.loads(os.environ.get("WAN_QUEUE", "[]"))
while isinstance(QUEUE, str):
    QUEUE = json.loads(QUEUE)
OUT = "/kaggle/working"
os.makedirs(OUT, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
report = {"device": DEV, "gpu": torch.cuda.get_device_name(0) if DEV == "cuda" else None,
          "torch": torch.__version__, "rendered": [], "failed": [], "probes": [], "engine": None}
print("GPU WORKER v2 (T2V+I2V)", report["gpu"], flush=True)

NEG_DEFAULT = "blurry, low quality, distorted, watermark, text, deformed, changing face, extra limbs, ugly, low resolution, jpeg artifacts"

import diffusers
from diffusers import WanPipeline, WanImageToVideoPipeline
T2V_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
I2V_ID = "Wan-AI/Wan2.1-I2V-1.3B-Diffusers"
report["diffusers"] = diffusers.__version__
PIPES = {}

def load_pipe(kind):
    if kind in PIPES:
        return PIPES[kind]
    cls, mid = (WanPipeline, T2V_ID) if kind == "t2v" else (WanImageToVideoPipeline, I2V_ID)
    pipe = cls.from_pretrained(mid, torch_dtype=torch.float16)
    if DEV == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(DEV)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    PIPES[kind] = pipe
    return pipe

def load_anchor(url, size):
    import requests, io
    from PIL import Image
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    im = im.resize(size)  # (width, height) — must match pipeline width/height
    return im

def to_uint8(frames):
    import numpy as np
    out = []
    for f in frames:
        a = f.cpu() if hasattr(f, "cpu") else f
        if hasattr(a, "numpy"):
            a = a.numpy()
        a = np.asarray(a)
        if a.dtype.kind == 'f':
            if a.max() <= 1.5:
                a = (np.clip(a, 0, 1) * 255).astype(np.uint8)
            else:
                a = np.clip(a, 0, 255).astype(np.uint8)
        else:
            a = a.astype(np.uint8)
        if a.ndim == 4:
            a = a[0]
        if a.shape[-1] == 4:
            a = a[..., :3]
        out.append(a)
    return out

def frame_means(u8frames):
    import numpy as np
    means = []
    for idx in (0, len(u8frames) // 2, len(u8frames) - 1):
        means.append(round(float(np.asarray(u8frames[idx], dtype=np.float32).mean()), 1))
    return means

def render(item):
    # 81 frames locked (5.06s). dims default 480x832 (matches anchor assets)
    w = item.get("width", 832); h = item.get("height", 480)
    gen = torch.Generator(DEV).manual_seed(item.get("seed", 7))
    kind = "i2v" if item.get("image") else "t2v"
    pipe = load_pipe(kind)
    kw = dict(
        prompt=item["prompt"],
        negative_prompt=item.get("negative", NEG_DEFAULT),
        num_frames=item.get("num_frames", 81),
        guidance_scale=item.get("cfg", 6.0),
        num_inference_steps=item.get("steps", 24),
        generator=gen,
        height=h, width=w,
        max_sequence_length=512,
    )
    if kind == "i2v":
        kw["image"] = load_anchor(item["image"], (w, h))
    return pipe(**kw).frames[0]

def save(u8frames, fid):
    import imageio
    fp = f"{OUT}/{fid}.mp4"
    imageio.mimwrite(fp, u8frames, fps=16, quality=8)
    from PIL import Image
    Image.fromarray(u8frames[0]).save(f"{OUT}/{fid}_f0.png")
    Image.fromarray(u8frames[-1]).save(f"{OUT}/{fid}_fend.png")
    Image.fromarray(u8frames[len(u8frames) // 2]).save(f"{OUT}/{fid}_mid.png")
    return fp

def main():
    report["engine"] = "wan21-13b-t2v+i2v-v2"
    probe = {"id": "probe", "prompt": "A golden retriever puppy running on a sunny beach, waves behind it, photorealistic",
             "seed": 7, "num_frames": 17, "steps": 8, "cfg": 6.0}
    t0 = time.time()
    u8 = to_uint8(render(probe))
    means = frame_means(u8)
    ok = min(means) > 8.0
    report["probes"].append({"raw": means, "ok": ok, "sec": round(time.time() - t0)})
    print("PROBE means255:", means, "ok:", ok, flush=True)
    if not ok:
        raise RuntimeError("probe dark: " + json.dumps(report["probes"]))

    for it in QUEUE:
        fid = it["id"]
        try:
            t0 = time.time()
            raw = render(it)
            u8 = to_uint8(raw)
            means = frame_means(u8)
            if min(means) <= 8.0:
                raise RuntimeError(f"genuinely dark clip means={means}")
            fp = save(u8, fid)
            report["rendered"].append({"id": fid, "kind": "i2v" if it.get("image") else "t2v",
                                       "file": os.path.basename(fp), "means_255": means,
                                       "sec": round(time.time() - t0), "bytes": os.path.getsize(fp)})
            print("OK", fid, means, os.path.getsize(fp), flush=True)
        except Exception:
            report["failed"].append({"id": fid, "error": traceback.format_exc(limit=4)})
            print("FAIL", fid, traceback.format_exc(limit=2), flush=True)
        gc.collect()
        if DEV == "cuda":
            torch.cuda.empty_cache()

    with open(f"{OUT}/_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("DONE", json.dumps(report, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
