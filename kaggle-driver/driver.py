#!/usr/bin/env python3
# Shimi Dev — autonomous chained poker-sequence driver (2 parallel chains)
import json, os, subprocess, sys, time, shutil, urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
LINGERIE = "https://base44.app/api/apps/6a901f55a4d9a9b76a095a77/files/mp/public/6a901f55a4d9a9b76a095a77/52bc48bff_s4_lingerie_anchor.png"
from scenes import prompt, NEG, ANCHOR_A, ANCHOR_B

USER = "bigshimi358"
KAGGLE = "/usr/local/bin/kaggle"

def run(*a, **k):
    return subprocess.run(list(a), capture_output=True, text=True, **k)

def log(m):
    line = f"[{time.strftime('%H:%M:%S')}] {m}"
    print(line, flush=True)
    with open(os.path.join(BASE, f"driver_{CHAIN}.log"), "a") as f:
        f.write(line + "\n")

def slug(n): return "shimi-poker-v2a-s1" if n == 1 else f"shimi-poker-v2b-s{n}"

def build_scene(n, init_src, init_is_url):
    work = f"/tmp/poker-{slug(n)}"
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    with open(os.path.join(BASE, "kernel_template.py")) as f:
        template = f.read()
    scene = {"id": f"s{n}", "prompt": prompt(n), "neg": NEG, "frames": 121,
             "steps": (26 if n >= 7 else 20), "cfg": 5.0, "seed": 7, "w": 832, "h": 480}
    prefix = "SCENE = " + json.dumps(scene, ensure_ascii=False) + "\n"
    with open(os.path.join(work, "kernel.py"), "w") as f:
        f.write(prefix + template)
    meta = {"id": f"{USER}/{slug(n)}", "title": f"Shimi Poker V2b S{n}",
            "code_file": "kernel.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True,
            "dataset_sources": [], "kernel_sources": [], "model_sources": [], "competition_sources": []}
    with open(os.path.join(work, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f)
    if init_src:
        dst = os.path.join(work, "init.png")
        if init_is_url:
            urllib.request.urlretrieve(init_src, dst)
        else:
            shutil.copy(init_src, dst)
    return work

def push(work, n):
    for attempt in range(40):
        r = run(KAGGLE, "kernels", "push", "-p", work)
        out = (r.stdout or "") + (r.stderr or "")
        if "successfully pushed" in out:
            return True
        if "session count" in out:
            log(f"s{n}: slots full, waiting... ({attempt+1})")
            time.sleep(150)
        else:
            log(f"s{n}: push failed: {out.strip()[:150]}")
            time.sleep(60)
    return False

def status(n):
    r = run(KAGGLE, "kernels", "status", f"{USER}/{slug(n)}")
    s = (r.stdout or r.stderr or "")
    if "RUNNING" in s: return "RUNNING"
    if "COMPLETE" in s: return "COMPLETE"
    if "ERROR" in s: return "ERROR"
    if "QUEUED" in s: return "QUEUED"
    return s.strip() or "UNKNOWN"

def pull(n, outdir):
    os.makedirs(outdir, exist_ok=True)
    r = run(KAGGLE, "kernels", "output", f"{USER}/{slug(n)}", "-p", outdir)
    files = [f for f in os.listdir(outdir)]
    return files

def scene_ok(outdir):
    mp4 = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
    if not mp4: return False
    rep = os.path.join(outdir, "_report.json")
    if os.path.exists(rep):
        try:
            r = json.loads(open(rep).read())
            if r.get("black"): return False
        except Exception: pass
    return True


def extract_last(n, outdir):
    """mp4 תקין → חלץ פריים ראשון+אחרון (דינמי לפי מספר פריימים) והחזר נתיב אחרון."""
    B = chr(92)  # באקסלש בלי כאבי רישות
    mp4s = [f for f in os.listdir(outdir) if f.endswith(".mp4")]
    if not mp4s: return None
    mp4 = os.path.join(outdir, mp4s[0])
    if os.path.getsize(mp4) < 50_000: return None
    pr = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-count_packets",
                         "-show_entries","stream=nb_read_packets","-of","csv=p=0",mp4],
                        capture_output=True, text=True)
    try: nf = int(pr.stdout.strip())
    except Exception: return None
    first, last = os.path.join(outdir, f"s{n}_first.png"), os.path.join(outdir, f"s{n}_last.png")
    ok1 = subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mp4,
                          "-vf",f"select=eq(n{B},0)","-vframes","1",first]).returncode == 0
    ok2 = subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mp4,
                          "-vf",f"select=eq(n{B},{nf-1})","-vframes","1",last]).returncode == 0
    if not (ok1 and ok2 and os.path.exists(last)): return None
    return last

def run_scene(n, init_src, init_is_url):
    outdir = os.path.join(BASE, "out", f"s{n}")
    for attempt in range(3):
        st0 = status(n)
        if st0 in ("RUNNING", "QUEUED"):
            log(f"s{n}: kernel already {st0}, polling instead of pushing")
        else:
            work = build_scene(n, init_src, init_is_url)
            if not push(work, n):
                log(f"s{n}: push gave up"); return None
            log(f"s{n}: pushed (attempt {attempt+1})")
        err_seen = 0
        for _ in range(240):
            st = status(n)
            if st == "COMPLETE": break
            if st == "ERROR":
                err_seen += 1
                if err_seen >= 2: break
            else:
                err_seen = 0
            time.sleep(60)
        st = status(n)
        log(f"s{n}: final status {st}")
        if st in ("COMPLETE", "ERROR"):
            files = pull(n, outdir)
            log(f"s{n}: pulled {files}")
            last_png = extract_last(n, outdir)
            if last_png:
                return last_png
            log(f"s{n}: no usable mp4, retrying")
        else:
            pull(n, outdir)
            log(f"s{n}: failed run, retrying")
        init_src, init_is_url = init_src, init_is_url
    return None

INITS = {1: ANCHOR_A, 2: ANCHOR_A, 3: ANCHOR_A,
         4: ANCHOR_B,
         5: LINGERIE, 6: LINGERIE, 7: LINGERIE, 8: LINGERIE, 9: LINGERIE, 10: LINGERIE}

def main(chain):
    import scenes as _sc
    scenes = CHAINS[chain]
    done = []
    log(f"chain {chain} starting, state-locked mode (no frame chaining)")
    for n in scenes:
        init_src, is_url = INITS[n], True
        outdir = os.path.join(BASE, 'out', f's{n}')
        if os.path.exists(os.path.join(outdir, f's{n}.mp4')) and scene_ok(outdir):
            log(f's{n}: already done, skipping')
            done.append(n)
            continue
        last = run_scene(n, init_src, is_url)
        if last is None:
            log(f"s{n}: FAILED after retries — continuing chain with previous init")
            continue
        done.append(n)
    log(f"CHAIN {chain} DONE: {done}")

CHAINS = {"A": [1, 2, 3], "B": [4, 5, 6], "C": [7, 8, 9, 10]}

CHAIN = sys.argv[1]
main(CHAIN)
