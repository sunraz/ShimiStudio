#!/usr/bin/env python3
# Shimi Dev — v2d driver: 20 קטעים × 81 פריימים (פיצול 10 הסצינות המקוריות), 3 שרשראות מקבילות
import json, os, subprocess, sys, time, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from segments_v2d import prompt, NEG, SEGMENTS

USER = "bigshimi358"
KAGGLE = "/usr/local/bin/kaggle"
CHAIN = os.environ.get("CHAIN", "A")
ROSTER = {"A": ["1a","1b","4a","4b","7a","7b","10a"],
          "B": ["2a","2b","5a","5b","8a","8b","10b"],
          "C": ["3a","3b","6a","6b"]}

def run(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(os.path.join(BASE, f"driver_v2d_{CHAIN}.log"), "a") as f:
        f.write(line + "\n")

def slug(seg): return f"shimi-poker-v2d-s{seg}"

def build(seg):
    work = f"/tmp/poker-{slug(seg)}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with open(os.path.join(BASE, "kernel_template.py")) as f:
        template = f.read()
    scene = {"id": f"s{seg}", "prompt": prompt(seg), "neg": NEG, "frames": 81,
             "steps": 20, "cfg": 5.0, "seed": 7, "w": 832, "h": 480}
    with open(os.path.join(work, "kernel.py"), "w") as f:
        f.write("SCENE = " + json.dumps(scene, ensure_ascii=False) + "\n" + template)
    meta = {"id": f"{USER}/{slug(seg)}", "title": f"Shimi Poker V2d S{seg}",
            "code_file": "kernel.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "kernel_sources": [], "model_sources": [], "competition_sources": []}
    with open(os.path.join(work, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f)
    return work

def push(work, seg):
    for attempt in range(60):
        r = run(KAGGLE, "kernels", "push", "-p", work)
        out = (r.stdout or "") + (r.stderr or "")
        if "successfully pushed" in out:
            return True
        if "session count" in out:
            if attempt % 4 == 3:
                log(f"s{seg}: slots full, waiting... ({attempt+1})")
            time.sleep(150)
        else:
            log(f"s{seg}: push failed: {out.strip()[:150]}")
            time.sleep(60)
    return False

def status(seg):
    r = run(KAGGLE, "kernels", "status", f"{USER}/{slug(seg)}")
    s = (r.stdout or r.stderr or "")
    for k in ("RUNNING", "COMPLETE", "ERROR", "QUEUED"):
        if k in s: return k
    return "UNKNOWN"

def extract_frames(seg, outdir):
    mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
    if not mp4s: return False
    mp4 = os.path.join(outdir, mp4s[0])
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets",
                         "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", mp4],
                        capture_output=True, text=True)
    try: nf = int(pr.stdout.strip())
    except Exception: return False
    B = chr(92)
    first, last = os.path.join(outdir, f"s{seg}_first.png"), os.path.join(outdir, f"s{seg}_last.png")
    ok1 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4,
                          "-vf", f"select=eq(n{B},0)", "-vframes", "1", first]).returncode == 0
    ok2 = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp4,
                          "-vf", f"select=eq(n{B},{nf-1})", "-vframes", "1", last]).returncode == 0
    return ok1 and ok2

def render(seg):
    outdir = os.path.join(BASE, "out_v2d", f"s{seg}")
    if os.path.exists(os.path.join(outdir, "_report.json")):
        rep = json.loads(open(os.path.join(outdir, "_report.json")).read())
        if rep.get("frames") == 81 and not rep.get("black"):
            log(f"s{seg}: already done, skipping")
            return True
    for attempt in range(3):
        st = status(seg)
        if st not in ("RUNNING", "QUEUED", "COMPLETE"):
            work = build(seg)
            if not push(work, seg):
                log(f"s{seg}: push gave up"); return False
            log(f"s{seg}: pushed (attempt {attempt+1})")
        waited = 0
        while True:
            st = status(seg)
            if st == "COMPLETE":
                time.sleep(20)
                os.makedirs(outdir, exist_ok=True)
                r = run(KAGGLE, "kernels", "output", f"{USER}/{slug(seg)}", "-p", outdir)
                mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
                if mp4s:
                    ok = extract_frames(seg, outdir)
                    log(f"s{seg}: COMPLETE, frames extracted: {ok}")
                    return ok
                log(f"s{seg}: complete but no mp4, retry")
                break
            if st == "ERROR":
                log(f"s{seg}: kernel ERROR, rebuild")
                break
            time.sleep(150); waited += 150
            if waited % 1200 == 0:
                log(f"s{seg}: still {st} ({waited//60} min)")
    return False

def main():
    log(f"chain {CHAIN} starting: {ROSTER[CHAIN]}")
    for seg in ROSTER[CHAIN]:
        for attempt in range(3):
            if render(seg):
                break
            log(f"s{seg}: attempt {attempt+1} failed, retrying")
        else:
            log(f"s{seg}: FAILED after 3 attempts")
    log(f"chain {CHAIN} done")

if __name__ == "__main__":
    main()
