import requests
import json
from datetime import datetime

# 1. The Madurai Farm Coordinates
lat = 9.8821
lon = 78.0815

# 2. The NDVI we just got from Google Earth Engine
mean_ndvi = 0.37 

# 3. Fetch Local Weather via Open-Meteo API
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation,precipitation_probability,wind_speed_10m&forecast_days=2&timezone=auto"
response = requests.get(url)
weather_data = response.json().get("hourly", {})

# 4. Calculate Risk Metrics (Next 24 Hours)
# Summing up the rain (in mm) and finding the max wind/probability
rain_24h_mm = sum(weather_data.get("precipitation", [])[:24])
max_rain_prob = max(weather_data.get("precipitation_probability", [])[:24], default=0)
max_wind_kmh = max(weather_data.get("wind_speed_10m", [])[:24], default=0)

# Determine Wash-Off Risk 
# If it rains more than 10mm or there is a high chance of rain, spraying is a bad idea.
wash_off_risk = "HIGH" if rain_24h_mm > 10.0 or max_rain_prob > 70 else "LOW"

# 5. Build the Final Krishi-Twin JSON Payload
payload = {
    "engine": "Krishi-Twin-Decision-Core",
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "farm_profile": {
        "coordinates": {"latitude": lat, "longitude": lon},
        "crop": "Rice (Paddy)",
        "farm_size_acres": 2.0,
        "detected_symptom": "Leaf Blight"
    },
    "geospatial_telemetry": {
        "mean_ndvi_index": mean_ndvi,
        "canopy_vigor": "Stressed" if mean_ndvi < 0.4 else "Healthy"
    },
    "meteorological_risk": {
        "rain_next_24h_mm": round(rain_24h_mm, 2),
        "rain_probability_pct": max_rain_prob,
        "max_wind_kmh": round(max_wind_kmh, 2),
        "computed_washoff_risk": wash_off_risk
    },
    "financial_inputs": {
        "spray_cost_inr": 850.0,
        "potential_crop_loss_inr": 4200.0
    }
}

# Print the payload
print("Krishi-Twin Unified Payload Ready:")
print(json.dumps(payload, indent=2))