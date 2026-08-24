import requests
import json
from datetime import datetime

lat = 9.8821
lon = 78.0815
mean_ndvi = 0.37

# 1. Fetch live meteorological telemetry
url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=precipitation,precipitation_probability,wind_speed_10m&forecast_days=2&timezone=auto"
response = requests.get(url)
weather_data = response.json().get("hourly", {})

rain_24h_mm = sum(weather_data.get("precipitation", [])[:24])
max_rain_prob = max(weather_data.get("precipitation_probability", [])[:24], default=0)
max_wind_kmh = max(weather_data.get("wind_speed_10m", [])[:24], default=0)

wash_off_risk = "HIGH" if rain_24h_mm > 10.0 or max_rain_prob > 70 else "LOW"

# 2. Build live dynamic payload
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

# 3. POST live payload directly to backend
server_url = "http://localhost:8080/api/v1/simulate"
sim_response = requests.post(server_url, json=payload)

print("\n--- Live Simulation Result from Backend ---")
print(json.dumps(sim_response.json(), indent=2))