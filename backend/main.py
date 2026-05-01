from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, BackgroundTasks
from datetime import datetime
import time
import threading
from collections import defaultdict

from models import Signal, RCA
from database import incidents, signals, cache

app = FastAPI()

# -----------------------------
# 🔐 Rate Limiting (simple)
# -----------------------------
request_count = 0
RATE_LIMIT = 100  # per 5 sec window

def rate_limiter():
    global request_count
    while True:
        request_count = 0
        time.sleep(5)

threading.Thread(target=rate_limiter, daemon=True).start()

# -----------------------------
# 🌐 CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# 📊 Throughput Metrics
# -----------------------------
signal_counter = 0

def log_metrics():
    global signal_counter
    while True:
        print(f"Signals/sec: {signal_counter}")
        signal_counter = 0
        time.sleep(5)

threading.Thread(target=log_metrics, daemon=True).start()

# -----------------------------
# ⚡ Async Queue (Simulation)
# -----------------------------
queue = []

def worker():
    while True:
        if queue:
            signal = queue.pop(0)
            process_signal(signal)
        time.sleep(0.01)

threading.Thread(target=worker, daemon=True).start()

# -----------------------------
# 🧠 Core Processing Logic
# -----------------------------
def process_signal(signal: Signal):
    global signal_counter
    signal_counter += 1

    comp = signal.component_id
    current_ts = time.time()

    # Debouncing
    if comp in cache:
        inc_id, last_ts = cache[comp]

        if current_ts - last_ts <= 10:
            signals.append({**signal.dict(), "incident_id": inc_id})
            cache[comp] = (inc_id, current_ts)
            return

    # Create Incident
    inc_id = len(incidents) + 1

    incidents[inc_id] = {
        "id": inc_id,
        "component_id": comp,
        "status": "OPEN",
        "start_time": signal.timestamp,
        "end_time": None,
        "rca": None,
        "severity": get_severity(comp)
    }

    signals.append({**signal.dict(), "incident_id": inc_id})
    cache[comp] = (inc_id, current_ts)

# -----------------------------
# 🎯 Alert Strategy (Strategy Pattern)
# -----------------------------
def get_severity(component):
    if "DB" in component:
        return "P0"
    elif "CACHE" in component:
        return "P2"
    return "P1"

# -----------------------------
# 🚀 API Endpoints
# -----------------------------

@app.post("/signals")
def ingest(signal: Signal):
    global request_count

    if request_count > RATE_LIMIT:
        return {"error": "Rate limit exceeded"}

    request_count += 1

    # Push to async queue
    queue.append(signal)

    return {"msg": "accepted (async processing)"}


@app.get("/incidents")
def get_incidents():
    return list(incidents.values())


@app.get("/incident/{id}")
def get_incident(id: int):
    return {
        "incident": incidents[id],
        "signals": [s for s in signals if s["incident_id"] == id]
    }


# -----------------------------
# 🔄 State Machine (Workflow)
# -----------------------------
valid_transitions = {
    "OPEN": ["INVESTIGATING"],
    "INVESTIGATING": ["RESOLVED"],
    "RESOLVED": ["CLOSED"],
    "CLOSED": []
}

@app.put("/incident/{id}/status")
def update_status(id: int, status: str):
    current = incidents[id]["status"]

    if status not in valid_transitions[current]:
        return {"error": f"Invalid transition from {current} → {status}"}

    # RCA enforcement
    if status == "CLOSED" and not incidents[id]["rca"]:
        return {"error": "RCA required before closing"}

    incidents[id]["status"] = status
    return {"msg": "status updated"}


# -----------------------------
# 📝 RCA + MTTR
# -----------------------------
@app.post("/incident/{id}/rca")
def add_rca(id: int, rca: RCA):
    incidents[id]["rca"] = rca.dict()
    incidents[id]["end_time"] = datetime.now()
    return {"msg": "RCA added"}


@app.put("/incident/{id}/close")
def close(id: int):
    if not incidents[id]["rca"]:
        return {"error": "RCA required"}

    incidents[id]["status"] = "CLOSED"

    start = incidents[id]["start_time"]
    end = incidents[id]["end_time"]

    mttr = None
    if start and end:
        mttr = (end - start).total_seconds()

    return {"msg": "closed", "MTTR_seconds": mttr}


# -----------------------------
# ❤️ Health Check
# -----------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "incidents": len(incidents),
        "signals": len(signals),
        "queue_size": len(queue)
    }
