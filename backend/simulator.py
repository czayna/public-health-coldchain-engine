"""
simulator.py — Realistic Mock Operational Data Generator
=========================================================
Generates production-realistic synthetic data for the cold-chain engine:
  • 15 regional clinics/warehouses across diverse geographies
  • 200+ vaccine batches with realistic manufacturers, costs, and shelf lives
  • 10,000+ time-series temperature readings with intentional breach injection
  • Consumption patterns that create natural surplus/deficit imbalances

Run directly:  python -m backend.simulator
Or import:     from backend.simulator import populate_database

Author: Portfolio Project
"""

import random
from datetime import date, datetime, timedelta

from backend.database import SessionLocal, init_db, Clinic, VaccineBatch, TemperatureLog

# ---------------------------------------------------------------------------
# Configuration Constants
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Realistic vaccine catalog with WHO-aligned pricing
VACCINE_CATALOG = [
    {"name": "Pfizer-BioNTech COVID-19 (Comirnaty)", "manufacturer": "Pfizer Inc.", "unit_cost": 19.50, "shelf_life_days": 270},
    {"name": "Moderna COVID-19 (Spikevax)", "manufacturer": "Moderna Inc.", "unit_cost": 25.50, "shelf_life_days": 270},
    {"name": "AstraZeneca COVID-19 (Vaxzevria)", "manufacturer": "AstraZeneca PLC", "unit_cost": 4.00, "shelf_life_days": 180},
    {"name": "Janssen COVID-19 (Ad26.COV2.S)", "manufacturer": "Johnson & Johnson", "unit_cost": 10.00, "shelf_life_days": 330},
    {"name": "Influenza Quadrivalent (Fluzone)", "manufacturer": "Sanofi Pasteur", "unit_cost": 18.00, "shelf_life_days": 365},
    {"name": "Measles-Mumps-Rubella (M-M-R II)", "manufacturer": "Merck & Co.", "unit_cost": 22.00, "shelf_life_days": 730},
    {"name": "Hepatitis B (Engerix-B)", "manufacturer": "GlaxoSmithKline", "unit_cost": 14.50, "shelf_life_days": 540},
    {"name": "Polio Inactivated (IPOL)", "manufacturer": "Sanofi Pasteur", "unit_cost": 12.00, "shelf_life_days": 540},
    {"name": "HPV Quadrivalent (Gardasil 9)", "manufacturer": "Merck & Co.", "unit_cost": 178.00, "shelf_life_days": 1095},
    {"name": "Tetanus-Diphtheria (Td Vaccine)", "manufacturer": "MassBiologics", "unit_cost": 8.50, "shelf_life_days": 730},
    {"name": "Pneumococcal (Prevnar 20)", "manufacturer": "Pfizer Inc.", "unit_cost": 230.00, "shelf_life_days": 730},
    {"name": "Rotavirus (RotaTeq)", "manufacturer": "Merck & Co.", "unit_cost": 75.00, "shelf_life_days": 730},
]

