import pandas as pd
import numpy as np

# CPCB/IPCC Standard Emission Factors (grams per km per vehicle)
# Sources: CPCB India vehicular emission standards & ARAI emission profiles
EMISSION_FACTORS = {
    "2-Wheeler (Bike/Scooter)": {
        "Petrol": {"CO2": 35.0, "NOx": 0.15, "PM2.5": 0.02, "CO": 1.20},
        "EV": {"CO2": 0.0, "NOx": 0.0, "PM2.5": 0.0, "CO": 0.0}
    },
    "3-Wheeler (Auto/E-Rickshaw)": {
        "CNG": {"CO2": 45.0, "NOx": 0.20, "PM2.5": 0.01, "CO": 0.50},
        "Petrol": {"CO2": 55.0, "NOx": 0.30, "PM2.5": 0.03, "CO": 1.50},
        "LPG": {"CO2": 48.0, "NOx": 0.22, "PM2.5": 0.015, "CO": 0.60},
        "EV": {"CO2": 0.0, "NOx": 0.0, "PM2.5": 0.0, "CO": 0.0}
    },
    "4-Wheeler (Car/Cab)": {
        "Petrol": {"CO2": 140.0, "NOx": 0.40, "PM2.5": 0.03, "CO": 1.80},
        "Diesel": {"CO2": 165.0, "NOx": 0.85, "PM2.5": 0.12, "CO": 0.90},
        "CNG": {"CO2": 110.0, "NOx": 0.25, "PM2.5": 0.01, "CO": 0.40},
        "EV": {"CO2": 0.0, "NOx": 0.0, "PM2.5": 0.0, "CO": 0.0}
    },
    "Bus (DTC/Private)": {
        "CNG": {"CO2": 650.0, "NOx": 3.50, "PM2.5": 0.15, "CO": 2.10},
        "Electric Bus": {"CO2": 0.0, "NOx": 0.0, "PM2.5": 0.0, "CO": 0.0},
        "Diesel": {"CO2": 820.0, "NOx": 7.20, "PM2.5": 0.65, "CO": 3.50}
    },
    "Heavy Vehicle (Truck/LVC)": {
        "Diesel": {"CO2": 950.0, "NOx": 8.80, "PM2.5": 0.85, "CO": 4.20},
        "CNG": {"CO2": 720.0, "NOx": 4.10, "PM2.5": 0.18, "CO": 2.50}
    }
}

# Default Fuel Mix percentage distribution across vehicle types in Delhi
DEFAULT_FUEL_MIX = {
    "2-Wheeler (Bike/Scooter)": {"Petrol": 0.85, "EV": 0.15},
    "3-Wheeler (Auto/E-Rickshaw)": {"CNG": 0.60, "EV": 0.30, "Petrol": 0.05, "LPG": 0.05},
    "4-Wheeler (Car/Cab)": {"Petrol": 0.50, "Diesel": 0.25, "CNG": 0.20, "EV": 0.05},
    "Bus (DTC/Private)": {"CNG": 0.70, "Electric Bus": 0.25, "Diesel": 0.05},
    "Heavy Vehicle (Truck/LVC)": {"Diesel": 0.80, "CNG": 0.20}
}

# Default vehicle composition in typical Delhi traffic stream
DEFAULT_VEHICLE_SPLIT = {
    "2-Wheeler (Bike/Scooter)": 0.45,
    "4-Wheeler (Car/Cab)": 0.35,
    "3-Wheeler (Auto/E-Rickshaw)": 0.12,
    "Bus (DTC/Private)": 0.05,
    "Heavy Vehicle (Truck/LVC)": 0.03
}

