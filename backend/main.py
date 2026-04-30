from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from datetime import datetime
import time

from models import Signal, RCA
from database import incidents, signals, cache

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 Signal ingestion + debouncing
@app.post("/signals")
def ingest(signal: Signal):
    now = time.time()
    comp = signal.component_id

    if comp in cache:
        inc_id, last = cache[comp]
        if now - last < 10:
            cache[comp] = (inc_id, now)
            signals.append({**signal.dict(), "incident_id": inc_id})
            return {"msg": "linked"}

    inc_id = len(incidents) + 1
    incidents[inc_id] = {
        "id": inc_id,
        "component_id": comp,
        "status": "OPEN",
        "start_time": signal.timestamp,
        "end_time": None,
        "rca": None
    }

    cache[comp] = (inc_id, now)
    signals.append({**signal.dict(), "incident_id": inc_id})

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
        return {"error": "RCA required"}

    incidents[id]["status"] = status
    return {"msg": "updated"}


# 🔹 Add RCA
@app.post("/incident/{id}/rca")
def add_rca(id: int, rca: RCA):
    incidents[id]["rca"] = rca.dict()
    incidents[id]["end_time"] = datetime.now()
    return {"msg": "RCA added"}


# 🔹 Close
@app.put("/incident/{id}/close")
def close(id: int):
    if not incidents[id]["rca"]:
        return {"error": "RCA required"}

    incidents[id]["status"] = "CLOSED"
    mttr = (incidents[id]["end_time"] - incidents[id]["start_time"]).total_seconds()
    return {"msg": "closed", "MTTR": mttr}


# 🔹 Health
@app.get("/health")
def health():
    return {"status": "ok"}


# 🔹 Observability (logs every 5 sec)
import threading

def log_metrics():
    while True:
        print(f"Total signals: {len(signals)}")
        time.sleep(5)

threading.Thread(target=log_metrics, daemon=True).start()
