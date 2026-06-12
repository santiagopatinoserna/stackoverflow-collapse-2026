#!/usr/bin/env python3
"""
Fetch Stack Overflow question volumes from the Stack Exchange API (no key).
v2: checkpoints after EVERY request (resume-safe), tolerant answers section.

Pulls:
  1. Quarterly question counts 2008-Q3 .. 2026-Q1 (71 req)
  2. Monthly question counts 2025-01 .. 2026-05 (17 req)
  3. Per-tag yearly counts, 8 tags x [2022, 2024, 2025] (24 req)
  4. Yearly answer counts [2014, 2022, 2025] — best effort (3 req)

Source: https://api.stackexchange.com/2.3 (filter=total, anonymous quota 300/day)
"""
import json
import gzip
import io
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BASE = "https://api.stackexchange.com/2.3"
UA = "santiago-godi-research/1.0 santiagopatinoserna@godi.ai"
CKPT = "checkpoint.json"

if os.path.exists(CKPT):
    with open(CKPT) as f:
        STORE = json.load(f)
    print(f"resuming: {len(STORE['data'])} entries already fetched")
else:
    STORE = {"meta": {
        "pulled_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "https://api.stackexchange.com/2.3",
        "auth": "none (anonymous quota)",
    }, "data": {}}

REQ = 0


def save():
    with open(CKPT, "w") as f:
        json.dump(STORE, f, indent=1)


def api_total(key, path, fromdate, todate, extra=None, timeout=60):
    """One filter=total call -> int. Checkpointed + idempotent by key."""
    global REQ
    if key in STORE["data"]:
        return STORE["data"][key]
    params = {"site": "stackoverflow", "fromdate": str(fromdate),
              "todate": str(todate), "filter": "total"}
    if extra:
        params.update(extra)
    url = f"{BASE}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept-Encoding": "gzip"})
    last_err = None
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
                data = json.loads(raw)
                REQ += 1
                if "backoff" in data:
                    print(f"  [backoff {data['backoff']}s]")
                    time.sleep(data["backoff"] + 1)
                STORE["data"][key] = data["total"]
                save()
                return data["total"]
        except Exception as e:
            last_err = e
            wait = 10 * (attempt + 1)
            print(f"  retry {attempt+1}/5 for {key}: {type(e).__name__} {e} (wait {wait}s)")
            time.sleep(wait)
    raise RuntimeError(f"failed after retries: {key} :: {last_err}")


def ts(y, m):
    return int(datetime(y, m, 1, tzinfo=timezone.utc).timestamp())


# ---- 1. Quarterly 2008Q3 .. 2026Q1 ----
print("Section 1: quarterly 2008Q3..2026Q1")
y, m = 2008, 7
while (y, m) <= (2026, 1):
    ey, em = (y, m + 3) if m + 3 <= 12 else (y + 1, m + 3 - 12)
    label = f"{y}Q{(m - 1) // 3 + 1}"
    n = api_total(f"q:{label}", "questions", ts(y, m), ts(ey, em))
    print(f"  {label}: {n:,}")
    time.sleep(1.2)
    y, m = ey, em

# ---- 2. Monthly 2025-01 .. 2026-05 ----
print("Section 2: monthly 2025-01..2026-05")
y, m = 2025, 1
while (y, m) <= (2026, 5):
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    n = api_total(f"m:{y}-{m:02d}", "questions", ts(y, m), ts(ny, nm))
    print(f"  {y}-{m:02d}: {n:,}")
    time.sleep(1.2)
    y, m = ny, nm

# ---- 3. Tags x years ----
print("Section 3: tags")
TAGS = ["python", "javascript", "reactjs", "pandas", "rust", "typescript",
        "langchain", "next.js"]
for tag in TAGS:
    for yy in [2022, 2024, 2025]:
        n = api_total(f"t:{tag}:{yy}", "questions", ts(yy, 1), ts(yy + 1, 1),
                      {"tagged": tag})
        print(f"  {tag} {yy}: {n:,}")
        time.sleep(1.2)

# ---- 4. Answers (best effort) ----
print("Section 4: answers (best effort)")
for yy in [2014, 2022, 2025]:
    try:
        n = api_total(f"a:{yy}", "answers", ts(yy, 1), ts(yy + 1, 1), timeout=90)
        print(f"  answers {yy}: {n:,}")
        time.sleep(1.2)
    except RuntimeError as e:
        print(f"  answers {yy}: UNAVAILABLE ({e})")
        STORE["data"][f"a:{yy}"] = None
        save()

# ---- reshape to final raw file ----
d = STORE["data"]
out = {"meta": {**STORE["meta"], "requests_this_run": REQ},
       "quarterly": [], "monthly": [], "tags": [], "answers": []}
y, m = 2008, 7
while (y, m) <= (2026, 1):
    label = f"{y}Q{(m - 1) // 3 + 1}"
    out["quarterly"].append({"quarter": label, "start": f"{y}-{m:02d}",
                             "questions": d[f"q:{label}"]})
    m += 3
    if m > 12:
        y, m = y + 1, m - 12
y, m = 2025, 1
while (y, m) <= (2026, 5):
    out["monthly"].append({"month": f"{y}-{m:02d}", "questions": d[f"m:{y}-{m:02d}"]})
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
for tag in TAGS:
    out["tags"].append({"tag": tag, **{str(yy): d[f"t:{tag}:{yy}"]
                                       for yy in [2022, 2024, 2025]}})
for yy in [2014, 2022, 2025]:
    out["answers"].append({"year": yy, "answers": d.get(f"a:{yy}")})

with open("stackoverflow_raw.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"\nDone. {REQ} new API requests this run. Saved stackoverflow_raw.json")
