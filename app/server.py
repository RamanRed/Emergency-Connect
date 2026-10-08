"""Emergency Relay — Responder Dashboard (receiver).

A standalone service that RECEIVES emergency signals from the
Emergency Relay Android app / gateway and shows them on a live
responder dashboard (the emergency service's view).

Endpoints are exposed under BOTH '' and '/api' so the same service
works for a local phone/emulator (which posts to <base>/messages)
and for a Vercel deployment (which routes /api/*).

Run locally:   python run.py        -> http://127.0.0.1:8000
"""

from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from .models import EmergencyRequest
from .store import MessageStore

app = FastAPI(
    title="Emergency Relay — Responder Dashboard",
    description="Receives emergency signals and shows them to responders.",
    version="1.0.0",
)

store = MessageStore()
api = APIRouter()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def emergency_name(code: int) -> str:
    return {
        1: "Medical", 2: "Fire", 3: "Police", 4: "Accident",
        5: "Trapped", 6: "Missing Person", 7: "General SOS",
    }.get(code, "Unknown")


def location_name(code: int) -> str:
    return {0: "Unknown", 1: "Origin (exact)", 2: "Relay approximate"}.get(code, "Unknown")


# ---------------------------------------------------------------------------
# API (mounted at '' and '/api')
# ---------------------------------------------------------------------------

@api.get("/health")
def health():
    return {"system": "Emergency Relay Dashboard", "status": "running",
            "store": store.backend, "messages": store.count()}


@api.post("/messages")
def receive_message(req: EmergencyRequest):
    """Receive one emergency signal."""
    msg = req.model_dump()
    msg["emergency_name"] = emergency_name(req.emergency_code)
    msg["location_name"] = location_name(req.location_source)
    status = store.add(msg)
    return {
        "status": status,
        "message_id": req.message_id,
        "emergency": msg["emergency_name"],
        "severity": req.severity,
        "hop_count": req.hop_count,
        "ttl": req.ttl,
    }


@api.get("/messages")
def list_messages():
    msgs = store.list()
    return {"count": len(msgs), "messages": msgs}


@api.get("/messages/{message_id}")
def get_message(message_id: str):
    m = store.get(message_id)
    if m is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return m


@api.post("/messages/{message_id}/ack")
def acknowledge(message_id: str):
    if not store.acknowledge(message_id):
        raise HTTPException(status_code=404, detail="Message not found")
    return {"status": "acknowledged", "message_id": message_id}


app.include_router(api)                 # /health, /messages, ...
app.include_router(api, prefix="/api")  # /api/health, /api/messages, ...


# ---------------------------------------------------------------------------
# Dashboard page
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(DASHBOARD_HTML)


DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Emergency Relay — Responder Dashboard</title>
<style>
  :root{
    --teal:#0f766e; --teal2:#14b8a6; --ink:#0f172a; --muted:#64748b;
    --bg:#f1f5f9; --panel:#fff; --line:#e2e8f0;
    --s5:#dc2626; --s4:#ea580c; --s3:#d97706; --s2:#2563eb; --s1:#64748b;
    --amber:#b45309; --amber-bg:#fef3c7; --green:#047857; --green-bg:#d1fae5;
  }
  *{box-sizing:border-box}
  body{margin:0;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--bg);color:var(--ink)}
  header{background:linear-gradient(90deg,var(--teal),var(--teal2));color:#fff;padding:20px 28px}
  header h1{margin:0;font-size:22px;font-weight:800}
  header p{margin:4px 0 0;font-size:13px;opacity:.9}
  .wrap{max-width:1500px;margin:24px auto;padding:0 20px}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
  .card .t{font-size:12px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.4px}
  .card .v{font-size:26px;font-weight:800;margin-top:6px}
  .live{display:inline-flex;align-items:center;gap:7px;font-size:14px;font-weight:700;color:var(--green)}
  .dot{width:9px;height:9px;border-radius:50%;background:#10b981;animation:pulse 1.6s infinite}
  @keyframes pulse{0%{opacity:1}50%{opacity:.4}100%{opacity:1}}
  .controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
  .controls input,.controls select{padding:9px 12px;border:1px solid var(--line);border-radius:9px;font-size:14px;background:#fff;color:var(--ink)}
  .controls input{min-width:220px}
  .controls .right{margin-left:auto;font-size:13px;color:var(--muted)}
  .table-wrap{background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow-x:auto}
  table{width:100%;border-collapse:collapse;min-width:1100px}
  th{background:#f8fafc;text-align:left;padding:13px 14px;font-size:12px;color:var(--muted);
     border-bottom:1px solid var(--line);text-transform:uppercase;letter-spacing:.3px;position:sticky;top:0}
  td{padding:13px 14px;border-bottom:1px solid #f1f5f9;font-size:14px;vertical-align:middle}
  tr.ack{opacity:.55;background:#fafafa}
  .sev{display:inline-flex;align-items:center;justify-content:center;min-width:34px;height:28px;
       border-radius:8px;color:#fff;font-weight:800;font-size:14px}
  .type{font-weight:700}
  .src{font-family:monospace;font-size:12px;color:var(--muted)}
  .mid{font-family:monospace;font-size:11px;color:#94a3b8}
  .loc-exact a{color:var(--teal);font-weight:600;text-decoration:none}
  .loc-approx{color:var(--amber);background:var(--amber-bg);padding:3px 8px;border-radius:7px;font-weight:600;font-size:12px}
  .loc-approx a{color:var(--amber);text-decoration:none}
  .loc-none{color:#cbd5e1}
  .hops{font-size:12px;color:var(--muted)}
  .btn{padding:7px 12px;border:1px solid var(--teal);background:#fff;color:var(--teal);
       border-radius:8px;font-weight:700;font-size:13px;cursor:pointer}
  .btn:hover{background:var(--teal);color:#fff}
  .badge-ack{color:var(--green);background:var(--green-bg);padding:4px 10px;border-radius:999px;font-weight:700;font-size:12px}
  .empty{text-align:center;padding:60px;color:var(--muted);font-size:15px}
  @media(max-width:800px){.stats{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>

<header>
  <h1>Emergency Relay — Responder Dashboard</h1>
  <p>Live emergency signals received by the backend. Prototype — not a substitute for 112.</p>
</header>

<div class="wrap">
  <div class="stats">
    <div class="card"><div class="t">Total emergencies</div><div class="v" id="stTotal">0</div></div>
    <div class="card"><div class="t">Needs attention</div><div class="v" id="stOpen" style="color:var(--s5)">0</div></div>
    <div class="card"><div class="t">Highest severity</div><div class="v" id="stSev">-</div></div>
    <div class="card"><div class="t">Backend</div><div class="v"><span class="live"><span class="dot"></span>Live</span></div></div>
  </div>

  <div class="controls">
    <input id="search" type="text" placeholder="Search type, source or ID..." oninput="apply()">
    <select id="fType" onchange="apply()">
      <option value="">All types</option>
      <option>Medical</option><option>Fire</option><option>Police</option>
      <option>Accident</option><option>Trapped</option><option>Missing Person</option><option>General SOS</option>
    </select>
    <select id="fSev" onchange="apply()">
      <option value="0">All severities</option>
      <option value="5">Severity 5 only</option>
      <option value="4">Severity 4+</option>
      <option value="3">Severity 3+</option>
    </select>
    <label style="font-size:13px;color:var(--muted)">
      <input type="checkbox" id="hideAck" onchange="apply()"> Hide acknowledged
    </label>
    <span class="right" id="updated">-</span>
  </div>

  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Sev</th><th>Emergency</th><th>Received</th><th>Age</th>
        <th>Source</th><th>Location</th><th>Relay</th><th>Message ID</th><th>Action</th>
      </tr></thead>
      <tbody id="rows"></tbody>
    </table>
    <div id="empty" class="empty">No emergency messages received yet.</div>
  </div>
</div>

<script>
  var SEV_COLORS = {5:'var(--s5)',4:'var(--s4)',3:'var(--s3)',2:'var(--s2)',1:'var(--s1)'};
  var latest = [];

  function fmtTime(ms){ if(!ms) return '-'; try{ return new Date(ms).toLocaleString(); }catch(e){ return '-'; } }
  function ageText(iso){
    if(!iso) return '-';
    var t = new Date(iso).getTime();
    var s = Math.max(0, Math.floor((Date.now()-t)/1000));
    if(s<60) return s+'s ago';
    if(s<3600) return Math.floor(s/60)+'m ago';
    if(s<86400) return Math.floor(s/3600)+'h ago';
    return Math.floor(s/86400)+'d ago';
  }
  function td(text, cls){
    var c = document.createElement('td');
    if(cls) c.className = cls;
    if(text !== undefined && text !== null) c.textContent = String(text);
    return c;
  }
  function locationCell(m){
    var c = document.createElement('td');
    if(m.origin_lat != null && m.origin_lon != null){
      c.className = 'loc-exact';
      var a = document.createElement('a');
      a.href = 'https://www.google.com/maps?q='+m.origin_lat+','+m.origin_lon;
      a.target='_blank'; a.rel='noopener';
      a.textContent = 'Exact: '+Number(m.origin_lat).toFixed(5)+', '+Number(m.origin_lon).toFixed(5);
      c.appendChild(a);
    } else if(m.fallback_lat != null && m.fallback_lon != null){
      var span = document.createElement('span'); span.className='loc-approx';
      var a2 = document.createElement('a');
      a2.href = 'https://www.google.com/maps?q='+m.fallback_lat+','+m.fallback_lon;
      a2.target='_blank'; a2.rel='noopener';
      a2.textContent = '~ Approx: '+Number(m.fallback_lat).toFixed(5)+', '+Number(m.fallback_lon).toFixed(5);
      span.appendChild(a2); c.appendChild(span);
    } else { c.className='loc-none'; c.textContent='No location'; }
    return c;
  }
  function sevCell(sev){
    var c = document.createElement('td');
    var b = document.createElement('span'); b.className='sev';
    b.style.background = SEV_COLORS[sev] || 'var(--s1)'; b.textContent = sev;
    c.appendChild(b); return c;
  }
  function actionCell(m){
    var c = document.createElement('td');
    if(m.acknowledged){
      var s = document.createElement('span'); s.className='badge-ack'; s.textContent='Acknowledged';
      c.appendChild(s);
    } else {
      var btn = document.createElement('button'); btn.className='btn'; btn.textContent='Acknowledge';
      btn.onclick = function(){ ack(m.message_id); };
      c.appendChild(btn);
    }
    return c;
  }
  function render(list){
    var body = document.getElementById('rows');
    var empty = document.getElementById('empty');
    body.textContent = '';
    if(list.length === 0){ empty.style.display='block'; return; }
    empty.style.display='none';
    list.forEach(function(m){
      var tr = document.createElement('tr');
      if(m.acknowledged) tr.className='ack';
      tr.appendChild(sevCell(m.severity));
      tr.appendChild(td(m.emergency_name, 'type'));
      tr.appendChild(td(fmtTime(m.timestamp)));
      tr.appendChild(td(ageText(m.received_at)));
      tr.appendChild(td((m.source_id||'').slice(0,10)+'...', 'src'));
      tr.appendChild(locationCell(m));
      tr.appendChild(td('Hops '+m.hop_count+' / TTL '+m.ttl, 'hops'));
      tr.appendChild(td((m.message_id||'').slice(0,12)+'...', 'mid'));
      tr.appendChild(actionCell(m));
      body.appendChild(tr);
    });
  }
  function apply(){
    var q = document.getElementById('search').value.toLowerCase();
    var ty = document.getElementById('fType').value;
    var sv = parseInt(document.getElementById('fSev').value,10);
    var hideAck = document.getElementById('hideAck').checked;
    var list = latest.filter(function(m){
      if(ty && m.emergency_name !== ty) return false;
      if(sv && m.severity < sv) return false;
      if(hideAck && m.acknowledged) return false;
      if(q){
        var hay = (m.emergency_name+' '+m.source_id+' '+m.message_id).toLowerCase();
        if(hay.indexOf(q) === -1) return false;
      }
      return true;
    });
    render(list);
    document.getElementById('stTotal').textContent = latest.length;
    document.getElementById('stOpen').textContent = latest.filter(function(m){return !m.acknowledged;}).length;
    var sevs = latest.map(function(m){return m.severity;});
    document.getElementById('stSev').textContent = sevs.length ? Math.max.apply(null, sevs) : '-';
  }
  function ack(id){
    fetch('messages/'+encodeURIComponent(id)+'/ack', {method:'POST'})
      .then(function(){ load(); }).catch(function(e){ console.error(e); });
  }
  async function load(){
    try{
      var res = await fetch('messages');
      if(!res.ok) throw new Error('load failed');
      var data = await res.json();
      latest = data.messages || [];
      apply();
      document.getElementById('updated').textContent = 'Updated '+new Date().toLocaleTimeString();
    }catch(e){ console.error(e); }
  }
  load();
  setInterval(load, 3000);
</script>
</body>
</html>
"""
