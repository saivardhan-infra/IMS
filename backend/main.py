from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from datetime import datetime
import time
import threading

from models import Signal, RCA
from database import incidents, signals, cache

app = FastAPI()

# ✅ CORS (for frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Signal ingestion + debouncing (FINAL)
@app.post("/signals")
def ingest(signal: Signal):
    comp = signal.component_id
    current_ts = time.time()

    # If incident exists in last 10 seconds → link
    if comp in cache:
        inc_id, last_ts = cache[comp]

        if current_ts - last_ts <= 10:
            signals.append({**signal.dict(), "incident_id": inc_id})

            # update last seen time
            cache[comp] = (inc_id, current_ts)

            return {"msg": "linked", "incident_id": inc_id}

    # Create new incident
    inc_id = len(incidents) + 1

    incidents[inc_id] = {
        "id": inc_id,
        "component_id": comp,
        "status": "OPEN",
        "start_time": signal.timestamp,
        "end_time": None,
        "rca": None
    }

    signals.append({**signal.dict(), "incident_id": inc_id})

    # store in cache
    cache[comp] = (inc_id, current_ts)

    return {"msg": "created", "incident_id": inc_id}


# 🔹 Get all incidents
@app.get("/incidents")
def get_incidents():
    return list(incidents.values())


# 🔹 Get incident details
@app.get("/incident/{id}")
def get_incident(id: int):
    return {
        "incident": incidents[id],
        "signals": [s for s in signals if s["incident_id"] == id]
    }


# 🔹 Update status
@app.put("/incident/{id}/status")
def update_status(id: int, status: str):
    valid = ["OPEN", "INVESTIGATING", "RESOLVED", "CLOSED"]

    if status not in valid:
        return {"error": "Invalid status"}

    if status == "CLOSED" and not incidents[id]["rca"]:
        return {"error": "RCA required before closing"}

    incidents[id]["status"] = status
    return {"msg": "status updated"}


# 🔹 Add RCA
@app.post("/incident/{id}/rca")
def add_rca(id: int, rca: RCA):
    incidents[id]["rca"] = rca.dict()
    incidents[id]["end_time"] = datetime.now()
    return {"msg": "RCA added"}


# 🔹 Close incident
@app.put("/incident/{id}/close")
def close(id: int):
    if not incidents[id]["rca"]:
        return {"error": "RCA required"}

    incidents[id]["status"] = "CLOSED"

    mttr = None
    if incidents[id]["end_time"]:
        mttr = (incidents[id]["end_time"] - incidents[id]["start_time"]).total_seconds()

    return {"msg": "closed", "MTTR": mttr}


# 🔹 Health check
@app.get("/health")
def health():
    return {"status": "ok"}


# 🔹 Observability
def log_metrics():
    while True:
        print(f"Total signals received: {len(signals)}")
        time.sleep(5)

threading.Thread(target=log_metrics, daemon=True).start()