# Realistic facility network — Philippine DOH Regional Health Facilities
# Based on actual DOH regional structure and real city coordinates
FACILITY_NETWORK = [
    # ── NCR (National Capital Region) ──
    {"name": "DOH NCR Central Vaccine Depot, Manila",          "region": "NCR",          "lat": 14.5995, "lon": 120.9842, "capacity": 250_000, "type": "warehouse"},
    {"name": "Philippine General Hospital, Ermita",             "region": "NCR",          "lat": 14.5764, "lon": 120.9851, "capacity": 80_000,  "type": "hospital"},
    {"name": "Quezon City Health Office, Diliman",              "region": "NCR",          "lat": 14.6507, "lon": 121.0495, "capacity": 60_000,  "type": "clinic"},

    # ── CAR (Cordillera Administrative Region) ──
    {"name": "Baguio General Hospital, Baguio City",            "region": "CAR",          "lat": 16.4023, "lon": 120.5960, "capacity": 35_000,  "type": "hospital"},
    {"name": "Mountain Province District Health Office",        "region": "CAR",          "lat": 17.0833, "lon": 121.1000, "capacity": 12_000,  "type": "clinic"},

    # ── Region I (Ilocos Region) ──
    {"name": "Mariano Marcos Memorial Hospital, Batac",         "region": "Region I",     "lat": 18.0551, "lon": 120.5649, "capacity": 40_000,  "type": "hospital"},

    # ── Region III (Central Luzon) ──
    {"name": "DOH Region III Warehouse, San Fernando",          "region": "Region III",   "lat": 15.0286, "lon": 120.6900, "capacity": 100_000, "type": "warehouse"},
    {"name": "Jose B. Lingad Memorial Hospital, San Fernando",  "region": "Region III",   "lat": 15.0286, "lon": 120.6937, "capacity": 50_000,  "type": "hospital"},

    # ── Region IV-A (CALABARZON) ──
    {"name": "DOH CALABARZON Cold Storage Hub, Calamba",        "region": "CALABARZON",   "lat": 14.2114, "lon": 121.1653, "capacity": 90_000,  "type": "warehouse"},
    {"name": "Batangas Provincial Health Office, Batangas City", "region": "CALABARZON",  "lat": 13.7565, "lon": 121.0583, "capacity": 30_000,  "type": "clinic"},

    # ── Region V (Bicol Region) ──
    {"name": "Bicol Regional Training & Teaching Hospital, Legazpi", "region": "Region V", "lat": 13.1391, "lon": 123.7438, "capacity": 45_000, "type": "hospital"},

    # ── Region VI (Western Visayas) ──
    {"name": "Western Visayas Medical Center, Iloilo City",     "region": "Region VI",    "lat": 10.7202, "lon": 122.5621, "capacity": 55_000,  "type": "hospital"},

    # ── Region VII (Central Visayas) ──
    {"name": "Vicente Sotto Memorial Medical Center, Cebu City","region": "Region VII",   "lat": 10.3157, "lon": 123.8854, "capacity": 65_000,  "type": "hospital"},
    {"name": "Bohol Provincial Health Office, Tagbilaran",      "region": "Region VII",   "lat": 9.6500,  "lon": 123.8500, "capacity": 22_000,  "type": "clinic"},

    # ── Region X (Northern Mindanao) ──
    {"name": "Northern Mindanao Medical Center, Cagayan de Oro","region": "Region X",     "lat": 8.4542,  "lon": 124.6319, "capacity": 50_000,  "type": "hospital"},

    # ── Region XI (Davao Region) ──
    {"name": "Southern Philippines Medical Center, Davao City", "region": "Region XI",    "lat": 7.0731,  "lon": 125.6128, "capacity": 70_000,  "type": "hospital"},
    {"name": "Davao Regional Health Office Clinic, Tagum",      "region": "Region XI",    "lat": 7.4478,  "lon": 125.8078, "capacity": 25_000,  "type": "clinic"},

    # ── BARMM (Bangsamoro Autonomous Region in Muslim Mindanao) ──
    {"name": "Amai Pakpak Medical Center, Marawi City",         "region": "BARMM",        "lat": 7.9986,  "lon": 124.2928, "capacity": 18_000,  "type": "hospital"},

    # ── Region XIII (Caraga) ──
    {"name": "Caraga Regional Hospital, Butuan City",           "region": "Caraga",       "lat": 8.9475,  "lon": 125.5406, "capacity": 30_000,  "type": "hospital"},
]



def _generate_batch_code(index: int) -> str:
    """Produce a realistic pharmaceutical batch code, e.g., VAX-2026-00042."""
    return f"VAX-2026-{index:05d}"


def _simulate_consumption(initial_qty: int, days_since_receipt: int, clinic_type: str) -> int:
    """
    Estimate how many doses have been consumed since the batch arrived.
    Warehouses consume slowly (they redistribute); hospitals consume fastest.
    """
    if clinic_type == "warehouse":
        daily_rate = random.uniform(5, 25)  # slow — mostly redistribution hub
    elif clinic_type == "hospital":
        daily_rate = random.uniform(40, 120)
    else:
        daily_rate = random.uniform(15, 60)

    consumed = int(daily_rate * days_since_receipt)
    remaining = max(0, initial_qty - consumed)
    return remaining


