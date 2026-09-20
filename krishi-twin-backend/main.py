import os
import json
import base64
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

app = FastAPI(
    title="Krishi-Twin Decision Core",
    version="1.2.0",
    description="Multimodal Agro-Financial Counterfactual Engine"
)

ai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
translate_client = translate.Client()
tts_client = texttospeech.TextToSpeechClient()

SYSTEM_INSTRUCTION = """
You are the Krishi-Twin Counterfactual Agronomic & Financial Engine.
Analyze the provided farm payload and any attached crop imagery.
1. VISUAL DIAGNOSIS: Inspect leaf imagery to visually confirm disease symptoms and spot lesions before executing simulations.
2. COUNTERFACTUAL SIMULATION: Compare Scenario A (Act Today) vs Scenario B (Wait 48 hours / Defer Action).
Output a JSON object strictly adhering to the response schema.
"""

# Regional voice profiles for TTS
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


@app.post("/api/v1/simulate", response_model=KrishiTwinResponse)
async def run_multimodal_simulation(payload: MultimodalSimulationRequest):
    try:
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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/tts")
async def generate_multilingual_tts(payload: MultilingualTTSRequest):
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