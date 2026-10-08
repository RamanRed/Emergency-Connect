# Emergency Relay — Responder Dashboard

A standalone service that **receives emergency signals** from the Emergency
Relay Android app (or its gateway) and shows them on a **live responder
dashboard** — the emergency service's view of incoming alerts.

This folder is self-contained: you can run, test and deploy it on its own.

```
emergency-dashboard/
├── app/
│   ├── server.py      FastAPI app: receiver endpoints + dashboard page
│   ├── models.py      Pydantic schema for an incoming signal
│   └── store.py       SQLite store (auto-falls back to in-memory)
├── api/index.py       Vercel entrypoint (re-exports the app)
├── run.py             Local dev runner  ->  http://127.0.0.1:8000
├── send_test.py       Simulate emergency signals (no extra installs)
├── requirements.txt
├── vercel.json
└── README.md
```

## 1. Run it locally

```bash
cd emergency-dashboard
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python run.py
```

Open **http://127.0.0.1:8000** — that is the dashboard.

## 2. Send a test signal

In another terminal:

```bash
python send_test.py            # one random alert (with a map location)
python send_test.py --n 5      # five random alerts
python send_test.py --code 1 --sev 5   # a Medical, severity 5
```

The alert appears on the dashboard within ~3 seconds (it auto-refreshes).

## 3. Point the Android app at it

In the app's `MainActivity.kt`, set `backendBaseUrl`:

- **Android emulator:** `http://10.0.2.2:8000`
- **Real phone on the same Wi-Fi:** `http://<your-PC-LAN-IP>:8000`
  (find the IP with `ipconfig` -> IPv4 Address)

The app posts to `<base>/messages`, which this service accepts.

## 4. Endpoints

Exposed under both `''` and `/api` (so it works locally and on Vercel):

| Method | Path | Purpose |
|---|---|---|
| GET  | `/`                         | The dashboard page |
| GET  | `/health`                   | Health + store type + count |
| POST | `/messages`                 | Receive one emergency signal |
| GET  | `/messages`                 | List all (newest first) |
| GET  | `/messages/{id}`            | One message |
| POST | `/messages/{id}/ack`        | Responder acknowledges it |

Example receive:

```bash
curl -X POST http://127.0.0.1:8000/messages -H "Content-Type: application/json" -d "{\"message_id\":\"m1\",\"source_id\":\"s1\",\"emergency_code\":1,\"severity\":5,\"timestamp\":1700000000000,\"location_source\":1,\"origin_lat\":18.52,\"origin_lon\":73.85,\"ttl\":5,\"hop_count\":0}"
```

## 5. What the dashboard shows

- Severity pill (1-5, colour-coded) and emergency type.
- Received time and age.
- Source id (truncated) and message id.
- **Location:** exact origin coordinates link to Google Maps; a relay's
  approximate location is clearly labelled "Approx" (never shown as exact);
  "No location" when none.
- Hops / TTL.
- **Acknowledge** button (responder marks it handled) — the row greys out.
- Filters: search, by type, by minimum severity, hide acknowledged.
- Stat cards: total, needs-attention, highest severity, live indicator.

Output is rendered with `textContent`, so attacker-controlled fields cannot
inject script (no XSS).

## 6. Deploy to Vercel (optional)

```bash
npm i -g vercel
vercel          # from this folder
```

`vercel.json` routes every request to the function, and `api/index.py`
re-exports the FastAPI app.

> **Important:** a serverless filesystem is ephemeral/read-only, so the
> SQLite store **falls back to in-memory** there and data does **not**
> persist between cold starts. For a real deployment, point `DB_PATH` at a
> writable disk or swap `store.py` for a hosted database (Postgres /
> Supabase). For a classroom demo, running locally (section 1) is simplest.

## 7. Storage

- **Local run:** SQLite file `emergency.db` in this folder — alerts survive
  a restart. Change the path with the `DB_PATH` environment variable.
- **Serverless:** automatic in-memory fallback (see the note above).

---

Prototype for the Emergency Relay System final-year project. Not a
substitute for India's 112 emergency service.