def populate_database(session=None):
    """
    Main entry point: seeds the database with realistic synthetic data.
    Returns summary statistics dict.
    """
    close_session = False
    if session is None:
        init_db()
        session = SessionLocal()
        close_session = True

    # ------------------------------------------------------------------
    # 1. Create Clinics / Facilities
    # ------------------------------------------------------------------
    clinics = []
    for fac in FACILITY_NETWORK:
        clinic = Clinic(
            name=fac["name"],
            region=fac["region"],
            latitude=fac["lat"],
            longitude=fac["lon"],
            storage_capacity_doses=fac["capacity"],
            facility_type=fac["type"],
        )
        session.add(clinic)
        clinics.append(clinic)

    session.flush()  # assign IDs without committing

    # ------------------------------------------------------------------
    # 2. Generate Vaccine Batches
    # ------------------------------------------------------------------
    today = date.today()
    batches = []
    batch_index = 1

    for clinic in clinics:
        # Each clinic gets 12–20 batches across various vaccines
        n_batches = random.randint(12, 20)
        for _ in range(n_batches):
            vaccine = random.choice(VACCINE_CATALOG)
            shelf_life = vaccine["shelf_life_days"]

            # Manufacturing date: 30–300 days ago
            days_ago = random.randint(30, min(shelf_life - 10, 300))
            mfg_date = today - timedelta(days=days_ago)
            exp_date = mfg_date + timedelta(days=shelf_life)

            initial_qty = random.choice([500, 1000, 2000, 5000, 10000])
            remaining = _simulate_consumption(initial_qty, days_ago, clinic.facility_type)

            # Determine batch status
            if exp_date < today:
                status = "expired"
                remaining = initial_qty  # expired stock sits unconsumed
            else:
                status = "active"

            batch = VaccineBatch(
                batch_code=_generate_batch_code(batch_index),
                vaccine_name=vaccine["name"],
                manufacturer=vaccine["manufacturer"],
                quantity_doses=remaining,
                initial_quantity=initial_qty,
                unit_cost_usd=vaccine["unit_cost"],
                manufacturing_date=mfg_date,
                expiry_date=exp_date,
                clinic_id=clinic.id,
                cold_chain_intact=True,  # updated after temp log generation
                status=status,
            )
            session.add(batch)
            batches.append(batch)
            batch_index += 1

    session.flush()

    # ------------------------------------------------------------------
    # 3. Generate Temperature Logs (time-series)
    # ------------------------------------------------------------------
    breach_batch_ids = set()

    for batch in batches:
        # 40–80 readings per batch over the past weeks
        n_readings = random.randint(40, 80)
        base_time = datetime.combine(batch.manufacturing_date, datetime.min.time())

        # Decide if this batch will have a temperature breach (~12% chance)
        will_breach = random.random() < 0.12

        for r in range(n_readings):
            # Readings spaced 4–12 hours apart
            offset_hours = random.uniform(4, 12) * r
            recorded_at = base_time + timedelta(hours=offset_hours)
            if recorded_at > datetime.now():
                recorded_at = datetime.now() - timedelta(minutes=random.randint(1, 600))

            if will_breach and r in range(n_readings - 5, n_readings):
                # Inject breach readings near end of series
                if random.random() < 0.5:
                    temp = random.uniform(-2.0, 1.5)   # below range
                else:
                    temp = random.uniform(8.5, 15.0)    # above range
                is_breach = True
                breach_batch_ids.add(batch.id)
            else:
                # Normal reading: 2°C – 8°C with slight noise
                temp = round(random.gauss(5.0, 1.2), 2)
                temp = max(2.0, min(8.0, temp))  # clamp to valid range
                is_breach = False

            temp = round(temp, 2)

            log = TemperatureLog(
                batch_id=batch.id,
                recorded_at=recorded_at,
                temperature_celsius=temp,
                sensor_id=f"SENSOR-{clinic.id:02d}-{random.randint(1, 4):02d}",
                is_breach=is_breach,
            )
            session.add(log)

    # Update cold_chain_intact flag for breached batches
    for batch in batches:
        if batch.id in breach_batch_ids:
            batch.cold_chain_intact = False

    session.commit()

    stats = {
        "clinics_created": len(clinics),
        "batches_created": len(batches),
        "breached_batches": len(breach_batch_ids),
    }

    if close_session:
        session.close()

    return stats


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("🔄 Populating database with realistic mock data …")
    result = populate_database()
    print(f"✅ Done — {result['clinics_created']} clinics, "
          f"{result['batches_created']} batches, "
          f"{result['breached_batches']} cold-chain breaches injected.")
