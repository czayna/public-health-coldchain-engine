"""
main.py — FastAPI Application (REST API Layer)
================================================
Exposes the cold-chain analytics engine via a production-ready REST API.

Endpoints:
  GET  /health                    — Liveness probe
  POST /api/v1/seed               — Populate database with mock data
  GET  /api/v1/audit/full         — Full audit report (KPI + risk + redistribution)
  GET  /api/v1/audit/kpi          — Executive KPI summary only
  GET  /api/v1/audit/risk-profiles — Batch-level risk profiles
  GET  /api/v1/audit/breaches     — Cold-chain breach events
  GET  /api/v1/audit/redistribution — Redistribution plan
  GET  /api/v1/inventory          — Raw inventory listing
  GET  /api/v1/clinics            — Facility registry

Author: Portfolio Project
"""

from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import get_db, init_db, VaccineBatch, Clinic, SessionLocal
from backend.models import (
    AuditReport,
    BatchRiskProfile,
    ColdChainBreach,
    ClinicOut,
    KPISummary,
    RedistributionRecommendation,
    VaccineBatchOut,
)
from backend.audit_engine import (
    detect_cold_chain_breaches,
    compute_risk_profiles,
    generate_redistribution_plan,
    run_full_audit,
)
from backend.simulator import populate_database

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Public Health Vaccine Cold-Chain Supply Chain Engine",
    description=(
        "Operations research engine that monitors cold-chain integrity, "
        "calculates expiration-driven financial leakage, and recommends "
        "optimal vaccine redistribution across a regional health network."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Allow CORS for the Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Startup event — ensure tables exist
# ---------------------------------------------------------------------------
@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@app.get("/health", tags=["System"])
def health_check():
    return {"status": "healthy", "service": "cold-chain-engine", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Data Seeding
# ---------------------------------------------------------------------------
@app.post("/api/v1/seed", tags=["System"])
def seed_database():
    """
    Populate the database with realistic mock data.
    WARNING: This clears existing data and regenerates from scratch.
    """
    from backend.database import Base, engine

    # Drop and recreate all tables for a clean seed
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    stats = populate_database()
    return {
        "message": "Database seeded successfully",
        "statistics": stats,
    }


# ---------------------------------------------------------------------------
# Full Audit Report
# ---------------------------------------------------------------------------
@app.get("/api/v1/audit/full", response_model=AuditReport, tags=["Audit"])
def get_full_audit(db: Session = Depends(get_db)):
    """Run the complete audit pipeline and return all analytics."""
    report = run_full_audit(db)
    return report


@app.get("/api/v1/audit/kpi", response_model=KPISummary, tags=["Audit"])
def get_kpi_summary(db: Session = Depends(get_db)):
    """Executive-level KPI snapshot."""
    report = run_full_audit(db)
    return report.kpi_summary


@app.get(
    "/api/v1/audit/risk-profiles",
    response_model=List[BatchRiskProfile],
    tags=["Audit"],
)
def get_risk_profiles(db: Session = Depends(get_db)):
    """Batch-by-batch risk profiles with DTE and leakage estimates."""
    return compute_risk_profiles(db)


@app.get(
    "/api/v1/audit/breaches",
    response_model=List[ColdChainBreach],
    tags=["Audit"],
)
def get_cold_chain_breaches(db: Session = Depends(get_db)):
    """All detected cold-chain temperature breaches."""
    return detect_cold_chain_breaches(db)


@app.get(
    "/api/v1/audit/redistribution",
    response_model=List[RedistributionRecommendation],
    tags=["Audit"],
)
def get_redistribution_plan(db: Session = Depends(get_db)):
    """Optimized redistribution recommendations."""
    profiles = compute_risk_profiles(db)
    return generate_redistribution_plan(profiles)


# ---------------------------------------------------------------------------
# Inventory & Facility Endpoints
# ---------------------------------------------------------------------------
@app.get(
    "/api/v1/inventory",
    response_model=List[VaccineBatchOut],
    tags=["Inventory"],
)
def list_inventory(
    status: str = "active",
    db: Session = Depends(get_db),
):
    """List vaccine batches, optionally filtered by status."""
    query = db.query(VaccineBatch)
    if status:
        query = query.filter(VaccineBatch.status == status)
    return query.all()


@app.get("/api/v1/clinics", response_model=List[ClinicOut], tags=["Facilities"])
def list_clinics(db: Session = Depends(get_db)):
    """List all registered clinics, warehouses, and hospitals."""
    return db.query(Clinic).all()


# ---------------------------------------------------------------------------
# Entry point for direct execution
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
