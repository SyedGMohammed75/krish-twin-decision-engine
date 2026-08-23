import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.cloud import texttospeech

load_dotenv()

# Point to J's credentials file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

app = FastAPI(
    title="Krishi-Twin Decision Core",
    version="1.0.0",
    description="Counterfactual Agro-Financial Simulation Engine"
)

# Initialize AI Client
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Cloud TTS Client
tts_client = texttospeech.TextToSpeechClient()

SYSTEM_INSTRUCTION = """
You are the Krishi-Twin Counterfactual Financial Engine.
Analyze the provided farm payload.
Compare Scenario A (Spray/Act Today) vs Scenario B (Wait 48 hours / Defer Action).
Output a JSON object with these exact keys:
- 'recommended_action' (String: 'SPRAY', 'WAIT', or 'IRRIGATE')
- 'scenario_a_roi_inr' (String: Calculate the net financial impact in ₹)
- 'scenario_b_roi_inr' (String: Calculate the net financial impact in ₹)
- 'risk_factor' (String: Explanation of the weather, wash-off, or disease risk)
- 'voice_script_2_sentences' (String: A simple, 2-sentence advisory for a low-literacy farmer)
"""

class KrishiTwinResponse(BaseModel):
    recommended_action: str
    scenario_a_roi_inr: str
    scenario_b_roi_inr: str
    risk_factor: str
    voice_script_2_sentences: str

class TTSRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "Do not spray medicine today because heavy rain will wash it away."})
    language_code: str = Field("hi-IN", json_schema_extra={"example": "hi-IN"})

@app.post("/api/v1/simulate", response_model=KrishiTwinResponse)
async def run_simulation(payload: dict):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=json.dumps(payload),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=KrishiTwinResponse,
                temperature=0.2,
            ),
        )
        return KrishiTwinResponse.model_validate_json(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tts")
async def generate_tts(payload: TTSRequest):
    try:
        synthesis_input = texttospeech.SynthesisInput(text=payload.text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=payload.language_code,
            ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)

        response = tts_client.synthesize_speech(
            input=synthesis_input, voice=voice, audio_config=audio_config
        )
        return Response(content=response.audio_content, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))