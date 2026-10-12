#!/usr/bin/env python3
# Shimi Dev — v2c driver: 16 קטעים × 81 פריימים, 3 שרשראות מקבילות על 2 סלוטים
import json, os, subprocess, sys, time, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from segments_v2c import prompt, NEG

USER = "bigshimi358"
KAGGLE = "/usr/local/bin/kaggle"
CHAIN = os.environ.get("CHAIN", "A")
ROSTER = {"A": [1, 4, 7, 10, 13, 16], "B": [2, 8, 11, 14], "C": [3, 9, 12, 15]}  # p05,p06 moved to colab

def run(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(os.path.join(BASE, f"driver_v2c_{CHAIN}.log"), "a") as f:
        f.write(line + "\n")

def slug(n): return f"shimi-poker-v2c-p{n:02d}"

def build(n):
    work = f"/tmp/poker-{slug(n)}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with open(os.path.join(BASE, "kernel_template.py")) as f:
        template = f.read()
    scene = {"id": f"p{n:02d}", "prompt": prompt(n), "neg": NEG, "frames": 81,
             "steps": (24 if n >= 11 else 20), "cfg": 5.0, "seed": 7, "w": 832, "h": 480}
    with open(os.path.join(work, "kernel.py"), "w") as f:
        f.write("SCENE = " + json.dumps(scene, ensure_ascii=False) + "\n" + template)
    meta = {"id": f"{USER}/{slug(n)}", "title": f"Shimi Poker V2c P{n:02d}",
            "code_file": "kernel.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "kernel_sources": [], "model_sources": [], "competition_sources": []}
    with open(os.path.join(work, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f)
    return work

def push(work, n):
    for attempt in range(60):
        r = run(KAGGLE, "kernels", "push", "-p", work)
        out = (r.stdout or "") + (r.stderr or "")
        if "successfully pushed" in out:
            return True
        if "session count" in out:
            if attempt % 4 == 3:
                log(f"p{n:02d}: slots full, waiting... ({attempt+1})")
            time.sleep(150)
        else:
            log(f"p{n:02d}: push failed: {out.strip()[:150]}")
            time.sleep(60)
    return False

def status(n):
    r = run(KAGGLE, "kernels", "status", f"{USER}/{slug(n)}")
    s = (r.stdout or r.stderr or "")
    for k in ("RUNNING", "COMPLETE", "ERROR", "QUEUED"):
        if k in s: return k
    return "UNKNOWN"

def extract_frames(n, outdir):
    mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
    if not mp4s: return False
    mp4 = os.path.join(outdir, mp4s[0])
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", mp4],
                        capture_output=True, text=True)
    try: nf = int(pr.stdout.strip())
    except Exception: return False
    B = chr(92)
    first, last = os.path.join(outdir, f"p{n:02d}_first.png"), os.path.join(outdir, f"p{n:02d}_last.png")
    ok1 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4,
                          "-vf", f"select=eq(n{B},0)", "-vframes", "1", first]).returncode == 0
    ok2 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4,
                          "-vf", f"select=eq(n{B},{nf-1})", "-vframes", "1", last]).returncode == 0
    return ok1 and ok2

def render(n):
    outdir = os.path.join(BASE, "out_v2c", f"p{n:02d}")
    if os.path.exists(os.path.join(outdir, "_report.json")):
        rep = json.loads(open(os.path.join(outdir, "_report.json")).read())
        if rep.get("frames") == 81 and not rep.get("black"):
            log(f"p{n:02d}: already done, skipping")
            return True
    for attempt in range(3):
        st = status(n)
        if st not in ("RUNNING", "QUEUED", "COMPLETE"):
            work = build(n)
            if not push(work, n):
                log(f"p{n:02d}: push gave up"); return False
            log(f"p{n:02d}: pushed (attempt {attempt+1})")
        # המתנה לסיום
        waited = 0
        while True:
            st = status(n)
            if st == "COMPLETE":
                time.sleep(20)
                os.makedirs(outdir, exist_ok=True)
                r = run(KAGGLE, "kernels", "output", f"{USER}/{slug(n)}", "-p", outdir)
                mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
                if mp4s:
                    ok = extract_frames(n, outdir)
                    log(f"p{n:02d}: COMPLETE, frames extracted: {ok}")
                    return ok
                log(f"p{n:02d}: complete but no mp4, retry")
                break
            if st == "ERROR":
                log(f"p{n:02d}: kernel ERROR, rebuild")
                break
            time.sleep(150); waited += 150
            if waited % 1200 == 0:
                log(f"p{n:02d}: still {st} ({waited//60} min)")
    return False

def main():
    log(f"chain {CHAIN} starting: {ROSTER[CHAIN]}")
    for n in ROSTER[CHAIN]:
        for attempt in range(3):
            if render(n):
                break
            log(f"p{n:02d}: attempt {attempt+1} failed, retrying")
        else:
            log(f"p{n:02d}: FAILED after 3 attempts")
    log(f"chain {CHAIN} done")

if __name__ == "__main__":
    main()
