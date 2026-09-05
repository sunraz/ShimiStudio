import requests, time, json, os, sys, traceback, urllib.request, base64

cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
with open(cfg_path, encoding="utf-8-sig") as f:
    cfg = json.load(f)

TOKEN = cfg["token"]
NAME = cfg["name"]
API = cfg["apiBase"].rstrip("/")
COMFYUI = "http://127.0.0.1:8188"
STUDIO_API = "https://solas-6a095a77.base44.app/functions/shimiStudioAPI"

def post(fn, data, timeout=120):
    try:
        r = requests.post(f"{API}/functions/{fn}", json=data, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  API err: {e}")
        return {}

def studio_post(data, timeout=180):
    try:
        r = requests.post(STUDIO_API, json=data, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  Studio API err: {e}")
        return {}

def comfy_post(endpoint, data, timeout=300):
    try:
        r = requests.post(f"{COMFYUI}/{endpoint}", json=data, timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  ComfyUI err: {e}")
        return {}

def comfy_get(endpoint, timeout=30):
    try:
        r = requests.get(f"{COMFYUI}/{endpoint}", timeout=timeout)
        return r.json()
    except Exception as e:
        print(f"  ComfyUI err: {e}")
        return {}

def check_comfyui():
    try:
        r = requests.get(f"{COMFYUI}/system_stats", timeout=5)
        return r.status_code == 200
    except:
        return False

def upload_file(filepath):
    fname = os.path.basename(filepath)
    print(f"  Uploading {fname}...")
    try:
        with open(filepath, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        d = studio_post({"action": "upload_image", "image_data": data, "filename": fname}, timeout=180)
        if d.get("success") and d.get("url"):
            print(f"  Uploaded ({d.get('method','base44')}): {d['url']}")
            return d["url"]
        else:
            print(f"  Superagent: {d.get('error','failed')}")
    except Exception as e:
        print(f"  Superagent failed: {e}")
    
    for service, url_base in [("tmpfiles","https://tmpfiles.org/api/v1/upload"),("0x0.st","https://0x0.st"),("catbox","https://catbox.moe/user/api.php")]:
        try:
            with open(filepath, "rb") as f:
                if service == "catbox":
                    r = requests.post(url_base, data={"reqtype":"fileupload"}, files={"fileToUpload":(fname,f)}, timeout=120)
                    if r.status_code == 200 and r.text.strip().startswith("http"): return r.text.strip()
                elif service == "tmpfiles":
                    r = requests.post(url_base, files={"file":(fname,f)}, timeout=120)
                    if r.status_code == 200:
                        url = r.json().get("data",{}).get("url","").replace("tmpfiles.org/","tmpfiles.org/dl/")
                        if url: return url
                else:
                    r = requests.post(url_base, files={"file":(fname,f)}, timeout=120)
                    if r.status_code == 200 and r.text.strip().startswith("http"): return r.text.strip()
        except: pass
    return ""

def get_available_models():
    try:
        r = requests.get(f"{COMFYUI}/object_info/CheckpointLoaderSimple", timeout=10)
        d = r.json()
        models = d.get("CheckpointLoaderSimple",{}).get("input",{}).get("required",{}).get("ckpt_name",[[]])
        return models[0] if models and isinstance(models[0], list) else models
    except: return []

def get_available_loras():
    try:
        r = requests.get(f"{COMFYUI}/object_info/LoraLoader", timeout=10)
        d = r.json()
        loras = d.get("LoraLoader",{}).get("input",{}).get("required",{}).get("lora_name",[[]])
        return loras[0] if loras and isinstance(loras[0], list) else []
    except: return []

def pick_model(job=None):
    models = get_available_models()
    if job and isinstance(job, dict):
        jm = job.get("model","")
        if jm:
            for m in models:
                if jm.lower() in m.lower() or m.lower() in jm.lower(): return m
    for m in models:
        if any(x in m.lower() for x in ["cyber","realistic","dreamshaper","v1-5","sd15"]): return m
    return models[0] if models else "cyberrealistic_final.safetensors"

def download_reference_image(url, filepath):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            with open(filepath, "wb") as f: f.write(r.content)
            print(f"  Reference downloaded")
            return filepath
    except Exception as e:
        print(f"  Ref failed: {e}")
    return None

def generate_image(prompt, negative="", width=768, height=768, steps=25, reference_image=None, job=None):
    model_name = pick_model(job)
    print(f"  Model: {model_name}")
    is_sd15 = any(x in model_name.lower() for x in ["cyber","realistic","anything","dreamshaper","v1-5","sd15","aom3","orangemix"])
    if is_sd15:
        cfg=7.0; sampler="dpmpp_2m"; scheduler="karras"
        neg = "bad quality, low quality, blurry, deformed, ugly, bad anatomy"
        negative = (negative+", "+neg) if negative else neg
    else:
        cfg=1.0; sampler="euler"; scheduler="simple"

    wf = {}; nid=[0]
    def nid_(): nid[0]+=1; return str(nid[0])

    ckpt = nid_(); wf[ckpt] = {"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":model_name}}
    m=[ckpt,0]; c=[ckpt,1]; v=[ckpt,2]

    for lora in get_available_loras()[:3]:
        lid=nid_(); wf[lid]={"class_type":"LoraLoader","inputs":{"lora_name":lora,"strength_model":0.5,"strength_clip":0.5,"model":m,"clip":c}}
        m=[lid,0]; c=[lid,1]; print(f"  LoRA: {lora}")

    ref=None
    if reference_image and os.path.exists(reference_image):
        ci=os.path.join(os.path.dirname(os.path.abspath(__file__)),"ComfyUI","input"); os.makedirs(ci,exist_ok=True)
        rd=os.path.join(ci,"ref_temp.png")
        with open(reference_image,"rb") as s, open(rd,"wb") as d: d.write(s.read())
        li=nid_(); wf[li]={"class_type":"LoadImage","inputs":{"image":"ref_temp.png"}}; ref=[li,0]

    p=nid_(); wf[p]={"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":c}}
    n=nid_(); wf[n]={"class_type":"CLIPTextEncode","inputs":{"text":negative or "","clip":c}}

    if ref:
        ve=nid_(); wf[ve]={"class_type":"VAEEncode","inputs":{"pixels":ref,"vae":v}}
        l=nid_(); wf[l]={"class_type":"EmptyLatentImage","inputs":{"width":width,"height":height,"batch_size":1}}; li=[l,0]; dn=0.65
    else:
        l=nid_(); wf[l]={"class_type":"EmptyLatentImage","inputs":{"width":width,"height":height,"batch_size":1}}; li=[l,0]; dn=1.0

    s=nid_(); wf[s]={"class_type":"KSampler","inputs":{"seed":int(time.time())%1000000,"steps":steps,"cfg":cfg,"sampler_name":sampler,"scheduler":scheduler,"denoise":dn,"model":m,"positive":[p,0],"negative":[n,0],"latent_image":li}}
    vd=nid_(); wf[vd]={"class_type":"VAEDecode","inputs":{"samples":[s,0],"vae":v}}
    sv=nid_(); wf[sv]={"class_type":"SaveImage","inputs":{"images":[vd,0],"filename_prefix":"ShimiStudio"}}

    print(f"  ComfyUI: {len(wf)} nodes")
    r=comfy_post("prompt",{"prompt":wf})
    if "prompt_id" not in r: print(f"  Error: {r}"); return None
    pid=r["prompt_id"]; print(f"  Waiting ({pid})...")
    for i in range(120):
        time.sleep(3); h=comfy_get(f"history/{pid}")
        if pid in h:
            for _,no in h[pid].get("outputs",{}).items():
                if "images" in no and no["images"]:
                    fn=no["images"][0]["filename"]; sf=no["images"][0].get("subfolder","")
                    print(f"  Ready: {fn}")
                    local=os.path.join(os.path.dirname(os.path.abspath(__file__)),"output_temp.png")
                    urllib.request.urlretrieve(f"{COMFYUI}/view?filename={fn}&subfolder={sf}&type=output",local)
                    return local
    print("  Timeout"); return None

# === AnimateDiff Video v4.2 — AnimateDiffLoaderV1 עם כל השדות הנדרשים ===
def generate_video(prompt, negative="", width=512, height=512, frames=16, steps=20, job=None):
    model_name = pick_model(job)
    print(f"  Model: {model_name}")
    print(f"  AnimateDiff: mm_sd_v15_v2.ckpt, {frames} frames @ 8fps = {frames/8:.1f}s")

    is_sd15 = any(x in model_name.lower() for x in ["cyber","realistic","anything","dreamshaper","v1-5","sd15","aom3","orangemix"])
    if is_sd15:
        cfg=7.0; sampler="dpmpp_2m"; scheduler="karras"
        neg = "bad quality, low quality, blurry, deformed, flickering, watermark"
        negative = (negative+", "+neg) if negative else neg
    else:
        cfg=1.0; sampler="euler"; scheduler="simple"

    wf = {}; nid=[0]
    def nid_(): nid[0]+=1; return str(nid[0])

    # 1. Checkpoint
    ckpt=nid_(); wf[ckpt]={"class_type":"CheckpointLoaderSimple","inputs":{"ckpt_name":model_name}}
    m=[ckpt,0]; c=[ckpt,1]; v=[ckpt,2]

    # 2. LoRAs (max 2 for VRAM)
    for lora in get_available_loras()[:2]:
        lid=nid_(); wf[lid]={"class_type":"LoraLoader","inputs":{"lora_name":lora,"strength_model":0.4,"strength_clip":0.4,"model":m,"clip":c}}
        m=[lid,0]; c=[lid,1]; print(f"  LoRA: {lora} @ 0.4")

    # 3. EmptyLatentImage — לפני AnimateDiffLoaderV1 כי הוא דורש latents
    latent=nid_(); wf[latent]={"class_type":"EmptyLatentImage","inputs":{"width":width,"height":height,"batch_size":frames}}

    # 4. AnimateDiffLoaderV1 עם כל השדות הנדרשים
    ad=nid_(); wf[ad]={
        "class_type":"AnimateDiffLoaderV1",
        "inputs":{
            "model": m,
            "latents": [latent, 0],
            "model_name": "mm_sd_v15_v2.ckpt",
            "beta_schedule": "sqrt_linear (AnimateDiff)","unlimited_area_hack": False
        }
    }
    m=[ad,0]  # MODEL עם motion

    # 5. Prompts
    p=nid_(); wf[p]={"class_type":"CLIPTextEncode","inputs":{"text":prompt,"clip":c}}
    n=nid_(); wf[n]={"class_type":"CLIPTextEncode","inputs":{"text":negative or "","clip":c}}

    # 6. KSampler
    s=nid_(); wf[s]={"class_type":"KSampler","inputs":{"seed":int(time.time())%1000000,"steps":steps,"cfg":cfg,"sampler_name":sampler,"scheduler":scheduler,"denoise":1.0,"model":m,"positive":[p,0],"negative":[n,0],"latent_image":[latent,0]}}

    # 7. VAEDecode
    vd=nid_(); wf[vd]={"class_type":"VAEDecode","inputs":{"samples":[s,0],"vae":v}}

    # 8. SaveAnimatedWEBP
    sv=nid_(); wf[sv]={"class_type":"SaveAnimatedWEBP","inputs":{"images":[vd,0],"filename_prefix":"ShimiStudio","fps":8,"lossless":False,"quality":85,"method":"default"}}

    print(f"  ComfyUI: {len(wf)} nodes, {frames} frames")
    r=comfy_post("prompt",{"prompt":wf})
    if "prompt_id" not in r: print(f"  Error: {r}"); return None
    pid=r["prompt_id"]; print(f"  Rendering video ({pid})... ~3-5 min")
    for i in range(200):
        time.sleep(3); h=comfy_get(f"history/{pid}")
        if pid in h:
            for _,no in h[pid].get("outputs",{}).items():
                if "images" in no and no["images"]:
                    fn=no["images"][0]["filename"]; sf=no["images"][0].get("subfolder","")
                    print(f"  Video ready: {fn}")
                    local=os.path.join(os.path.dirname(os.path.abspath(__file__)),"output_video.webp")
                    urllib.request.urlretrieve(f"{COMFYUI}/view?filename={fn}&subfolder={sf}&type=output",local)
                    return local
    print("  Timeout (10 min)"); return None

# === MAIN ===
print("="*50)
print("  ShimiStudio Worker v4.2 - AnimateDiff Fix v2")
print("="*50)
print(f"  ComfyUI: {COMFYUI}")
print(f"  API: {API}")
print(f"  Upload: {STUDIO_API}")
print()

if not check_comfyui():
    print("  ComfyUI OFFLINE!"); sys.exit(1)

stats = comfy_get("system_stats")
dev = stats.get("system",{}).get("devices",[{}])[0]
print(f"  GPU: {dev.get('name','?')}")
print(f"  VRAM: {dev.get('vram_total',0)//(1024*1024)}MB")
print("  ComfyUI: ONLINE")

models = get_available_models()
loras = get_available_loras()
print(f"  Checkpoints: {models}")
print(f"  LoRAs: {loras}")
print()

post("workerApi",{"action":"register","token":TOKEN,"name":NAME,"os_type":"windows","gpu_model":"Quadro P2200","vram_total":5368578048,"checkpoints":models,"loras":loras})
print("  Registered\n")
studio_post({"action":"report_models","worker_id":NAME,"models":models,"loras":loras,"vram":5120})

while True:
    try:
        post("workerApi",{"action":"heartbeat","token":TOKEN,"status":"online","gpu_util":0,"vram_used":0,"ping_ms":10,"checkpoints":models,"loras":loras})
        r = post("jobApi",{"action":"claim","token":TOKEN})
        job = r.get("job")
        if job:
            jid=job.get("id","?"); jtype=job.get("type",job.get("job_type","image"))
            prompt=job.get("prompt",""); job_model=job.get("model","")
            job_lora=job.get("lora_path") or job.get("lora_url") or ""
            ref_url=job.get("source_image") or job.get("reference_image") or ""
            duration=job.get("duration",6)
            print(f"\n{'='*50}")
            print(f"  Job: {jid} | Type: {jtype}")
            print(f"  Prompt: {prompt[:80]}")
            if job_model: print(f"  Model: {job_model}")

            post("workerApi",{"action":"heartbeat","token":TOKEN,"status":"busy","current_job_type":jtype,"current_job_progress":0,"current_job_prompt":prompt[:80]})

            try:
                ref_path=None
                if ref_url and ref_url.startswith("http"):
                    ref_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),"ref_temp.png")
                    download_reference_image(ref_url,ref_path)

                path=None
                if jtype=="video":
                    frames=16
                    try:
                        path=generate_video(prompt,job.get("negative_prompt",""),512,512,frames,20,job)
                    except Exception as ve:
                        print(f"  Video error: {ve}")
                        print(f"  Retry with 8 frames...")
                        try: path=generate_video(prompt,job.get("negative_prompt",""),512,512,8,15,job)
                        except: path=None
                else:
                    path=generate_image(prompt,job.get("negative_prompt",""),reference_image=ref_path,job=job)

                if path:
                    url=upload_file(path)
                    if url:
                        print(f"  SUCCESS: {url}")
                        post("jobApi",{"action":"complete","job_id":jid,"result_url":url})
                    else:
                        post("jobApi",{"action":"fail","job_id":jid,"error":"Upload failed"})
                else:
                    post("jobApi",{"action":"fail","job_id":jid,"error":"Generation failed"})

                try:
                    if path and os.path.exists(path): os.remove(path)
                    if ref_path and os.path.exists(ref_path): os.remove(ref_path)
                except: pass
            except Exception as e:
                print(f"  ERROR: {e}"); traceback.print_exc()
                post("jobApi",{"action":"fail","job_id":jid,"error":str(e)})

            post("workerApi",{"action":"heartbeat","token":TOKEN,"status":"online","current_job_type":None,"current_job_progress":0,"checkpoints":models,"loras":loras})
            print(f"  Done: {jid}\n{'='*50}")
    except Exception as e:
        print(f"  Loop error: {e}")
    time.sleep(5)
