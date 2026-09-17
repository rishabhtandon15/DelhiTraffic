import pandas as pd
import numpy as np
import datetime

# All 11 Districts of Delhi and prominent places/traffic probe locations
DELHI_DISTRICTS_PLACES = {
    "Central Delhi": [
        {"name": "Connaught Place", "lat": 28.6315, "lon": 77.2167, "base_count": 4500},
        {"name": "ITO Junction", "lat": 28.6288, "lon": 77.2405, "base_count": 5800},
        {"name": "Karol Bagh", "lat": 28.6514, "lon": 77.1907, "base_count": 4200},
        {"name": "Chandni Chowk", "lat": 28.6506, "lon": 77.2303, "base_count": 3900}
    ],
    "New Delhi": [
        {"name": "India Gate Circle", "lat": 28.6129, "lon": 77.2295, "base_count": 5100},
        {"name": "Dhaula Kuan Interchange", "lat": 28.5918, "lon": 77.1617, "base_count": 6200},
        {"name": "Chanakyapuri", "lat": 28.5983, "lon": 77.1930, "base_count": 2800},
        {"name": "Khan Market", "lat": 28.6002, "lon": 77.2270, "base_count": 3100}
    ],
    "South Delhi": [
        {"name": "AIIMS Flyover", "lat": 28.5672, "lon": 77.2100, "base_count": 6400},
        {"name": "Hauz Khas", "lat": 28.5494, "lon": 77.2001, "base_count": 3800},
        {"name": "Saket District Centre", "lat": 28.5244, "lon": 77.2188, "base_count": 4100},
        {"name": "Mehrauli Badarpur Road", "lat": 28.5100, "lon": 77.2250, "base_count": 4700}
    ],
    "South East Delhi": [
        {"name": "Lajpat Nagar Flyover", "lat": 28.5677, "lon": 77.2433, "base_count": 5300},
        {"name": "Nehru Place", "lat": 28.5485, "lon": 77.2514, "base_count": 4900},
        {"name": "Okhla Industrial Area", "lat": 28.5300, "lon": 77.2700, "base_count": 4300},
        {"name": "Ashram Chowk", "lat": 28.5705, "lon": 77.2592, "base_count": 6700}
    ],
    "South West Delhi": [
        {"name": "Dwarka Mor", "lat": 28.6186, "lon": 77.0345, "base_count": 4600},
        {"name": "Vasant Kunj", "lat": 28.5293, "lon": 77.1539, "base_count": 3700},
        {"name": "IGIA Airport Approach", "lat": 28.5562, "lon": 77.1000, "base_count": 5900},
        {"name": "Najafgarh Road", "lat": 28.6090, "lon": 76.9850, "base_count": 3400}
    ],
    "East Delhi": [
        {"name": "Anand Vihar ISBT", "lat": 28.6469, "lon": 77.3160, "base_count": 6100},
        {"name": "Laxmi Nagar Metro", "lat": 28.6304, "lon": 77.2773, "base_count": 4800},
        {"name": "Mayur Vihar Phase 1", "lat": 28.6075, "lon": 77.2940, "base_count": 3900},
        {"name": "Preet Vihar", "lat": 28.6410, "lon": 77.2970, "base_count": 3600}
    ],
    "Shahdara": [
        {"name": "Shahdara GT Road", "lat": 28.6732, "lon": 77.2872, "base_count": 5100},
        {"name": "Seelampur Crossing", "lat": 28.6698, "lon": 77.2678, "base_count": 4700},
        {"name": "Dilshad Garden", "lat": 28.6811, "lon": 77.3182, "base_count": 3800}
    ],
    "North East Delhi": [
        {"name": "Khajuri Khas Chowk", "lat": 28.7118, "lon": 77.2635, "base_count": 4400},
        {"name": "Yamuna Vihar", "lat": 28.6990, "lon": 77.2730, "base_count": 3500},
        {"name": "Bhopura Border", "lat": 28.7200, "lon": 77.3100, "base_count": 4200}
    ],
    "North Delhi": [
        {"name": "Kashmere Gate ISBT", "lat": 28.6665, "lon": 77.2285, "base_count": 6500},
        {"name": "DU North Campus", "lat": 28.6882, "lon": 77.2104, "base_count": 3600},
        {"name": "Model Town", "lat": 28.7029, "lon": 77.1937, "base_count": 3700},
        {"name": "Azadpur Mandi", "lat": 28.7067, "lon": 77.1764, "base_count": 5400}
    ],
    "North West Delhi": [
        {"name": "Rohini Sector 7/8 Crossing", "lat": 28.7041, "lon": 77.1170, "base_count": 4600},
        {"name": "Pitampura TV Tower", "lat": 28.6980, "lon": 77.1400, "base_count": 4100},
        {"name": "Shalimar Bagh", "lat": 28.7140, "lon": 77.1610, "base_count": 3800},
        {"name": "Nethaji Subhash Place", "lat": 28.6917, "lon": 77.1517, "base_count": 4900}
    ],
    "West Delhi": [
        {"name": "Rajouri Garden Ring Road", "lat": 28.6490, "lon": 77.1225, "base_count": 5200},
        {"name": "Janakpuri District Centre", "lat": 28.6292, "lon": 77.0792, "base_count": 4400},
        {"name": "Punjabi Bagh Club Road", "lat": 28.6660, "lon": 77.1330, "base_count": 5000},
        {"name": "Tilak Nagar", "lat": 28.6366, "lon": 77.0963, "base_count": 4100}
    ]
}

