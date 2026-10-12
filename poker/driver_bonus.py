#!/usr/bin/env python3
# Shimi Dev — bonus dance segments b1/b2 (v2b style: 121 frames, 7.5s, lace, friend)
# Appends to the full movie: s1..s10 + b1 + b2
import json, os, subprocess, sys, time, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
from scenes import ID_BASE, CORE, MOTION, DANCE_CONSISTENCY, NEG

USER = "bigshimi358"
KAGGLE = "/usr/local/bin/kaggle"
ANCHOR = "https://base44.app/api/apps/6a901f55a4d9a9b76a095a77/files/mp/public/6a901f55a4d9a9b76a095a77/815a6f04a_anchor_s10_last.png"

BONUS = {
 "b1": "steps up beside her friend's chair and dances a slow teasing dance, one hand resting on the back of the chair, hips circling in rhythm, her long black hair swinging with each sway, her friend clapping to the beat",
 "b2": "steps into the warm pool of lamplight and dances freely with her arms raised above her head then flowing down her sides, hips rolling smoothly, turning slowly in place, both women laughing",
}

def bprompt(k):
    state = "She wears a black lace bra and matching black lace panties. "
    return (ID_BASE + CORE + "She loses the hand, reacts in amused disbelief, then she " + BONUS[k] + ". "
            + "Her friend laughs and pulls the chips toward herself. " + state + MOTION + DANCE_CONSISTENCY)

def run(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(os.path.join(BASE, "driver_bonus.log"), "a") as f:
        f.write(line + "\n")

def slug(k): return f"shimi-poker-v2b-{k}"

def build(k):
    work = f"/tmp/poker-{slug(k)}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with open(os.path.join(BASE, "kernel_template.py")) as f:
        template = f.read()
    scene = {"id": k, "prompt": bprompt(k), "neg": NEG, "frames": 121,
             "steps": 26, "cfg": 5.0, "seed": 7, "w": 832, "h": 480, "init_url": ANCHOR}
    with open(os.path.join(work, "kernel.py"), "w") as f:
        f.write("SCENE = " + json.dumps(scene, ensure_ascii=False) + "\n" + template)
    meta = {"id": f"{USER}/{slug(k)}", "title": f"Shimi Poker V2b {k.upper()}",
            "code_file": "kernel.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "kernel_sources": [], "model_sources": [], "competition_sources": []}
    with open(os.path.join(work, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f)
    return work

def push(work, k):
    for attempt in range(40):
        r = run(KAGGLE, "kernels", "push", "-p", work)
        out = (r.stdout or "") + (r.stderr or "")
        if "successfully pushed" in out:
            return True
        if "session count" in out:
            log(f"{k}: slots full, waiting... ({attempt+1})")
            time.sleep(150)
        else:
            log(f"{k}: push failed: {out.strip()[:150]}")
            time.sleep(60)
    return False

def status(k):
    r = run(KAGGLE, "kernels", "status", f"{USER}/{slug(k)}")
    s = (r.stdout or r.stderr or "")
    for st in ("RUNNING", "COMPLETE", "ERROR", "QUEUED"):
        if st in s: return st
    return s.strip() or "UNKNOWN"

def pull(k, outdir):
    os.makedirs(outdir, exist_ok=True)
    run(KAGGLE, "kernels", "output", f"{USER}/{slug(k)}", "-p", outdir)
    return os.listdir(outdir)

def extract_frames(k, outdir):
    B = chr(92)
    mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
    if not mp4s: return False
    mp4 = os.path.join(outdir, mp4s[0])
    if os.path.getsize(mp4) < 50_000: return False
    pr = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-count_packets",
                         "-show_entries","stream=nb_read_packets","-of","csv=p=0",mp4],
                        capture_output=True, text=True)
    try: nf = int(pr.stdout.strip())
    except Exception: return False
    for name, n in ((f"{k}_first.png", 0), (f"{k}_last.png", nf-1)):
        rc = subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mp4,
                             "-vf",f"select=eq(n{B},{n})","-vframes","1",
                             os.path.join(outdir,name)]).returncode
        if rc != 0: return False
    log(f"{k}: frames extracted ({nf} frames)")
    return True

def render(k):
    outdir = os.path.join(BASE, "out_v2b", k)
    for attempt in range(3):
        st0 = status(k)
        if st0 not in ("RUNNING", "QUEUED"):
            work = build(k)
            if not push(work, k):
                log(f"{k}: push gave up"); return False
            log(f"{k}: pushed (attempt {attempt+1})")
        err_seen = 0
        for _ in range(240):
            st = status(k)
            if st == "COMPLETE": break
            if st == "ERROR":
                err_seen += 1
                if err_seen >= 2: break
            else:
                err_seen = 0
            time.sleep(60)
        if st != "COMPLETE":
            log(f"{k}: ended with status {st}"); time.sleep(30); continue
        pull(k, outdir)
        files = os.listdir(outdir)
        mp4 = [f for f in files if f.endswith(".mp4")]
        rep = os.path.join(outdir, "_report.json")
        black = False
        if os.path.exists(rep):
            try:
                r = json.loads(open(rep).read())
                black = bool(r.get("black"))
            except Exception: pass
        if mp4 and not black and extract_frames(k, outdir):
            log(f"{k}: DONE")
            return True
        log(f"{k}: output invalid (mp4={bool(mp4)}, black={black}), retrying")
    return False

def main():
    log("bonus driver starting: ['b1','b2']")
    done = {}
    # push both (parallel on 2 slots)
    for k in ("b1", "b2"):
        st0 = status(k)
        if st0 not in ("RUNNING", "QUEUED"):
            work = build(k)
            if push(work, k):
                log(f"{k}: pushed")
        else:
            log(f"{k}: already {st0}")
    # poll both until done
    remaining = {"b1", "b2"}
    while remaining:
        for k in list(remaining):
            st = status(k)
            if st == "COMPLETE":
                outdir = os.path.join(BASE, "out_v2b", k)
                pull(k, outdir)
                files = os.listdir(outdir)
                mp4 = [f for f in files if f.endswith(".mp4")]
                rep = os.path.join(outdir, "_report.json")
                black = False
                if os.path.exists(rep):
                    try:
                        r = json.loads(open(rep).read())
                        black = bool(r.get("black"))
                    except Exception: pass
                if mp4 and not black and extract_frames(k, outdir):
                    log(f"{k}: DONE")
                    remaining.discard(k)
                else:
                    log(f"{k}: output invalid, re-pushing")
                    work = build(k)
                    push(work, k)
            elif st == "ERROR":
                log(f"{k}: ERROR, re-pushing")
                work = build(k)
                push(work, k)
        time.sleep(60)
    log("ALL BONUS DONE")

if __name__ == "__main__":
    main()
