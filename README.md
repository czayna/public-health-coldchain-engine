# 🏥 Public Health Vaccine & Medical Cold-Chain Supply Chain Leakage & Expiration Risk Engine

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Executive Summary

An end-to-end **operations research engine** that monitors vaccine cold-chain integrity, calculates expiration-driven financial leakage across a regional public health network, and generates automated redistribution recommendations to minimize waste and prevent stockouts.

Built as a production-grade portfolio project demonstrating expertise in:
- **Data Engineering** — relational data modeling, ETL pipeline design, REST API architecture
- **Operations Research** — consumption velocity modeling, surplus/deficit optimization, risk-tier classification
- **Analytics Engineering** — executive-level KPI dashboards, interactive data visualization, real-time monitoring

---

## 🔑 Key Capabilities

| Capability | Description |
|---|---|
| **Cold-Chain Monitoring** | Continuous temperature tracking with WHO-standard breach detection (2°C – 8°C) |
| **Expiration Risk Engine** | Days-to-Expiry (DTE) vs. consumption velocity → projected waste & financial leakage |
| **Redistribution Optimizer** | Greedy surplus→deficit matching algorithm generating actionable transfer schedules |
| **Executive Dashboard** | Streamlit command center with KPI cards, Plotly charts, and filterable risk matrices |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│  (KPI Cards · Risk Matrix · Redistribution Planner)         │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST
┌──────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend                          │
│  /api/v1/audit/* · /api/v1/inventory · /api/v1/clinics      │
├─────────────────────────────────────────────────────────────┤
│                   Audit Engine (OR Logic)                    │
│  breach_detection · risk_profiles · redistribution_optimizer │
├─────────────────────────────────────────────────────────────┤
│               SQLAlchemy ORM + Database                     │
│         (PostgreSQL production / SQLite development)        │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
public-health-coldchain-engine/
├── backend/
│   ├── __init__.py
│   ├── database.py        # SQLAlchemy ORM models & connection management
│   ├── models.py           # Pydantic request/response schemas
│   ├── simulator.py        # Realistic mock data generator (15 clinics, 200+ batches)
│   ├── audit_engine.py     # Core OR logic: breaches, DTE, leakage, redistribution
│   └── main.py             # FastAPI application with REST endpoints
├── frontend/
│   └── app.py              # Streamlit executive command center dashboard
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- pip package manager

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/public-health-coldchain-engine.git
cd public-health-coldchain-engine
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Start the Backend API

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000` with interactive docs at `/docs`.

### 3. Seed the Database

Open `http://localhost:8000/docs` and execute the `POST /api/v1/seed` endpoint, or run:

```bash
curl -X POST http://localhost:8000/api/v1/seed
```

### 4. Launch the Dashboard

```bash
streamlit run frontend/app.py
```

Navigate to `http://localhost:8501` to access the command center.

---

## 📊 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service liveness check |
| `POST` | `/api/v1/seed` | Generate mock data (resets database) |
| `GET` | `/api/v1/audit/full` | Complete audit report (KPI + risk + redistribution) |
| `GET` | `/api/v1/audit/kpi` | Executive KPI summary |
| `GET` | `/api/v1/audit/risk-profiles` | Batch-level risk profiles |
| `GET` | `/api/v1/audit/breaches` | Cold-chain breach events |
| `GET` | `/api/v1/audit/redistribution` | Redistribution recommendations |
| `GET` | `/api/v1/inventory?status=active` | Raw inventory listing |
| `GET` | `/api/v1/clinics` | Facility registry |

Full OpenAPI documentation available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## 🧠 Operations Research Methodology

### Cold-Chain Breach Detection
- **Standard:** WHO 2°C – 8°C storage requirement for most vaccines
- **Method:** Every temperature log is evaluated against the threshold window. Breaches are flagged at the reading level and propagated to the batch level, marking `cold_chain_intact = False`

### Expiration Risk & Financial Leakage
- **DTE Calculation:** `days_to_expiry = expiry_date - today`
- **Consumption Velocity:** `daily_rate = (initial_quantity - current_quantity) / days_in_service`
- **Projected Waste:** `waste = max(0, current_quantity - daily_rate × DTE)`
- **Financial Leakage:** `leakage = projected_waste × unit_cost_usd`
- **Risk Tiers:**
  - 🟢 **Optimal** — DTE > 30 days and projected waste < 50% of stock
  - 🟡 **Near-Expiry Warning** — DTE ≤ 30 days
  - 🔴 **High Spoilage Risk** — DTE ≤ 14 days or projected waste > 50%

### Redistribution Optimization
- **Surplus Detection:** Clinics holding near-expiry/high-risk batches with >50 doses
- **Deficit Detection:** Clinics with <30 days of supply at current consumption rate
- **Matching:** Greedy algorithm, sorted by urgency (lowest DTE first), with priority assignment:
  - 🔴 Critical: DTE ≤ 7 days
  - 🟠 High: DTE ≤ 14 days
  - 🔵 Medium: DTE ≤ 30 days

---

## 🧪 Mock Data Profile

The simulator generates a realistic operational dataset:

| Entity | Volume | Details |
|--------|--------|---------|
| **Facilities** | 15 | Warehouses, hospitals, and rural clinics across 7 regions |
| **Vaccine Types** | 12 | COVID-19, Influenza, MMR, Hepatitis B, HPV, Pneumococcal, etc. |
| **Batches** | 200+ | With realistic pricing ($4 – $230/dose), shelf lives, and consumption patterns |
| **Temperature Logs** | 10,000+ | Time-series readings with ~12% intentional breach injection |
| **Consumption Model** | Variable | Hospitals consume fastest; warehouses slowest (redistribution hubs) |

---

## 🔧 Configuration

### PostgreSQL (Production)
Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/coldchain"
```

Uncomment `psycopg2-binary` in `requirements.txt` and reinstall.

### SQLite (Development)
No configuration needed — the engine defaults to `./coldchain.db`.

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

<p align="center">
  <em>Built to demonstrate production-grade data engineering and operations research capabilities.</em>
</p>
