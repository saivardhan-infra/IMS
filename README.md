# 🚀 Incident Management System (IMS)

## 📌 Overview

This project is a simple Incident Management System built for an Infrastructure/SRE assignment.

It focuses on handling large volumes of system signals and reducing alert noise using **time-based debouncing**, similar to real-world monitoring systems.

---

## 💡 Problem

In production systems, a single failure (like a DB issue) can generate many alerts.
Creating an incident for each alert leads to noise and confusion.

This system solves that by grouping related signals into a single incident.

---

## ⚙️ Features

* Signal ingestion via API
* 10-second debouncing window
* Incident creation and grouping
* Incident lifecycle (OPEN → CLOSED)
* RCA required before closing
* MTTR calculation
* Simple dashboard
* Docker-based setup

---

## 🏗️ Architecture

```text
Client (curl/UI)
        ↓
FastAPI Backend
        ↓
Debounce Logic (10s window)
        ↓
In-memory Store
        ↓
Frontend Dashboard
```

---

## 🧠 Key Design Decision

### Debouncing Logic

If multiple signals for the same component arrive within 10 seconds:
👉 They are grouped into one incident
👉 Prevents duplicate incidents

---

## 🚀 Run the Project

```bash
docker-compose up --build
```

---

## 🌐 Access

* Backend → http://localhost:8000
* Frontend → http://localhost:3000

---

## 📡 Example API

```bash
curl -X POST http://localhost:8000/signals \
-H "Content-Type: application/json" \
-d '{"component_id":"DB","message":"error","timestamp":"2026-01-01T10:00:00"}'
```

---

## 🧪 Behavior

* Multiple signals within 10 sec → same incident
* Signals after 10 sec → new incident

---

## 📁 Structure

```text
backend/   - FastAPI service
frontend/  - UI
scripts/   - test scripts
prompts/   - AI prompts used
```

---

## 🔐 Limitations

* In-memory storage (no persistence)
* No authentication
* Single-node system

---

## 🔮 Improvements

* Add PostgreSQL
* Add Redis
* Use Kafka for streaming
* Add monitoring (Prometheus)

---

## 👨‍💻 Author

Sai Vardhan
