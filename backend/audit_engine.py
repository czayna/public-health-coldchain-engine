"""
audit_engine.py — Core Operations Research & Risk Analytics Engine
===================================================================
Implements the three analytical pillars of the cold-chain engine:

  1. Cold-Chain Breach Detection   — flags batches with out-of-range temps
  2. Expiration Risk & Leakage     — DTE vs. consumption velocity → waste $
  3. Redistribution Optimization   — surplus/deficit matching across clinics

This module is deliberately pure-logic (no HTTP concerns) so it can be
tested independently and called from both FastAPI and Streamlit.

Author: Portfolio Project
"""

from datetime import date, datetime
from typing import Dict, List, Tuple

from sqlalchemy.orm import Session

from backend.database import Clinic, VaccineBatch, TemperatureLog
from backend.models import (
    AuditReport,
    BatchRiskProfile,
    ColdChainBreach,
    KPISummary,
    RedistributionRecommendation,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
COLD_CHAIN_MIN_C = 2.0   # WHO lower bound (°C)
COLD_CHAIN_MAX_C = 8.0   # WHO upper bound (°C)
NEAR_EXPIRY_THRESHOLD_DAYS = 30
HIGH_RISK_THRESHOLD_DAYS = 14


# ═══════════════════════════════════════════════════════════════════════════
# 1. COLD-CHAIN BREACH DETECTION
# ═══════════════════════════════════════════════════════════════════════════

def detect_cold_chain_breaches(db: Session) -> List[ColdChainBreach]:
    """
    Scan all temperature logs and return every breach event where the
    recorded temperature fell outside the 2 °C – 8 °C safe window.
    """
    breach_logs = (
        db.query(TemperatureLog)
        .filter(TemperatureLog.is_breach == True)  # noqa: E712
        .all()
    )

    breaches: List[ColdChainBreach] = []
    for log in breach_logs:
        batch = db.query(VaccineBatch).get(log.batch_id)
        if batch is None:
            continue
        clinic = db.query(Clinic).get(batch.clinic_id)

        if log.temperature_celsius < COLD_CHAIN_MIN_C:
            breach_type = f"Below Range (<{COLD_CHAIN_MIN_C}°C)"
        else:
            breach_type = f"Above Range (>{COLD_CHAIN_MAX_C}°C)"

        breaches.append(
            ColdChainBreach(
                batch_id=batch.id,
                batch_code=batch.batch_code,
                vaccine_name=batch.vaccine_name,
                clinic_name=clinic.name if clinic else "Unknown",
                breach_temperature=log.temperature_celsius,
                recorded_at=log.recorded_at,
                breach_type=breach_type,
            )
        )

    return breaches


# ═══════════════════════════════════════════════════════════════════════════
# 2. EXPIRATION RISK & FINANCIAL LEAKAGE CALCULATION
# ═══════════════════════════════════════════════════════════════════════════

def _estimate_daily_consumption(batch: VaccineBatch) -> float:
    """
    Derive an empirical daily consumption rate from observed inventory
    depletion:  (initial_qty - current_qty) / days_in_service.
    Falls back to a conservative estimate if data is insufficient.
    """
    days_in_service = (date.today() - batch.manufacturing_date).days
    if days_in_service <= 0:
        return 0.0

    doses_consumed = batch.initial_quantity - batch.quantity_doses
    if doses_consumed < 0:
        doses_consumed = 0

    return round(doses_consumed / days_in_service, 2)


def compute_risk_profiles(db: Session) -> List[BatchRiskProfile]:
    """
    For every active vaccine batch, compute:
      • Days-to-Expiry (DTE)
      • Projected waste (doses that won't be consumed before expiry)
      • Financial leakage ($)
      • Risk tier assignment
    """
    active_batches = (
        db.query(VaccineBatch)
        .filter(VaccineBatch.status == "active")
        .all()
    )

    profiles: List[BatchRiskProfile] = []
    today = date.today()

    for batch in active_batches:
        clinic = db.query(Clinic).get(batch.clinic_id)
        dte = (batch.expiry_date - today).days
        daily_rate = _estimate_daily_consumption(batch)

        # Projected doses consumed before expiry
        projected_consumed = int(daily_rate * max(dte, 0))
        projected_waste = max(0, batch.quantity_doses - projected_consumed)
        leakage_usd = round(projected_waste * batch.unit_cost_usd, 2)

        # Risk tier classification
        if dte < 0:
            risk_tier = "Expired"
        elif dte <= HIGH_RISK_THRESHOLD_DAYS or projected_waste > batch.quantity_doses * 0.5:
            risk_tier = "High Spoilage Risk"
        elif dte <= NEAR_EXPIRY_THRESHOLD_DAYS:
            risk_tier = "Near-Expiry Warning"
        else:
            risk_tier = "Optimal"

        profiles.append(
            BatchRiskProfile(
                batch_id=batch.id,
                batch_code=batch.batch_code,
                vaccine_name=batch.vaccine_name,
                clinic_name=clinic.name if clinic else "Unknown",
                region=clinic.region if clinic else "Unknown",
                quantity_doses=batch.quantity_doses,
                days_to_expiry=dte,
                expiry_date=batch.expiry_date,
                daily_consumption_rate=daily_rate,
                projected_waste_doses=projected_waste,
                financial_leakage_usd=leakage_usd,
                risk_tier=risk_tier,
                cold_chain_intact=batch.cold_chain_intact,
            )
        )

    return profiles


# ═══════════════════════════════════════════════════════════════════════════
# 3. AUTOMATED REDISTRIBUTION OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════

def _compute_clinic_demand_balance(
    profiles: List[BatchRiskProfile],
) -> Tuple[Dict[str, List[BatchRiskProfile]], List[str]]:
    """
    Partition clinics into surplus (holding near-expiry stock) and
    deficit (low inventory or high consumption rate) categories.

    Returns:
      surplus_map   — {clinic_name: [profiles with excess near-expiry stock]}
      deficit_clinics — [clinic names that could absorb more doses]
    """
    # Aggregate per-clinic metrics
    clinic_inventory: Dict[str, int] = {}
    clinic_consumption: Dict[str, float] = {}
    clinic_region: Dict[str, str] = {}

    surplus_map: Dict[str, List[BatchRiskProfile]] = {}

    for p in profiles:
        clinic_inventory[p.clinic_name] = (
            clinic_inventory.get(p.clinic_name, 0) + p.quantity_doses
        )
        clinic_consumption[p.clinic_name] = (
            clinic_consumption.get(p.clinic_name, 0.0) + p.daily_consumption_rate
        )
        clinic_region[p.clinic_name] = p.region

        # Near-expiry with remaining stock → surplus candidate
        if p.risk_tier in ("High Spoilage Risk", "Near-Expiry Warning") and p.quantity_doses > 50:
            surplus_map.setdefault(p.clinic_name, []).append(p)

    # Identify deficit clinics: low stock relative to consumption
    deficit_clinics: List[str] = []
    for clinic_name, total_doses in clinic_inventory.items():
        daily = clinic_consumption.get(clinic_name, 1.0)
        if daily > 0:
            days_of_supply = total_doses / daily
        else:
            days_of_supply = 999

        # A clinic with fewer than 30 days of supply is a deficit candidate
        if days_of_supply < 30 and clinic_name not in surplus_map:
            deficit_clinics.append(clinic_name)

    return surplus_map, deficit_clinics


def generate_redistribution_plan(
    profiles: List[BatchRiskProfile],
) -> List[RedistributionRecommendation]:
    """
    Match surplus clinics (holding near-expiry stock) with deficit clinics
    (facing stockout risk) to propose optimal dose transfers.

    Algorithm:
      1. Rank surplus batches by urgency (lowest DTE first).
      2. For each surplus batch, find the nearest deficit clinic (same region
         preferred, then cross-region).
      3. Propose a transfer of min(surplus, deficit_need) doses.
    """
    surplus_map, deficit_clinics = _compute_clinic_demand_balance(profiles)

    recommendations: List[RedistributionRecommendation] = []

    if not deficit_clinics:
        # If no explicit deficit clinics, still recommend redistributions
        # between surplus clinics and clinics with "Optimal" stock that
        # could absorb more to accelerate consumption.
        optimal_clinics = list({
            p.clinic_name for p in profiles
            if p.risk_tier == "Optimal"
            and p.daily_consumption_rate > 20  # only high-throughput clinics
        })
        deficit_clinics = optimal_clinics[:5]  # limit to top 5

    # Flatten and sort surplus batches by DTE ascending (most urgent first)
    surplus_batches: List[Tuple[str, BatchRiskProfile]] = []
    for clinic_name, batch_profiles in surplus_map.items():
        for bp in batch_profiles:
            surplus_batches.append((clinic_name, bp))

    surplus_batches.sort(key=lambda x: x[1].days_to_expiry)

    # Greedy matching
    deficit_idx = 0
    for source_clinic, bp in surplus_batches:
        if deficit_idx >= len(deficit_clinics):
            deficit_idx = 0  # wrap around
        if not deficit_clinics:
            break

        dest_clinic = deficit_clinics[deficit_idx]
        deficit_idx += 1

        # Transfer up to 70% of surplus (keep some buffer at source)
        transfer_qty = max(50, int(bp.quantity_doses * 0.7))

        # Priority assignment
        if bp.days_to_expiry <= 7:
            priority = "Critical"
        elif bp.days_to_expiry <= 14:
            priority = "High"
        else:
            priority = "Medium"

        dest_region = next(
            (p.region for p in profiles if p.clinic_name == dest_clinic),
            "Unknown",
        )

        recommendations.append(
            RedistributionRecommendation(
                source_clinic=source_clinic,
                source_region=bp.region,
                destination_clinic=dest_clinic,
                destination_region=dest_region,
                vaccine_name=bp.vaccine_name,
                batch_code=bp.batch_code,
                transfer_quantity=transfer_qty,
                days_to_expiry=bp.days_to_expiry,
                financial_value_usd=round(transfer_qty * (bp.financial_leakage_usd / max(bp.quantity_doses, 1)), 2),
                priority=priority,
                rationale=(
                    f"{source_clinic} holds {bp.quantity_doses:,} doses of {bp.vaccine_name} "
                    f"expiring in {bp.days_to_expiry} days. Transferring {transfer_qty:,} doses "
                    f"to {dest_clinic} can prevent ${transfer_qty * bp.financial_leakage_usd / max(bp.quantity_doses, 1):,.0f} "
                    f"in potential waste."
                ),
            )
        )

    return recommendations


# ═══════════════════════════════════════════════════════════════════════════
# 4. FULL AUDIT REPORT ASSEMBLY
# ═══════════════════════════════════════════════════════════════════════════

def run_full_audit(db: Session) -> AuditReport:
    """
    Execute the complete audit pipeline and return a unified report:
      1. Detect cold-chain breaches
      2. Compute batch risk profiles + financial leakage
      3. Generate redistribution recommendations
      4. Aggregate KPI summary
    """
    # Phase 1 — Cold-chain
    breaches = detect_cold_chain_breaches(db)

    # Phase 2 — Risk & leakage
    profiles = compute_risk_profiles(db)

    # Phase 3 — Redistribution
    redistribution_plan = generate_redistribution_plan(profiles)

    # Phase 4 — KPI aggregation
    total_doses = sum(p.quantity_doses for p in profiles)
    total_value = sum(p.quantity_doses * (p.financial_leakage_usd / max(p.projected_waste_doses, 1))
                      for p in profiles if p.projected_waste_doses > 0)
    # Recalculate total value more accurately
    total_value = 0.0
    for p in profiles:
        # Value = current stock × unit cost (derived from leakage / waste)
        if p.projected_waste_doses > 0:
            unit_cost = p.financial_leakage_usd / p.projected_waste_doses
        else:
            unit_cost = 0.0
        total_value += p.quantity_doses * unit_cost

    total_leakage = sum(p.financial_leakage_usd for p in profiles)
    total_leakage_doses = sum(p.projected_waste_doses for p in profiles)

    high_risk = sum(1 for p in profiles if p.risk_tier == "High Spoilage Risk")
    near_expiry = sum(1 for p in profiles if p.risk_tier == "Near-Expiry Warning")
    optimal = sum(1 for p in profiles if p.risk_tier == "Optimal")

    # Unique breached batches
    breached_batch_ids = {b.batch_id for b in breaches}

    # Clinics with less than 15 days of supply
    clinic_doses: Dict[str, int] = {}
    clinic_consumption: Dict[str, float] = {}
    for p in profiles:
        clinic_doses[p.clinic_name] = clinic_doses.get(p.clinic_name, 0) + p.quantity_doses
        clinic_consumption[p.clinic_name] = (
            clinic_consumption.get(p.clinic_name, 0.0) + p.daily_consumption_rate
        )
    stockout_risk = sum(
        1 for c, d in clinic_doses.items()
        if clinic_consumption.get(c, 1) > 0 and d / clinic_consumption[c] < 15
    )

    kpi = KPISummary(
        total_active_inventory_doses=total_doses,
        total_active_inventory_value_usd=round(total_value, 2),
        total_projected_leakage_usd=round(total_leakage, 2),
        total_leakage_doses=total_leakage_doses,
        active_cold_chain_breaches=len(breached_batch_ids),
        batches_at_high_risk=high_risk,
        batches_near_expiry_warning=near_expiry,
        batches_optimal=optimal,
        clinics_with_stockout_risk=stockout_risk,
        redistribution_opportunities=len(redistribution_plan),
    )

    return AuditReport(
        kpi_summary=kpi,
        risk_profiles=profiles,
        cold_chain_breaches=breaches,
        redistribution_plan=redistribution_plan,
    )
