"""
training/upgrade_with_real_data.py
------------------------------------
Reads the real IMD district-wise rainfall normal CSV and prints the
corrected avg_monsoon_rainfall_mm values for each of our 15 seed zones.

Run this ONCE, then manually paste the values into build_dataset.py SEED_ZONES,
then re-run build_dataset.py and train_model.py.

Usage:
    cd module2-risk-engine
    python training/upgrade_with_real_data.py
"""

import os
import sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DISTRICT_CSV = os.path.join(
    ROOT, "data", "raw", "Rainfall dataset", "district wise rainfall normal.csv"
)

# ── Mapping: our pincode → (STATE_UT_NAME, DISTRICT) in the CSV ──────────────
ZONE_DISTRICT_MAP: dict[str, tuple[str, str]] = {
    "600017": ("TAMIL NADU",   "CHENNAI"),
    "600020": ("TAMIL NADU",   "CHENNAI"),
    "600032": ("TAMIL NADU",   "CHENNAI"),
    "600028": ("TAMIL NADU",   "CHENNAI"),
    "400017": ("MAHARASHTRA",  "MUMBAI CITY"),
    "400050": ("MAHARASHTRA",  "MUMBAI CITY"),
    "400069": ("MAHARASHTRA",  "THANE"),
    "560034": ("KARNATAKA",    "BANGALORE URB"),
    "560011": ("KARNATAKA",    "BANGALORE URB"),
    "560095": ("KARNATAKA",    "BANGALORE URB"),
    "110001": ("DELHI",        "CENTRAL DELHI"),
    "110019": ("DELHI",        "SOUTH DELHI"),
    "110045": ("DELHI",        "SW DELHI"),
    "411038": ("MAHARASHTRA",  "PUNE"),
    "411001": ("MAHARASHTRA",  "PUNE"),
}

ZONE_AREAS: dict[str, str] = {
    "600017": "T. Nagar, Chennai",
    "600020": "Adyar, Chennai",
    "600032": "Velachery, Chennai",
    "600028": "Mylapore, Chennai",
    "400017": "Dharavi, Mumbai",
    "400050": "Bandra West, Mumbai",
    "400069": "Andheri, Mumbai",
    "560034": "Koramangala, Bangalore",
    "560011": "Jayanagar, Bangalore",
    "560095": "HSR Layout, Bangalore",
    "110001": "Connaught Place, Delhi",
    "110019": "South Delhi",
    "110045": "Dwarka, Delhi",
    "411038": "Kothrud, Pune",
    "411001": "Shivajinagar, Pune",
}

# ── Values currently in build_dataset.py (pre-upgrade estimates) ─────────────
CURRENT_ESTIMATES: dict[str, float] = {
    "600017": 180, "600020": 170, "600032": 200, "600028": 150,
    "400017": 950, "400050": 850, "400069": 900,
    "560034": 120, "560011": 115, "560095": 125,
    "110001": 220, "110019": 200, "110045": 210,
    "411038": 400, "411001": 420,
}


def load_district_monsoon(csv_path: str) -> dict[tuple[str, str], float]:
    """
    Parses the district CSV and returns a dict:
        (STATE_UT_NAME_UPPER, DISTRICT_UPPER) -> Jun-Sep rainfall (mm)
    """
    df = pd.read_csv(csv_path)
    result: dict[tuple[str, str], float] = {}
    for _, row in df.iterrows():
        try:
            state = str(row["STATE_UT_NAME"]).strip().upper()
            dist  = str(row["DISTRICT"]).strip().upper()
            val   = float(row["Jun-Sep"])
            result[(state, dist)] = val
        except (ValueError, KeyError):
            continue
    return result


def main() -> None:
    if not os.path.exists(DISTRICT_CSV):
        print(f"ERROR: District CSV not found at:\n  {DISTRICT_CSV}")
        sys.exit(1)

    print(f"Loading: {DISTRICT_CSV}")
    district_data = load_district_monsoon(DISTRICT_CSV)
    print(f"Loaded {len(district_data)} district records.\n")

    print(
        f"{'Pincode':<10} {'Area':<28} {'Old (est.)':<12} {'New (IMD)':<12} {'Delta':>8}"
    )
    print("-" * 72)

    corrections: dict[str, float] = {}
    for pincode, area in ZONE_AREAS.items():
        state, district = ZONE_DISTRICT_MAP[pincode]
        key = (state.upper(), district.upper())
        real = district_data.get(key)
        if real is None:
            # Try partial match (district names can have truncation in CSV)
            for (s, d), v in district_data.items():
                if s == state.upper() and district.upper() in d:
                    real = v
                    break
        old = CURRENT_ESTIMATES[pincode]
        if real is not None:
            corrections[pincode] = real
            delta = real - old
            sign  = "+" if delta >= 0 else ""
            print(
                f"{pincode:<10} {area:<28} {old:<12.0f} {real:<12.0f} "
                f"{sign}{delta:>6.0f}"
            )
        else:
            corrections[pincode] = old
            print(
                f"{pincode:<10} {area:<28} {old:<12.0f} {'NOT FOUND':<12} {'  N/A':>8}"
            )

    print("\n" + "=" * 72)
    print("Paste these corrected values into build_dataset.py SEED_ZONES:\n")
    print("# avg_monsoon_rainfall_mm corrections from IMD district normals:")
    for pincode, val in corrections.items():
        print(f"    # {ZONE_AREAS[pincode]}: old={CURRENT_ESTIMATES[pincode]:.0f} -> new={val:.0f}")
    print()
    print("After updating build_dataset.py, run:")
    print("    python training/build_dataset.py")
    print("    python training/train_model.py")


if __name__ == "__main__":
    main()