def generate_delhi_traffic_dataset(start_date=None, end_date=None):
    """
    Generates synthetic Delhi probe traffic hourly counts across all places
    for the selected date range.
    """
    if start_date is None:
        start_date = datetime.date(2024, 1, 1)
    if end_date is None:
        end_date = datetime.date(2024, 1, 7)
        
    date_range = pd.date_range(start_date, end_date, freq='D')
    hours = list(range(0, 24))
    
    rows = []
    
    for dt in date_range:
        is_weekend = dt.weekday() >= 5
        day_str = dt.strftime('%Y-%m-%d')
        
        for district, places in DELHI_DISTRICTS_PLACES.items():
            for p in places:
                for h in hours:
                    # Peak hour traffic profile: 8-11 AM & 5-9 PM
                    if 8 <= h <= 10 or 17 <= h <= 20:
                        hour_factor = 1.6 + np.random.uniform(-0.1, 0.2)
                        congestion = round(np.random.uniform(1.4, 1.9), 2)
                    elif 11 <= h <= 16:
                        hour_factor = 1.1 + np.random.uniform(-0.1, 0.1)
                        congestion = round(np.random.uniform(1.1, 1.4), 2)
                    elif 22 <= h or h <= 5:
                        hour_factor = 0.35 + np.random.uniform(-0.05, 0.05)
                        congestion = round(np.random.uniform(1.0, 1.1), 2)
                    else:
                        hour_factor = 0.8 + np.random.uniform(-0.1, 0.1)
                        congestion = round(np.random.uniform(1.0, 1.2), 2)
                        
                    if is_weekend:
                        hour_factor *= 0.85
                        
                    count = int(p['base_count'] * (hour_factor / 24.0) * np.random.uniform(0.9, 1.1))
                    
                    rows.append({
                        "date": day_str,
                        "hour": h,
                        "district": district,
                        "place": p['name'],
                        "lat": p['lat'],
                        "lon": p['lon'],
                        "vehicle_count": count,
                        "congestion_level": congestion
                    })
                    
    return pd.DataFrame(rows)

def generate_full_year_2024_dataset():
    """
    Generates full 365-day Delhi traffic & air quality dataset for Jan 1 to Dec 31, 2024
    including Location, Vehicle Count, Congestion, and AQI.
    """
    date_range = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    rows = []
    
    rng = np.random.default_rng(42)
    
    for dt in date_range:
        month = dt.month
        day_str = dt.strftime('%Y-%m-%d')
        is_weekend = dt.weekday() >= 5
        
        # Delhi seasonal AQI baseline profile
        if month in [11, 12, 1]:  # Winter smog peak
            seasonal_aqi_base = rng.uniform(270, 410)
        elif month in [2, 3, 10]: # Autumn/Spring transition
            seasonal_aqi_base = rng.uniform(170, 280)
        elif month in [4, 5, 6]:  # Summer dust & hot winds
            seasonal_aqi_base = rng.uniform(140, 230)
        else:                     # Monsoon wash out (Jul-Sep)
            seasonal_aqi_base = rng.uniform(40, 105)
            
        for district, places in DELHI_DISTRICTS_PLACES.items():
            for p in places:
                day_multiplier = 0.85 if is_weekend else 1.0
                loc_variance = rng.uniform(0.92, 1.08)
                daily_count = int(p['base_count'] * 24 * 0.55 * day_multiplier * loc_variance)
                
                congestion = round(float(rng.uniform(1.15, 1.75)), 2)
                
                # AQI factoring traffic volume, congestion penalty, and seasonal base
                traffic_impact = (daily_count / 35000.0) * (congestion ** 1.2) * 30.0
                final_aqi = min(500.0, max(15.0, round(float(seasonal_aqi_base + traffic_impact), 1)))
                
                if final_aqi > 400:
                    category = "Severe"
                elif final_aqi > 300:
                    category = "Very Poor"
                elif final_aqi > 200:
                    category = "Poor"
                elif final_aqi > 100:
                    category = "Moderate"
                elif final_aqi > 50:
                    category = "Satisfactory"
                else:
                    category = "Good"
                
                rows.append({
                    "Date": day_str,
                    "District": district,
                    "Location": p['name'],
                    "Vehicle Count": daily_count,
                    "Congestion": congestion,
                    "AQI": final_aqi,
                    "AQI Category": category
                })
                
    return pd.DataFrame(rows)