def calculate_emissions_for_dataframe(df, fuel_mix=None, avg_trip_km=5.0):
    """
    Takes dataframe with total vehicle count and calculates:
    - Per-vehicle category counts
    - Fuel-wise counts
    - Per-vehicle emission breakdown
    - Total emissions (CO2 in kg, NOx, PM2.5, CO in grams)
    """
    if fuel_mix is None:
        fuel_mix = DEFAULT_FUEL_MIX

    records = []
    
    for idx, row in df.iterrows():
        total_vehicles = row['vehicle_count']
        congestion = row.get('congestion_level', 1.0) # multiplier factor for idling traffic
        
        # Congestion emission penalty (slower/stop-and-go traffic increases emissions up to 1.4x)
        congestion_multiplier = 1.0 + (congestion - 1.0) * 0.3 if congestion > 1.0 else 1.0
        
        for v_type, v_prop in DEFAULT_VEHICLE_SPLIT.items():
            v_count = int(total_vehicles * v_prop)
            fuels = fuel_mix.get(v_type, {})
            
            for fuel_type, fuel_prop in fuels.items():
                v_fuel_count = int(v_count * fuel_prop)
                ef = EMISSION_FACTORS.get(v_type, {}).get(fuel_type, {"CO2": 0, "NOx": 0, "PM2.5": 0, "CO": 0})
                
                # Distance traveled = v_fuel_count * avg_trip_km
                total_km = v_fuel_count * avg_trip_km
                
                co2_kg = (total_km * ef["CO2"] * congestion_multiplier) / 1000.0
                nox_g = total_km * ef["NOx"] * congestion_multiplier
                pm25_g = total_km * ef["PM2.5"] * congestion_multiplier
                co_g = total_km * ef["CO"] * congestion_multiplier
                
                # Per vehicle rates
                per_veh_co2_g_km = ef["CO2"] * congestion_multiplier
                per_veh_nox_g_km = ef["NOx"] * congestion_multiplier
                per_veh_pm25_g_km = ef["PM2.5"] * congestion_multiplier
                
                records.append({
                    "date": row['date'],
                    "district": row['district'],
                    "place": row['place'],
                    "hour": row.get('hour', 12),
                    "vehicle_type": v_type,
                    "fuel_type": fuel_type,
                    "vehicle_count": v_fuel_count,
                    "trip_km": avg_trip_km,
                    "co2_kg": co2_kg,
                    "nox_g": nox_g,
                    "pm25_g": pm25_g,
                    "co_g": co_g,
                    "per_veh_co2_g_km": per_veh_co2_g_km,
                    "per_veh_nox_g_km": per_veh_nox_g_km,
                    "per_veh_pm25_g_km": per_veh_pm25_g_km
                })
                
    return pd.DataFrame(records)

# --- CPCB AQI CALCULATION MODULE ---
# Breakpoints for Indian National Air Quality Index (NAQI - CPCB)
AQI_BREAKPOINTS = {
    "PM2.5": [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (250, 500, 401, 500)
    ],
    "NO2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 180, 101, 200),
        (181, 280, 201, 300),
        (281, 400, 301, 400),
        (400, 800, 401, 500)
    ],
    "CO": [
        (0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.0, 50.0, 401, 500)
    ]
}

def calculate_sub_index(conc, pollutant):
    """
    Calculates sub-index for a pollutant using linear piecewise interpolation:
    Ip = I_low + ((I_high - I_low) / (B_high - B_low)) * (C - B_low)
    """
    if pollutant not in AQI_BREAKPOINTS:
        return 0.0
    
    breakpoints = AQI_BREAKPOINTS[pollutant]
    for b_low, b_high, i_low, i_high in breakpoints:
        if b_low <= conc <= b_high:
            sub_index = i_low + ((i_high - i_low) / (b_high - b_low)) * (conc - b_low)
            return round(sub_index, 1)
            
    # Handle concentration beyond maximum table value
    max_b_low, max_b_high, max_i_low, max_i_high = breakpoints[-1]
    if conc > max_b_high:
        return 500.0
    return 0.0

def get_aqi_category(aqi_val):
    """Returns Indian CPCB AQI Category and Hex Color Code."""
    if aqi_val <= 50:
        return "Good", "#10B981"
    elif aqi_val <= 100:
        return "Satisfactory", "#84CC16"
    elif aqi_val <= 200:
        return "Moderate", "#F59E0B"
    elif aqi_val <= 300:
        return "Poor", "#F97316"
    elif aqi_val <= 400:
        return "Very Poor", "#EF4444"
    else:
        return "Severe", "#881337"

def calculate_aqi_from_emissions(pm25_ug_m3, no2_ug_m3, co_mg_m3):
    """
    Calculates individual pollutant sub-indices and overall AQI (Max sub-index).
    """
    sub_pm25 = calculate_sub_index(pm25_ug_m3, "PM2.5")
    sub_no2 = calculate_sub_index(no2_ug_m3, "NO2")
    sub_co = calculate_sub_index(co_mg_m3, "CO")
    
    overall_aqi = max(sub_pm25, sub_no2, sub_co)
    category, color = get_aqi_category(overall_aqi)
    
    return {
        "aqi": round(overall_aqi, 1),
        "category": category,
        "color": color,
        "sub_pm25": sub_pm25,
        "sub_no2": sub_no2,
        "sub_co": sub_co,
        "prominent_pollutant": "PM2.5" if overall_aqi == sub_pm25 else ("NO2" if overall_aqi == sub_no2 else "CO")
    }

