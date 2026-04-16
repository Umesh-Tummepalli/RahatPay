"""Explore real raw data to understand what features we can extract for each city."""
import pandas as pd
import pickle
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw")

# 1. IMD District Rainfall Normals
print("=" * 60)
print("1. IMD DISTRICT RAINFALL NORMALS")
print("=" * 60)
df_rain = pd.read_csv(os.path.join(RAW, "Rainfall dataset", "district wise rainfall normal.csv"))
targets = ["CHENNAI", "MUMBAI", "BANGALORE", "DELHI", "PUNE", "THANE"]
for t in targets:
    match = df_rain[df_rain["DISTRICT"].str.contains(t, case=False, na=False)]
    for _, r in match.iterrows():
        print(f"  {r['STATE_UT_NAME']}/{r['DISTRICT']}: Jun-Sep={r['Jun-Sep']}mm, Oct-Dec={r['Oct-Dec']}mm, Annual={r['ANNUAL']}mm")

# 2. Historical Rainfall 1901-2015
print("\n" + "=" * 60)
print("2. HISTORICAL RAINFALL (1901-2015)")
print("=" * 60)
df_hist = pd.read_csv(os.path.join(RAW, "Rainfall dataset", "rainfall in india 1901-2015.csv"))
subdiv_map = {
    "Chennai": "TAMIL NADU",
    "Mumbai": "KONKAN & GOA",
    "Bangalore": "SOUTH INTERIOR KARNATAKA",
    "Delhi": "DELHI",
    "Pune": "MADHYA MAHARASHTRA",
}
for city, subdiv in subdiv_map.items():
    sub = df_hist[df_hist["SUBDIVISION"].str.contains(subdiv, case=False, na=False)]
    if len(sub) > 0:
        monsoon = sub["Jun-Sep"].dropna()
        # Count years with extreme monsoon rainfall (> mean + 1.5*std)
        threshold = monsoon.mean() + 1.5 * monsoon.std()
        extreme_years = (monsoon > threshold).sum()
        print(f"  {city} ({subdiv}): {len(sub)} years, Avg monsoon={monsoon.mean():.0f}mm, Extreme years={extreme_years}, Max={monsoon.max():.0f}mm")

# 3. EM-DAT Disasters
print("\n" + "=" * 60)
print("3. EM-DAT INDIA DISASTERS")
print("=" * 60)
df_dis = pd.read_csv(os.path.join(RAW, "disasterIND.csv"))
print(f"  Total events: {len(df_dis)}")
print(f"  Disaster types: {df_dis['Disaster Type'].value_counts().head(8).to_dict()}")
# Filter floods
floods = df_dis[df_dis["Disaster Type"].str.contains("Flood", case=False, na=False)]
print(f"  Flood events: {len(floods)}")
# Find floods mentioning our cities in Location column
for city in ["Chennai", "Mumbai", "Delhi", "Bangalore", "Pune"]:
    city_floods = floods[floods["Location"].str.contains(city, case=False, na=False)]
    print(f"    {city} floods: {len(city_floods)}")

# 4. Real CPCB AQI Data
print("\n" + "=" * 60)
print("4. CPCB AQI DATA (main_data.pkl)")
print("=" * 60)
df_aqi = pickle.load(open(os.path.join(RAW, "main_data.pkl"), "rb"))
print(f"  Total rows: {len(df_aqi)}")
print(f"  Date range: {df_aqi['Timestamp'].min()} to {df_aqi['Timestamp'].max()}")
for city in ["Chennai", "Mumbai", "Delhi", "Bengaluru", "Pune"]:
    sub = df_aqi[df_aqi["city"].str.contains(city, case=False, na=False)]
    pm25 = sub["PM2.5"].dropna()
    if len(pm25) > 0:
        # Indian AQI: poor > 200 (PM2.5 > ~80ug/m3), severe > 300 (PM2.5 > ~120)
        days_poor = (pm25 > 80).sum()
        days_severe = (pm25 > 120).sum()
        n_stations = sub["station"].nunique()
        n_years = pd.to_datetime(sub["Timestamp"]).dt.year.nunique()
        days_per_station_per_year = days_poor / max(n_stations, 1) / max(n_years, 1)
        print(f"  {city}: {n_stations} stations, {n_years} years, mean PM2.5={pm25.mean():.1f}, "
              f"readings>80={days_poor}, readings>120={days_severe}, "
              f"~{days_per_station_per_year:.0f} exceedance readings/station/year")
