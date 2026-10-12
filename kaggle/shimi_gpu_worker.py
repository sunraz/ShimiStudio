# Shimi GPU worker v3 (12/10) — anchor image-to-video via Wan2.2 TI2V-5B (open repo) + T2V 1.3B
# Proven dtype recipe from shimi-poker-v2c kernels: UMT5 bfloat16, VAE fp32, transformer fp16,
# pre-encode prompt then free the text encoder (T4-safe).
import os, json, sys, traceback, gc, time, subprocess
subprocess.run(['pip', 'uninstall', '-y', '-q', 'torchao'])
subprocess.run(['pip', 'install', '-q', '-U', 'diffusers>=0.41.0', 'transformers', 'accelerate', 'imageio', 'safetensors', 'ftfy'])

import torch

QUEUE = json.loads(os.environ.get("WAN_QUEUE", "[]"))
while isinstance(QUEUE, str):
    QUEUE = json.loads(QUEUE)
OUT = "/kaggle/working"
os.makedirs(OUT, exist_ok=True)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
report = {"device": DEV, "gpu": torch.cuda.get_device_name(0) if DEV == "cuda" else None,
          "torch": torch.__version__, "rendered": [], "failed": [], "engine": None}
print("GPU WORKER v3 (T2V-1.3B + I2V-TI2V-5B)", report["gpu"], flush=True)

NEG_DEFAULT = "blurry, low quality, distorted, watermark, text, deformed, changing face, extra limbs, ugly, low resolution, jpeg artifacts"

import diffusers
from transformers import UMT5EncoderModel, AutoTokenizer
report["diffusers"] = diffusers.__version__

T2V_ID = "Wan-AI/Wan2.1-T2V-1.3B-Diffusers"
I2V_ID = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
PIPES = {}


def load_t2v():
    if "t2v" in PIPES:
        return PIPES["t2v"]
    from diffusers import WanPipeline
    pipe = WanPipeline.from_pretrained(T2V_ID, torch_dtype=torch.float16)
    if DEV == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(DEV)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    PIPES["t2v"] = pipe
    return pipe


def load_i2v():
    if "i2v" in PIPES:
        return PIPES["i2v"]
    from diffusers import WanImageToVideoPipeline, AutoencoderKLWan, WanTransformer3DModel
    text_encoder = UMT5EncoderModel.from_pretrained(I2V_ID, subfolder="text_encoder", torch_dtype=torch.bfloat16)
    tokenizer = AutoTokenizer.from_pretrained(I2V_ID, subfolder="tokenizer")
    vae = AutoencoderKLWan.from_pretrained(I2V_ID, subfolder="vae", torch_dtype=torch.float32)
    transformer = WanTransformer3DModel.from_pretrained(I2V_ID, subfolder="transformer", torch_dtype=torch.float16)
    pipe = WanImageToVideoPipeline.from_pretrained(
        I2V_ID, text_encoder=text_encoder, tokenizer=tokenizer, vae=vae, transformer=transformer)
    if DEV == "cuda":
        pipe.enable_model_cpu_offload()
    else:
        pipe.to(DEV)
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    PIPES["i2v"] = pipe
    return pipe


def load_anchor(url, size):
    import requests, io
    from PIL import Image
    r = requests.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGB")
    return im.resize(size)


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


def render_t2v(item):
    pipe = load_t2v()
    gen = torch.Generator(DEV).manual_seed(item.get("seed", 7))
    return pipe(
        prompt=item["prompt"],
        negative_prompt=item.get("negative", NEG_DEFAULT),
        num_frames=item.get("num_frames", 81),
        guidance_scale=item.get("cfg", 6.0),
        num_inference_steps=item.get("steps", 24),
        generator=gen,
        height=item.get("height", 480), width=item.get("width", 832),
        max_sequence_length=512,
    ).frames[0]


def render_i2v(item):
    pipe = load_i2v()
    W, H = item.get("width", 832), item.get("height", 480)
    anchor = load_anchor(item["image"], (W, H))
    # pre-encode prompt then free T5 (proven T4 memory strategy from v2c)
    with torch.no_grad():
        pe = pipe.encode_prompt(prompt=item["prompt"], negative_prompt=item.get("negative", NEG_DEFAULT))
    prompt_embeds, negative_embeds = pe[0], pe[1]
    if pipe.text_encoder is not None:
        pipe.text_encoder = None
    gc.collect()
    gen = torch.Generator(DEV).manual_seed(item.get("seed", 7))
    return pipe(
        image=anchor,
        prompt_embeds=prompt_embeds,
        negative_prompt_embeds=negative_embeds,
        height=H, width=W,
        num_frames=item.get("num_frames", 81),
        guidance_scale=item.get("cfg", 5.0),
        num_inference_steps=item.get("steps", 16),
        generator=gen,
        max_sequence_length=512,
    ).frames[0]


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
    report["engine"] = "t2v-1.3b + i2v-ti2v-5b-v3"
    for it in QUEUE:
        fid = it["id"]
        kind = "i2v" if it.get("image") else "t2v"
        try:
            t0 = time.time()
            raw = render_i2v(it) if kind == "i2v" else render_t2v(it)
            u8 = to_uint8(raw)
            means = frame_means(u8)
            if min(means) <= 8.0:
                raise RuntimeError(f"genuinely dark clip means={means}")
            fp = save(u8, fid)
            report["rendered"].append({"id": fid, "kind": kind, "file": os.path.basename(fp),
                                       "means_255": means, "sec": round(time.time() - t0),
                                       "bytes": os.path.getsize(fp), "frames": len(u8)})
            print("OK", fid, kind, means, os.path.getsize(fp), flush=True)
        except Exception:
            report["failed"].append({"id": fid, "kind": kind, "error": traceback.format_exc(limit=4)})
            print("FAIL", fid, kind, traceback.format_exc(limit=2), flush=True)
        gc.collect()
        if DEV == "cuda":
            torch.cuda.empty_cache()

    with open(f"{OUT}/_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("DONE", json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
