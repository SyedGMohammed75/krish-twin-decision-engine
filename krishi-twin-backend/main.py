import os
import json
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.cloud import translate
from google.cloud import texttospeech

# Load environment variables
load_dotenv()

# Point to J's credentials for GCP services (TTS & Translation)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

app = FastAPI(
    title="Krishi-Twin Decision Core",
    version="1.0.0",
    description="Counterfactual Agro-Financial Simulation Engine"
)

# Initialize Clients
ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
translate_client = translate.TranslationServiceClient()
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

# Regional voice profiles for TTS
REGIONAL_VOICES = {
    'hi': {'language_code': 'hi-IN', 'name': 'hi-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'te': {'language_code': 'te-IN', 'name': 'te-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'mr': {'language_code': 'mr-IN', 'name': 'mr-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'ta': {'language_code': 'ta-IN', 'name': 'ta-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'en': {'language_code': 'en-IN', 'name': 'en-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}
}

# Response Schemas
class KrishiTwinResponse(BaseModel):
    recommended_action: str
    scenario_a_roi_inr: str
    scenario_b_roi_inr: str
    risk_factor: str
    voice_script_2_sentences: str

class MultilingualTTSRequest(BaseModel):
    text: str = Field(..., json_schema_extra={"example": "Do not spray medicine today because heavy rain will wash it away."})
    target_lang: str = Field("hi", json_schema_extra={"example": "hi"})  # 'hi', 'te', 'mr', 'ta', 'en'


@app.post("/api/v1/simulate", response_model=KrishiTwinResponse)
async def run_simulation(payload: dict):
    """Ingests farm telemetry (from S) and generates counterfactual simulation via Gemini 3.6 Flash."""
    try:
        response = ai_client.models.generate_content(
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
async def generate_multilingual_tts(payload: MultilingualTTSRequest):
    """Translates advisory text into target regional language and synthesizes spoken MP3 audio."""
    try:
        translated_text = payload.text

        # 1. Translate text if target language is not English
        if payload.target_lang != 'en':
            parent = f"projects/{os.getenv('GOOGLE_CLOUD_PROJECT', 'krishi-twin-audio')}/locations/global"
            response = translate_client.translate_text(
                request={
                    "parent": parent,
                    "contents": [payload.text],
                    "mime_type": "text/plain",
                    "source_language_code": "en",
                    "target_language_code": payload.target_lang,
                }
            )
            translated_text = response.translations[0].translated_text

        # 2. Select voice profile
        voice_config = REGIONAL_VOICES.get(payload.target_lang, REGIONAL_VOICES['en'])

        # 3. Synthesize speech via Google Cloud TTS
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

        # Return clean audio stream without non-ASCII header
        return Response(
            content=tts_response.audio_content, 
            media_type="audio/mpeg"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))