import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# Load environment variables from .env file
load_dotenv()

# Initialize FastAPI App
app = FastAPI(
    title="Krishi-Twin Engine",
    version="1.0.0",
    description="Counterfactual Agro-Financial Simulation Middleware"
)

# Initialize Google Gen AI Client using key from .env
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_INSTRUCTION = """
You are the master agronomic intelligence engine of "Krishi-Twin," an automated decision simulation middleware for smallholder agriculture in India.

Your primary objective is to convert crop health indicators, micro-soil parameters, and IMD/meteorological forecasts into structured counterfactual decision intelligence. You MUST NEVER output isolated diagnostic text or generic recommendations.

Core Reasoning Rules:
1. COUNTERFACTUAL SIMULATION: Analyze two distinct operational paths:
   - Scenario A (Immediate Action): Executing typical or immediate intervention today.
   - Scenario B (Deferred/Optimized Action): Postponing, modifying, or altering inputs based on soil absorption, micro-climate windows, and cost constraints.
2. FINANCIAL QUANTIFICATION: Evaluate economic risks for both paths in Indian Rupees (₹/acre), taking into account chemical/fertilizer input costs, manual labor fees, pump electricity/diesel costs, and protected crop yield value.
3. ENVIRONMENTAL RISK ASSESSMENT: Assess micro-environmental impact, including chemical wash-off likelihood, soil microbial toxicity, water table runoff, and plant stomatal absorption efficiency.
4. VOICE ADVISORY GENERATION: Produce a voice_advisory_script that is STRICTLY 2 sentences long, written in plain, localized language accessible to low-literacy farmers.
"""

# Define Pydantic Output Schemas for Gemini Enforced JSON
class ScenarioDetails(BaseModel):
    action_name: str = Field(..., description="Short title of the scenario action")
    expected_efficacy_pct: int = Field(..., description="Expected efficacy percentage from 0 to 100")
    financial_risk_rupees: str = Field(..., description="Estimated gain or loss in Indian Rupees (₹) per acre")
    environmental_tradeoffs: str = Field(..., description="Analysis of wash-off, soil health, runoff, or absorption")

class KrishiTwinResponse(BaseModel):
    scenario_a_immediate: ScenarioDetails
    scenario_b_deferred: ScenarioDetails
    voice_advisory_script: str = Field(..., description="Strictly 2 short sentences in plain text suitable for voice conversion")

# Define API Request Schema
class SimulationRequest(BaseModel):
    crop: str = Field(..., json_schema_extra={"example": "Paddy Rice"})
    location: str = Field(..., json_schema_extra={"example": "Andhra Pradesh"})
    symptoms_or_issue: str = Field(..., json_schema_extra={"example": "Yellow leaf spots and lesions (Leaf Blight)"})
    soil_moisture_pct: float = Field(..., json_schema_extra={"example": 82.0})
    imd_weather_forecast: dict = Field(
        ..., 
        json_schema_extra={"example": {"next_24h_rain_mm": 40, "humidity_pct": 85, "temp_c": 30}}
    )
    estimated_input_costs_rupees: float = Field(..., json_schema_extra={"example": 2000.0})

@app.post("/api/v1/simulate", response_model=KrishiTwinResponse)
async def run_counterfactual_simulation(payload: SimulationRequest):
    try:
        user_prompt = f"""
        Execute a counterfactual simulation for the following field parameters:
        - Crop: {payload.crop}
        - Location: {payload.location}
        - Diagnostic Issue: {payload.symptoms_or_issue}
        - Current Soil Moisture: {payload.soil_moisture_pct}%
        - IMD Weather Forecast: {payload.imd_weather_forecast}
        - Base Input Cost (Fungicide/Labor): ₹{payload.estimated_input_costs_rupees}
        """

        # Updated model parameter to gemini-3.6-flash
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=KrishiTwinResponse,
                temperature=0.2,
            ),
        )
        
        # Parse output directly into Pydantic model
        structured_data = KrishiTwinResponse.model_validate_json(response.text)
        return structured_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))