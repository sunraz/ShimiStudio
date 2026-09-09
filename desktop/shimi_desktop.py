#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ShimiStudio Desktop v1.0 — UI עצמאי לרשת שימי (Windows / Mac)
רינדור וידאו/תמונה מכל מנוע: ענן (Wan 2.2 — קולאב/קגל) או מקומי (AnimateDiff).
רץ מקומי על http://localhost:8787 — בלי תלות באתר. Python 3 + requests בלבד.

הפעלה:  python shimi_desktop.py   (פותח דפדפן אוטומטית)
"""
import json, os, sys, subprocess, threading, time, webbrowser, socketserver
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
CONF_PATH = os.path.join(HERE, "config.json")
PORT = 8787
API_DEFAULT = "https://shimi-studio.base44.app/api/apps/6a9206e9f29b8d9f70a77b47"
CLOUD_LINKS = [
    ("קולאב — GPU חינם T4", "https://github.com/sunraz/ShimiStudio/blob/main/cloud/shimi_cloud_worker_colab.ipynb"),
    ("קגל — GPU חינם T4", "https://github.com/sunraz/ShimiStudio/blob/main/cloud/shimi_cloud_worker_kaggle.ipynb"),
]

def load_cfg():
    cfg = {}
    if os.path.exists(CONF_PATH):
        try:
            cfg = json.load(open(CONF_PATH, encoding="utf-8-sig"))
        except Exception:
            pass
    api = cfg.get("apiBase") or API_DEFAULT
    return {
        "api": api,
        "token": cfg.get("token", ""),
        "name": cfg.get("name", "ShimiStudio Desktop"),
        "comfy_path": cfg.get("comfyui_path", os.path.join(HERE, "ComfyUI")),
        "comfy_url": cfg.get("comfyui_url", "http://127.0.0.1:8188"),
        "wan": (cfg.get("wan") or {}),
        "has_comfy": os.path.exists(cfg.get("comfyui_path", os.path.join(HERE, "ComfyUI"))),
    }

CFG = load_cfg()
WORKER_PROC = {"proc": None}

def api_post(fn, payload, timeout=30):
    try:
        r = requests.post(f"{CFG['api']}/functions/{fn}", json=payload, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

def local_worker_running():
    p = WORKER_PROC.get("proc")
    return bool(p and p.poll() is None)

def local_comfy_up():
    try:
        return requests.get(CFG["comfy_url"] + "/system_stats", timeout=3).status_code == 200
    except Exception:
        return False

# ─────────────────────────── UI ───────────────────────────
HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl"><head><meta charset="utf-8">
<title>Shimi Studio</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root{--bg:#0e0c0a;--card:#171310;--card2:#1f1a15;--gold:#e8c87a;--gold2:#c9a45c;
--text:#f0e9dd;--mut:#9a8f7d;--ok:#7ec98f;--err:#e07a6a;--b:#2a221a}
*{box-sizing:border-box;margin:0}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh}
header{display:flex;align-items:center;gap:14px;padding:18px 28px;border-bottom:1px solid var(--b);background:linear-gradient(180deg,#161210,#0e0c0a)}
.logo{width:42px;height:42px;border-radius:12px;background:linear-gradient(135deg,var(--gold),#8a6a35);display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:800;color:#1a1408}
h1{font-size:19px;font-weight:600;letter-spacing:.4px}
h1 small{color:var(--mut);font-weight:400;font-size:12px;margin-inline-start:8px}
.dot{width:9px;height:9px;border-radius:50%;background:var(--mut);display:inline-block;margin-inline-end:6px}
.dot.on{background:var(--ok);box-shadow:0 0 8px var(--ok)}
nav{display:flex;gap:4px;padding:10px 28px 0;border-bottom:1px solid var(--b)}
nav button{background:none;border:none;color:var(--mut);font-size:14px;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit}
nav button.act{color:var(--gold);border-bottom-color:var(--gold)}
main{max-width:1080px;margin:0 auto;padding:26px 28px 60px}
.tab{display:none}.tab.act{display:block}
.card{background:var(--card);border:1px solid var(--b);border-radius:14px;padding:20px;margin-bottom:16px}
.card h3{font-size:14px;color:var(--gold);margin-bottom:12px;letter-spacing:.5px}
label{display:block;font-size:12px;color:var(--mut);margin:12px 0 5px}
textarea,input[type=text],input[type=number],input[type=password],select{width:100%;background:var(--card2);border:1px solid var(--b);color:var(--text);border-radius:9px;padding:10px 12px;font-size:14px;font-family:inherit}
textarea{min-height:110px;resize:vertical}
textarea:focus,input:focus,select:focus{outline:none;border-color:var(--gold2)}
.row{display:flex;gap:12px;flex-wrap:wrap}
.row>*{flex:1;min-width:150px}
.engines{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}
.eng{background:var(--card2);border:1.5px solid var(--b);border-radius:11px;padding:12px 14px;cursor:pointer;transition:.15s}
.eng:hover{border-color:var(--gold2)}
.eng.sel{border-color:var(--gold);background:linear-gradient(180deg,#221b12,#171310)}
.eng b{font-size:14px}.eng span{display:block;font-size:11px;color:var(--mut);margin-top:3px}
.badge{font-size:10px;padding:2px 8px;border-radius:20px;background:#2a2318;color:var(--gold);display:inline-block;margin-inline-start:6px;vertical-align:2px}
.badge.loc{background:#18222a;color:#7ab8d4}
.btn{background:linear-gradient(135deg,var(--gold),var(--gold2));color:#1a1408;border:none;border-radius:10px;padding:12px 26px;font-size:15px;font-weight:700;cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.45;cursor:default}
.btn.ghost{background:none;border:1px solid var(--gold2);color:var(--gold)}
.btn.small{padding:6px 14px;font-size:12px;font-weight:500}
#msg{margin-top:12px;font-size:13px;min-height:20px}
#msg.ok{color:var(--ok)}#msg.err{color:var(--err)}
table{width:100%;border-collapse:collapse;font-size:13px}
th{color:var(--mut);font-weight:400;text-align:right;padding:8px 6px;border-bottom:1px solid var(--b);font-size:11px}
td{padding:10px 6px;border-bottom:1px solid #201913}
.st{padding:2px 10px;border-radius:20px;font-size:11px}
.st.pending{background:#2a2113;color:var(--gold)}.st.rendering{background:#16242a;color:#7ab8d4}
.st.completed{background:#152318;color:var(--ok)}.st.failed,.st.cancelled{background:#2a1512;color:var(--err)}
video,img.res{width:100%;max-width:260px;border-radius:10px;margin-top:6px;background:#000}
.wcard{background:var(--card2);border:1px solid var(--b);border-radius:11px;padding:14px;margin-bottom:10px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.wcard .nm{font-weight:600}.wcard small{color:var(--mut)}
.links a{color:var(--gold);text-decoration:none;border-bottom:1px dotted var(--gold2)}
.hint{font-size:11px;color:var(--mut);margin-top:5px;line-height:1.6}
.pill{display:inline-block;background:var(--card2);border:1px solid var(--b);border-radius:9px;padding:8px 12px;margin:3px;font-size:12px}
.pill b{color:var(--gold)}
@media(max-width:640px){.row>*{min-width:100%}}
</style></head><body>
<header>
 <div class="logo">ש</div>
 <h1>Shimi Studio <small>דסקטופ v1.0 — כל המנועים ביד אחת</small></h1>
 <div style="margin-inline-start:auto;font-size:12px">
   <span class="dot" id="hdot"></span>ענן
   <span class="dot" id="ldot" style="margin-inline-start:14px"></span>מקומי
 </div>
</header>
<nav>
 <button class="act" data-t="create">יצירה</button>
 <button data-t="queue">תור</button>
 <button data-t="workers">עובדים ומנועים</button>
 <button data-t="loras">לורות</button>
</nav>
<main>

<div class="tab act" id="t-create"><div class="card">
 <h3>צור וידאו</h3>
 <label>פרומפט — שוט אחד או רצף. לרצף: הפרד שוטים בשורה חדשה שמתחילה ב- / SHOT 2:</label>
 <textarea id="prompt" placeholder="בחורה רוקדת במועדון, תאורה סגולה, מצלמה עוקבת&#10;/ SHOT 2: היא מסתובבת אל המצלמה ומחייכת"></textarea>
 <label>נגטיב (רשות)</label>
 <input type="text" id="neg" placeholder="רשות — ישמש ברירת מחדל אם ריק">
 <div class="row">
  <div><label>מנוע</label><select id="engine"></select></div>
  <div><label>פורמט</label><select id="ar">
    <option value="9:16">אנכי 9:16 — רילס/טיקטוק</option>
    <option value="2:3">אנכי 2:3 — 1080x1600 (לנה)</option>
    <option value="16:9">אופקי 16:9 — יוטיוב</option>
    <option value="1:1">ריבוע 1:1</option></select></div>
  <div><label>אורך כולל (שניות)</label><input type="number" id="dur" value="15" min="3" max="180"></div>
 </div>
 <div style="margin-top:18px"><button class="btn" id="go" onclick="submitJob()">הגש לתור</button>
 <span id="msg"></span></div>
 <div class="hint">שרשור שוטים (I2V) + גימור 1080x1600@30fps פועלים אוטומטית ברצף של Wan 2.2 בענן.</div>
</div></div>

<div class="tab" id="t-queue"><div class="card">
 <h3>תור רינדור</h3>
 <table><thead><tr><th>פרומפט</th><th>מנוע</th><th>סטטוס</th><th>התקדמות</th><th></th></tr></thead>
 <tbody id="jobs"></tbody></table>
 <div class="hint">רינדורים נשמרים במדיה של הסטודיו — ניתן לפתוח את התוצאה בלחיצה.</div>
</div></div>

<div class="tab" id="t-workers"><div class="card">
 <h3>עובדים חיים</h3><div id="workers">טוען…</div>
</div>
<div class="card"><h3>הפעלת ענן חינם — בלי התקנה מקומית</h3>
 <div class="hint">מנועי הענן (Wan 2.2) רצים במחברות GPU חינמיות. פתח, הרץ את כל התאים לפי הסדר — העובד נרשם לבד לתור שלנו עם תוקף סשן:</div>
 <div class="links" id="clinks" style="margin-top:10px"></div>
 <div class="hint" style="margin-top:8px">קולאב ≈ 11 שעות, קגל ≈ 8 שעות. המודלים נשמרים ב-Drive שלך (קולאב) — הרצות הבאות עולות בדקות.</div>
</div>
<div class="card" id="localcard"><h3>עובד מקומי</h3>
 <div id="localstatus" class="hint"></div>
 <div style="margin-top:10px">
  <button class="btn ghost small" id="wkbtn" onclick="toggleWorker()">הפעל עובד מקומי</button>
 </div>
</div></div>

<div class="tab" id="t-loras"><div class="card">
 <h3>לורות מקומיים</h3><div id="loralist" class="hint">טוען…</div>
</div>
<div class="card"><h3>הורדת LoRA</h3>
 <div class="row">
  <div><label>מזהה CivitAI (מספר) או קישור ישיר</label><input type="text" id="loraurl" placeholder="1234567 או https://civitai.com/..."></div>
  <div><label>מפתח CivitAI (נשמר מקומית בלבד)</label><input type="password" id="civtoken" placeholder="civitai api key"></div>
 </div>
 <div style="margin-top:12px"><button class="btn small" onclick="dlLora()">הורד לורה</button> <span id="lmsg" class="hint"></span></div>
 <div class="hint">LoRA ל-Wan 2.2 נטען אוטומטית ברינדורי ענן דרך ה-Drive (קולאב) או תא ה-CivitAI במחברת.</div>
</div></div>

</main><script>
let ENGINE=null;
const ENG=[
 {id:'wan22',nm:'Wan 2.2',d:'איכות לנה — ראשי',where:'cloud'},
 {id:'ad15',nm:'AnimateDiff + SD1.5',d:'מורשת מקומית',where:'local'},
 {id:'ltx',nm:'LTX-Video',d:'טיוטות מהירות (בקרוב)',where:'cloud',soon:1}
];
const $=q=>document.querySelector(q);
function tab(t){document.querySelectorAll('nav button').forEach(b=>b.classList.toggle('act',b.dataset.t===t));
 document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('act',x.id=='t-'+t));}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>tab(b.dataset.t));
function fillEngines(av){
 const sel=$('#engine');sel.innerHTML='';
 ENG.forEach(e=>{
  const ok=av.includes(e.id);
  const o=document.createElement('option');o.value=e.id;
  o.textContent=e.nm+(e.soon?' (בקרוב)':ok?' ✓':'')+' — '+(e.where=='cloud'?'ענן':'מקומי');
  if(e.soon)o.disabled=true;
  sel.appendChild(o);});
 sel.value='wan22';
}
async function refresh(){
 try{
  const r=await fetch('/api/state');const s=await r.json();
  $('#hdot').className='dot'+(s.cloudOnline?' on':'');
  $('#ldot').className='dot'+(s.localUp?' on':'');
  fillEngines(s.engines||[]);
  // תור
  const tb=$('#jobs');tb.innerHTML='';
  (s.jobs||[]).slice(0,15).forEach(j=>{
   const tr=document.createElement('tr');
   const st=j.status||'pending';
   const pr=j.progress?`<div style="background:#221b12;border-radius:6px;height:7px;width:90px"><div style="background:var(--gold);height:7px;border-radius:6px;width:${j.progress||0}%"></div></div>`:'';
   tr.innerHTML=`<td style="max-width:330px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${(j.prompt||'').slice(0,60)}</td>
    <td>${j.engine||'—'}</td><td><span class="st ${st}">${st}</span></td><td>${pr||'—'}</td>
    <td>${j.result_url?`<video class="res" src="${j.result_url}" controls muted></video>`:(st=='pending'||st=='rendering')?`<button class="btn ghost small" onclick="cancelJob('${j.id}')">בטל</button>`:''}</td>`;
   tb.appendChild(tr);});
  // עובדים
  const w=$('#workers');
  if(!(s.workers||[]).length){w.innerHTML='<div class="hint">אין עובדים פעילים כרגע — הפעל ענן מהמחברות למטה או את העובד המקומי.</div>';}
  else{w.innerHTML='';s.workers.forEach(x=>{
   const exp=x.session_expires_at?new Date(x.session_expires_at):null;
   const alive=exp&&exp>new Date();
   w.innerHTML+=`<div class="wcard"><div><div class="nm">${x.name||'?'}</div>
    <small>${x.gpu_model||''} ${x.checkpoints?'· '+x.checkpoints.length+' מודלים':''}</small></div>
    <div><span class="st ${alive?'completed':'failed'}">${alive?'חי עד '+exp.toLocaleTimeString('he'):'סשן הסתיים'}</span></div></div>`;});}
  // קישורי ענן
  $('#clinks').innerHTML=(s.cloud_links||[]).map(l=>`<div>→ <a href="${l[1]}" target="_blank">${l[0]}</a></div>`).join('');
  // מקומי
  $('#localstatus').innerHTML=s.has_comfy?`ComfyUI: ${s.comfyUp?'רץ':'מותקן, כבוי'} · עובד: ${s.workerRunning?'רץ':'כבוי'} · תיקיית לורות: ${s.lora_count}`:'אין התקנה מקומית — מצב ענן בלבד. מנועים מקומיים יופיעו אחרי הרצת המתקין.';
  $('#wkbtn').style.display=s.has_comfy?'':'none';
 }catch(e){}
}
async function submitJob(){
 const prompt=$('#prompt').value.trim();if(!prompt){return say('כתוב פרומפט','err');}
 const r=await fetch('/api/job',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
  prompt,negative_prompt:$('#neg').value.trim(),engine:$('#engine').value,
  aspect_ratio:$('#ar').value,duration:+$('#dur').value,type:'video'})});
 const d=await r.json();
 if(d.ok){say('נשלח לתור ✓ עוקבים בטאב תור','ok');$('#prompt').value='';}
 else say('שגיאה: '+(d.error||'?'),'err');
}
async function cancelJob(id){await fetch('/api/cancel',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh();}
async function toggleWorker(){await fetch('/api/worker',{method:'POST'});setTimeout(refresh,1200);}
async function dlLora(){
 const u=$('#loraurl').value.trim(),t=$('#civtoken').value.trim();
 if(!u){$('#lmsg').textContent='מלא מזהה או קישור';return;}
 const r=await fetch('/api/lora',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u,token:t})});
 const d=await r.json();$('#lmsg').textContent=d.ok?'הורד ✓ '+d.name:'שגיאה: '+(d.error||'?');refresh();
}
function say(t,c){const m=$('#msg');m.textContent=t;m.className=c;}
refresh();setInterval(refresh,5000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            self._json(self.state())
        elif self.path == "/" or self.path.startswith("/?"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            data = {}
        if self.path == "/api/job":
            self._json(self.create_job(data))
        elif self.path == "/api/cancel":
            r = api_post("jobApi", {"action": "cancel", "job_id": data.get("id")})
            self._json({"ok": not r.get("error"), "error": r.get("error")})
        elif self.path == "/api/worker":
            self._json(self.toggle_worker())
        elif self.path == "/api/lora":
            self._json(self.dl_lora(data))
        else:
            self._json({"error": "not found"}, 404)

    # ── לוגיקה ──
    def state(self):
        workers = api_post("workerApi", {"action": "list"}).get("workers") or []
        jobs = api_post("jobApi", {"action": "list"}).get("jobs") or []
        lora_dir = os.path.join(CFG["comfy_path"], "models", "loras")
        loras = []
        if os.path.isdir(lora_dir):
            loras = [f for f in os.listdir(lora_dir) if f.lower().endswith((".safetensors", ".ckpt"))]
        engines = ["wan22", "ad15"]
        return {
            "engines": engines,
            "cloudOnline": any((w.get("session_expires_at") and w.get("session_expires_at", "") > time.strftime("%Y-%m-%dT%H:%M", time.gmtime())) for w in workers),
            "localUp": local_comfy_up(),
            "comfyUp": local_comfy_up(),
            "workerRunning": local_worker_running(),
            "has_comfy": CFG["has_comfy"],
            "loras": loras, "lora_count": len(loras),
            "workers": workers, "jobs": jobs,
            "cloud_links": CLOUD_LINKS,
        }

    def create_job(self, d):
        prompt = (d.get("prompt") or "").strip()
        if not prompt:
            return {"ok": False, "error": "prompt required"}
        payload = {
            "action": "create", "prompt": prompt,
            "negative_prompt": d.get("negative_prompt") or "",
            "engine": d.get("engine") or "wan22",
            "aspect_ratio": d.get("aspect_ratio") or "9:16",
            "duration": int(d.get("duration") or 10),
            "type": d.get("type") or "video",
        }
        if CFG["token"]:
            payload["token"] = CFG["token"]
        r = api_post("jobApi", payload)
        if r.get("error"):
            return {"ok": False, "error": r["error"]}
        return {"ok": True, "job_id": (r.get("job") or {}).get("id")}

    def toggle_worker(self):
        if not CFG["has_comfy"]:
            return {"ok": False, "error": "no local install"}
        if local_worker_running():
            try:
                WORKER_PROC["proc"].terminate()
            except Exception:
                pass
            return {"ok": True, "running": False}
        wpath = os.path.join(HERE, "worker.py")
        if not os.path.exists(wpath):
            return {"ok": False, "error": "worker.py not found — הרץ את המתקין"}
        WORKER_PROC["proc"] = subprocess.Popen([sys.executable, wpath], cwd=HERE,
                                               stdout=open(os.path.join(HERE, "desktop_worker.log"), "w", encoding="utf-8"),
                                               stderr=subprocess.STDOUT)
        return {"ok": True, "running": True}

    def dl_lora(self, d):
        url = (d.get("url") or "").strip()
        token = (d.get("token") or "").strip()
        if not url:
            return {"ok": False, "error": "url required"}
        if url.isdigit():
            if not token:
                return {"ok": False, "error": "CivitAI token נדרש למזהה"}
            url = f"https://civitai.com/api/download/models/{url}"
        lora_dir = os.path.join(CFG["comfy_path"], "models", "loras")
        os.makedirs(lora_dir, exist_ok=True)
        name = "lora_" + url.rstrip("/").split("/")[-1].split("?")[0]
        if not name.lower().endswith(".safetensors"):
            name += ".safetensors"
        dest = os.path.join(lora_dir, name)
        try:
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            with requests.get(url, headers=headers, stream=True, timeout=600, allow_redirects=True) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for c in r.iter_content(1024 * 1024):
                        f.write(c)
            if os.path.getsize(dest) < 1024:
                os.remove(dest)
                return {"ok": False, "error": "קובץ ריק — token שגוי?"}
            return {"ok": True, "name": name, "size_mb": round(os.path.getsize(dest) / 1e6, 1)}
        except Exception as e:
            return {"ok": False, "error": str(e)}


def main():
    print(f"  Shimi Studio Desktop — http://localhost:{PORT}")
    print(f"  API: {CFG['api']}")
    print(f"  התקנה מקומית: {'כן' if CFG['has_comfy'] else 'לא (מצב ענן בלבד)'}")
    try:
        server = socketserver.TCPServer(("0.0.0.0", PORT), Handler)
        server.allow_reuse_address = True
    except OSError:
        print(f"  פורט {PORT} תפוס — מנסה 8788")
        server = socketserver.TCPServer(("0.0.0.0", 8788), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    webbrowser.open("http://localhost:8787")
    print("  מוכן. Ctrl+C ליציאה.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  להתראות")

if __name__ == "__main__":
    main()
