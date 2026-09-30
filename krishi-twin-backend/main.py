import os
import json
import base64
import time
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Load environment variables
load_dotenv()

# Safe GCP Credentials Initialization (Local File or Cloud Env Var)
key_path = "gcp-key.json"
if os.path.exists(key_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_path
elif os.getenv("GCP_SA_KEY_BASE64"):
    try:
        decoded_bytes = base64.b64decode(os.getenv("GCP_SA_KEY_BASE64"))
        with open("/tmp/gcp-key.json", "wb") as f:
            f.write(decoded_bytes)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/gcp-key.json"
    except Exception as err:
        print(f"Warning decoding GCP_SA_KEY_BASE64: {err}")

app = FastAPI(
    title="Krishi-Twin Decision Core",
    version="1.2.0",
    description="Multimodal Agro-Financial Counterfactual Engine"
)

# Enable CORS for Frontend & Cross-Origin Requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AI Client
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Lazy/Safe initialization for GCP Services
try:
    translate_client = translate.Client()
except Exception as e:
    print(f"Warning initializing Google Translate Client: {e}")
    translate_client = None

try:
    tts_client = texttospeech.TextToSpeechClient()
except Exception as e:
    print(f"Warning initializing Google TTS Client: {e}")
    tts_client = None

SYSTEM_INSTRUCTION = """
You are the Krishi-Twin Counterfactual Agronomic & Financial Engine.
Analyze the provided farm payload and any attached crop imagery.
1. VISUAL DIAGNOSIS: Inspect leaf imagery to visually confirm disease symptoms and spot lesions before executing simulations.
2. COUNTERFACTUAL SIMULATION: Compare Scenario A (Act Today) vs Scenario B (Wait 48 hours / Defer Action).
Output a JSON object strictly adhering to the response schema.
"""

REGIONAL_VOICES = {
    'hi': {'language_code': 'hi-IN', 'name': 'hi-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'te': {'language_code': 'te-IN', 'name': 'te-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'mr': {'language_code': 'mr-IN', 'name': 'mr-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'ta': {'language_code': 'ta-IN', 'name': 'ta-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'en': {'language_code': 'en-IN', 'name': 'en-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}
}

class MultimodalSimulationRequest(BaseModel):
    farm_profile: dict
    geospatial_telemetry: dict
    meteorological_risk: dict
    financial_inputs: dict
    image_base64: str | None = Field(default=None, description="Base64 string of crop leaf image")

class KrishiTwinResponse(BaseModel):
    recommended_action: str
    visual_diagnosis_confirmation: str
    scenario_a_roi_inr: str
    scenario_b_roi_inr: str
    risk_factor: str
    voice_script_2_sentences: str

class MultilingualTTSRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "Do not spray medicine today because heavy rain will wash it away."})
    target_lang: str = Field("hi", json_schema_extra={"example": "hi"})

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML_PATH = os.path.join(BASE_DIR, "static", "index.html")

@app.get("/", response_class=FileResponse)
async def serve_index():
    """Serve the interactive web UI dashboard at GET /."""
    if os.path.exists(INDEX_HTML_PATH):
        return FileResponse(INDEX_HTML_PATH)
    raise HTTPException(status_code=404, detail="Frontend index.html not found.")

@app.get("/health")
async def health_check():
    """Liveness probe endpoint for cloud deployment services (Render, Railway, GCP Cloud Run)."""
    return {
        "status": "online",
        "service": "Krishi-Twin Decision Core",
        "version": "1.2.0",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/v1/simulate", response_model=KrishiTwinResponse)
async def run_multimodal_simulation(payload: MultimodalSimulationRequest):
    telemetry_json = json.dumps({
        "farm_profile": payload.farm_profile,
        "geospatial_telemetry": payload.geospatial_telemetry,
        "meteorological_risk": payload.meteorological_risk,
        "financial_inputs": payload.financial_inputs
    })
    
    contents = [f"Farm Telemetry Payload:\n{telemetry_json}"]

    if payload.image_base64:
        image_bytes = base64.b64decode(payload.image_base64)
        contents.append(
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
        )

    max_retries = 3
    last_exception = None

    for attempt in range(max_retries):
        try:
            response = ai_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    response_schema=KrishiTwinResponse,
                    temperature=0.2,
                ),
            )
            return KrishiTwinResponse.model_validate_json(response.text)
        except Exception as e:
            last_exception = e
            if ("503" in str(e) or "UNAVAILABLE" in str(e)) and attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))
                continue

    raise HTTPException(status_code=500, detail=str(last_exception))

@app.post("/api/v1/tts")
async def generate_multilingual_tts(payload: MultilingualTTSRequest):
    if not tts_client or not translate_client:
        raise HTTPException(status_code=503, detail="GCP TTS/Translate services not configured on server.")

    try:
        translated_text = payload.text
        
        if payload.target_lang != 'en':
            translation = translate_client.translate(
                payload.text,
                target_language=payload.target_lang,
                source_language='en'
            )
            translated_text = translation['translatedText']

        voice_config = REGIONAL_VOICES.get(payload.target_lang, REGIONAL_VOICES['en'])

        synthesis_input = texttospeech.SynthesisInput(text=translated_text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_config['language_code'],
            name=voice_config['name'],
            ssml_gender=voice_config['ssml_gender']
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.90
        )

        tts_response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        return Response(
            content=tts_response.audio_content, 
            media_type="audio/mpeg"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))