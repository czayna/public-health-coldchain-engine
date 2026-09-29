"""
database.py — Database Connection & SQLAlchemy ORM Models
=========================================================
Manages the connection pool, session factory, and declarative ORM models
for the Public Health Vaccine Cold-Chain Supply Chain Engine.

Supported backends:
  • PostgreSQL (production)  — set DATABASE_URL env var
  • SQLite     (development) — automatic fallback to ./coldchain.db

Author: Portfolio Project
"""

import os
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ---------------------------------------------------------------------------
# Engine & Session Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./coldchain.db",  # lightweight default for local dev
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    # SQLite needs check_same_thread=False for FastAPI's threaded model
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# Dependency helper — yields a scoped DB session for FastAPI endpoints
# ---------------------------------------------------------------------------
def get_db():
    """FastAPI dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# ORM Models
# ---------------------------------------------------------------------------

class Clinic(Base):
    """
    Represents a regional health facility (clinic, hospital, or warehouse)
    that stores and administers vaccines.
    """
    __tablename__ = "clinics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    region = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    storage_capacity_doses = Column(Integer, default=50_000)
    facility_type = Column(String(50), default="clinic")  # clinic | warehouse | hospital

    # Relationships
    batches = relationship("VaccineBatch", back_populates="clinic")

    def __repr__(self):
        return f"<Clinic {self.name} ({self.region})>"


class VaccineBatch(Base):
    """
    A single lot/batch of vaccines stored at a specific clinic.
    Tracks quantity, cost, expiry, and cold-chain integrity status.
    """
    __tablename__ = "vaccine_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_code = Column(String(30), nullable=False, unique=True, index=True)
    vaccine_name = Column(String(150), nullable=False)
    manufacturer = Column(String(150), nullable=False)

    quantity_doses = Column(Integer, nullable=False)
    initial_quantity = Column(Integer, nullable=False)
    unit_cost_usd = Column(Float, nullable=False)

    manufacturing_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)

    clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False)
    cold_chain_intact = Column(Boolean, default=True)
    status = Column(String(30), default="active")  # active | expired | redistributed | disposed

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    clinic = relationship("Clinic", back_populates="batches")
    temperature_logs = relationship("TemperatureLog", back_populates="batch")

    def __repr__(self):
        return f"<VaccineBatch {self.batch_code} — {self.vaccine_name}>"


class TemperatureLog(Base):
    """
    Time-series cold-chain temperature reading for a specific vaccine batch.
    Acceptable range: 2 °C – 8 °C (WHO standard for most vaccines).
    """
    __tablename__ = "temperature_logs"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("vaccine_batches.id"), nullable=False)
    recorded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    temperature_celsius = Column(Float, nullable=False)
    sensor_id = Column(String(50), nullable=True)
    is_breach = Column(Boolean, default=False)

    # Relationships
    batch = relationship("VaccineBatch", back_populates="temperature_logs")

    def __repr__(self):
        return f"<TempLog batch={self.batch_id} temp={self.temperature_celsius}°C>"


class Shipment(Base):
    """
    Records movement of vaccine doses between facilities (redistribution,
    initial delivery, or emergency transfer).
    """
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("vaccine_batches.id"), nullable=False)
    source_clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False)
    destination_clinic_id = Column(Integer, ForeignKey("clinics.id"), nullable=False)
    quantity_doses = Column(Integer, nullable=False)
    shipment_type = Column(String(30), default="redistribution")  # initial | redistribution | emergency
    status = Column(String(30), default="planned")  # planned | in_transit | delivered | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Relationships
    batch = relationship("VaccineBatch")
    source_clinic = relationship("Clinic", foreign_keys=[source_clinic_id])
    destination_clinic = relationship("Clinic", foreign_keys=[destination_clinic_id])

    def __repr__(self):
        return f"<Shipment {self.source_clinic_id} → {self.destination_clinic_id} ({self.quantity_doses} doses)>"


# ---------------------------------------------------------------------------
# Table creation utility
# ---------------------------------------------------------------------------
def init_db():
    """Create all tables. Safe to call multiple times (uses IF NOT EXISTS)."""
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
    print("✅ Database tables created successfully.")
