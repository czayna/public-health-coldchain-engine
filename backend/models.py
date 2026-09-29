"""
models.py — Pydantic Schemas & Data Transfer Objects
=====================================================
Defines the request/response contracts for the FastAPI REST layer.
These schemas are deliberately separate from the SQLAlchemy ORM models
in database.py to maintain a clean architectural boundary.

Author: Portfolio Project
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Clinic Schemas
# ---------------------------------------------------------------------------

class ClinicBase(BaseModel):
    name: str
    region: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    storage_capacity_doses: int = 50_000
    facility_type: str = "clinic"


class ClinicOut(ClinicBase):
    id: int
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Vaccine Batch Schemas
# ---------------------------------------------------------------------------

class VaccineBatchBase(BaseModel):
    batch_code: str
    vaccine_name: str
    manufacturer: str
    quantity_doses: int
    initial_quantity: int
    unit_cost_usd: float
    manufacturing_date: date
    expiry_date: date
    clinic_id: int
    cold_chain_intact: bool = True
    status: str = "active"


class VaccineBatchOut(VaccineBatchBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Temperature Log Schemas
# ---------------------------------------------------------------------------

class TemperatureLogBase(BaseModel):
    batch_id: int
    temperature_celsius: float
    sensor_id: Optional[str] = None
    is_breach: bool = False
    recorded_at: Optional[datetime] = None


class TemperatureLogOut(TemperatureLogBase):
    id: int
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Shipment / Redistribution Schemas
# ---------------------------------------------------------------------------

class ShipmentBase(BaseModel):
    batch_id: int
    source_clinic_id: int
    destination_clinic_id: int
    quantity_doses: int
    shipment_type: str = "redistribution"
    status: str = "planned"
    notes: Optional[str] = None


class ShipmentOut(ShipmentBase):
    id: int
    created_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Audit / Analytics Response Schemas
# ---------------------------------------------------------------------------

class BatchRiskProfile(BaseModel):
    """Risk assessment for a single vaccine batch."""
    batch_id: int
    batch_code: str
    vaccine_name: str
    clinic_name: str
    region: str
    quantity_doses: int
    days_to_expiry: int
    expiry_date: date
    daily_consumption_rate: float = Field(
        description="Estimated average doses consumed per day at this clinic."
    )
    projected_waste_doses: int = Field(
        description="Doses expected to expire before consumption at current velocity."
    )
    financial_leakage_usd: float = Field(
        description="Estimated dollar value of projected wasted doses."
    )
    risk_tier: str = Field(
        description="Optimal | Near-Expiry Warning | High Spoilage Risk"
    )
    cold_chain_intact: bool


class ColdChainBreach(BaseModel):
    """A detected temperature excursion event."""
    batch_id: int
    batch_code: str
    vaccine_name: str
    clinic_name: str
    breach_temperature: float
    recorded_at: datetime
    breach_type: str = Field(description="Below Range (<2°C) | Above Range (>8°C)")


class RedistributionRecommendation(BaseModel):
    """Proposed transfer of doses from surplus → deficit clinic."""
    source_clinic: str
    source_region: str
    destination_clinic: str
    destination_region: str
    vaccine_name: str
    batch_code: str
    transfer_quantity: int
    days_to_expiry: int
    financial_value_usd: float
    priority: str = Field(description="Critical | High | Medium")
    rationale: str


class KPISummary(BaseModel):
    """Executive-level KPI snapshot."""
    total_active_inventory_doses: int
    total_active_inventory_value_usd: float
    total_projected_leakage_usd: float
    total_leakage_doses: int
    active_cold_chain_breaches: int
    batches_at_high_risk: int
    batches_near_expiry_warning: int
    batches_optimal: int
    clinics_with_stockout_risk: int
    redistribution_opportunities: int


class AuditReport(BaseModel):
    """Full audit engine output bundled for the dashboard."""
    kpi_summary: KPISummary
    risk_profiles: List[BatchRiskProfile]
    cold_chain_breaches: List[ColdChainBreach]
    redistribution_plan: List[RedistributionRecommendation]
