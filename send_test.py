"""Simulate an emergency signal being received by the dashboard.

Uses only the standard library (no extra installs).

    python send_test.py                     # one random Medical SOS -> 127.0.0.1:8000
    python send_test.py --code 2 --sev 5     # a Fire, severity 5
    python send_test.py --n 5                # five random alerts
    python send_test.py --url http://192.168.1.7:8000   # a phone / LAN target
"""

import argparse
import json
import random
import time
import urllib.request
import uuid

CODES = {1: "Medical", 2: "Fire", 3: "Police", 4: "Accident",
         5: "Trapped", 6: "Missing", 7: "General SOS"}

# A few plausible coordinates (Pune, India) to show map pins on the dashboard.
SPOTS = [
    (18.5204, 73.8567), (18.5089, 73.8553), (18.5679, 73.9143),
    (18.4575, 73.8508), (18.6298, 73.7997),
]


def send(url: str, code: int, sev: int, with_location: bool) -> None:
    lat, lon = random.choice(SPOTS)
    body = {
        "message_id": str(uuid.uuid4()),
        "source_id": "test-" + uuid.uuid4().hex[:8],
        "emergency_code": code,
        "severity": sev,
        "timestamp": int(time.time() * 1000),   # ms (matches the Android app)
        "origin_lat": lat if with_location else None,
        "origin_lon": lon if with_location else None,
        "location_source": 1 if with_location else 0,
        "fallback_lat": None,
        "fallback_lon": None,
        "ttl": 5,
        "hop_count": random.randint(0, 2),
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/messages", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as r:
        resp = json.loads(r.read().decode())
    print(f"  sent {CODES.get(code, '?'):8} sev{sev}  ->  {resp.get('status')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--code", type=int, default=None, help="emergency code 1-7")
    ap.add_argument("--sev", type=int, default=None, help="severity 1-5")
    ap.add_argument("--n", type=int, default=1, help="how many alerts")
    ap.add_argument("--no-location", action="store_true")
    args = ap.parse_args()

    print(f"Sending {args.n} signal(s) to {args.url} ...")
    for _ in range(args.n):
        code = args.code or random.choice(list(CODES))
        sev = args.sev or random.randint(1, 5)
        try:
            send(args.url, code, sev, not args.no_location)
        except Exception as exc:
            print(f"  FAILED: {exc}")
        time.sleep(0.3)
    print("Open the dashboard to see them.")


if __name__ == "__main__":
    main()
