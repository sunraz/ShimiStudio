# Shimi Dev — Wan2.2 TI2V-5B chained scene renderer (T4-safe dtypes, range-fix)
import os, json, subprocess, time, traceback, glob, urllib.request
subprocess.run(['pip','uninstall','-y','-q','torchao'], check=False)
subprocess.run(['pip','install','-q','-U','git+https://github.com/huggingface/diffusers.git','transformers>=4.51','accelerate','ftfy','protobuf','imageio','safetensors'], check=True)
import torch, numpy as np
from PIL import Image



# --- No-Filter Policy (permanent, Sun 18/10) --- איפוס פילטרים קבוע בכל פייפליין ---
def apply_no_filter(pipe):
    for attr, val in (("safety_checker", None), ("requires_safety_checker", False), ("feature_extractor", None)):
        if hasattr(pipe, attr):
            try: setattr(pipe, attr, val)
            except Exception: pass
    return pipe
# --- סוף איפוס פילטרים ---

t0 = time.time()
assert SCENE.get("prompt"), "SCENE injection failed!"
print("SCENE START", SCENE.get("id"), "| prompt:", SCENE["prompt"][:80], flush=True)
from diffusers import WanPipeline, AutoencoderKLWan, WanTransformer3DModel
from transformers import AutoTokenizer, UMT5EncoderModel
from diffusers.utils import export_to_video

MID = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
# T5 מקודד טקסט: bf16 על CPU — חוסך 6GB+ RAM, ללא בעיית ה-NaN של fp16
text_encoder = UMT5EncoderModel.from_pretrained(MID, subfolder="text_encoder", torch_dtype=torch.bfloat16)
tokenizer = AutoTokenizer.from_pretrained(MID, subfolder="tokenizer")
vae = AutoencoderKLWan.from_pretrained(MID, subfolder="vae", torch_dtype=torch.float32)
transformer = WanTransformer3DModel.from_pretrained(MID, subfolder="transformer", torch_dtype=torch.float16)
pipe = WanPipeline.from_pretrained(MID, text_encoder=text_encoder, tokenizer=tokenizer, vae=vae, transformer=transformer)
pipe = apply_no_filter(pipe)
pipe.enable_model_cpu_offload()
# קידוד פרומפט מוקדם על CPU, ואז שחרור מלא של מקודד הטקסט
import gc
with torch.no_grad():
    _pe = pipe.encode_prompt(prompt=SCENE["prompt"], negative_prompt=SCENE.get("neg", ""))
prompt_embeds, negative_embeds = _pe[0], _pe[1]
print("PROMPT ENCODED on cpu, freeing T5", flush=True)
pipe.text_encoder = None
gc.collect()
if hasattr(pipe, "enable_vae_tiling"): pipe.enable_vae_tiling()
print("LOADED", round(time.time()-t0, 1), "s", flush=True)

init = None
for p in glob.glob("/kaggle/input/**/init.png", recursive=True):
    init = Image.open(p).convert("RGB"); break
if SCENE.get("init_url") and init is None:
    q = "/kaggle/working/init.png"
    urllib.request.urlretrieve(SCENE["init_url"], q)
    init = Image.open(q).convert("RGB")

W, H = SCENE.get("w", 832), SCENE.get("h", 480)
kw = dict(prompt_embeds=prompt_embeds, negative_prompt_embeds=negative_embeds, height=H, width=W,
          num_frames=SCENE.get("frames", 49), guidance_scale=SCENE.get("cfg", 5.0),
          num_inference_steps=SCENE.get("steps", 16),
          generator=torch.Generator("cuda").manual_seed(SCENE.get("seed", 7)))
used = "t2v"
def do_render(nf):
    kw2 = dict(kw); kw2["num_frames"] = nf
    if init is not None:
        return pipe(image=init.resize((W, H)), **kw2)
    return pipe(**kw2)
FRAMES = SCENE.get("frames", 49)
try:
    out = do_render(FRAMES)
    if init is not None: used = "ti2v"
except Exception as e:
    print("render", FRAMES, "failed:", str(e)[:140], flush=True)
    gc.collect(); torch.cuda.empty_cache()
    if FRAMES > 81:
        print("retrying with 81 frames", flush=True)
        out = do_render(81)
    else:
        raise
print("RENDERED", used, round(time.time()-t0, 1), "s", flush=True)

frames = out.frames[0]
def mean255(f):
    a = np.asarray(f).astype("float32")
    if a.max() <= 1.5: a = a * 255.0
    return round(float(a.mean()), 1)
means = [mean255(f) for f in frames]
sid = SCENE.get("id", "scene")
export_to_video(frames, f"/kaggle/working/{sid}.mp4", fps=16)
def to_pil(f):
    a = np.asarray(f)
    if a.dtype != np.uint8:
        a = (a * 255.0).clip(0, 255).astype("uint8") if a.max() <= 1.5 else a.clip(0, 255).astype("uint8")
    return Image.fromarray(a)
to_pil(frames[0]).save(f"/kaggle/working/{sid}_first.png")
to_pil(frames[-1]).save(f"/kaggle/working/{sid}_last.png")
rep = {"id": sid, "mode": used, "frames": len(frames), "means": [means[0], means[len(means)//2], means[-1]],
       "seconds": round(time.time()-t0, 1), "black": min(means) < 3}
json.dump(rep, open("/kaggle/working/_report.json", "w"), indent=1)
print("DONE_SCENE", json.dumps(rep), flush=True)
