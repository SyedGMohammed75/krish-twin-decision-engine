import os
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

# Voice Configuration Matrix
REGIONAL_VOICES = {
    'ta': {'language_code': 'ta-IN', 'name': 'ta-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}, # Tamil Nadu
    'te': {'language_code': 'te-IN', 'name': 'te-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}, # AP / Telangana
    'kn': {'language_code': 'kn-IN', 'name': 'kn-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}, # Karnataka
    'ml': {'language_code': 'ml-IN', 'name': 'ml-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}, # Kerala
    'mr': {'language_code': 'mr-IN', 'name': 'mr-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}, # Maharashtra
    'hi': {'language_code': 'hi-IN', 'name': 'hi-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},  # North India
    'en': {'language_code': 'en-IN', 'name': 'en-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}
}

translate_client = translate.Client()
tts_client = texttospeech.TextToSpeechClient()

def resolve_language_from_coordinates(lat: float, lon: float) -> str:
    """Geofences GPS coordinates to the primary regional language code."""
    if 8.0 <= lat <= 13.5 and 76.0 <= lon <= 80.3:
        return 'ta'  # Tamil Nadu
    elif 12.5 <= lat <= 19.8 and 76.7 <= lon <= 84.8:
        return 'te'  # AP / Telangana
    elif 11.5 <= lat <= 18.5 and 74.0 <= lon <= 78.5:
        return 'kn'  # Karnataka
    elif 8.2 <= lat <= 12.8 and 74.8 <= lon <= 77.5:
        return 'ml'  # Kerala
    elif 15.6 <= lat <= 22.0 and 72.6 <= lon <= 80.9:
        return 'mr'  # Maharashtra
    return 'hi'      # Default fallback

def process_advisory_audio_by_coordinates(raw_text: str, lat: float, lon: float) -> dict:
    """Dynamically translates text based on map location and returns synthesized audio."""
    target_lang = resolve_language_from_coordinates(lat, lon)
    translated_text = raw_text

    if target_lang != 'en':
        result = translate_client.translate(
            raw_text,
            target_language=target_lang,
            source_language='en'
        )
        translated_text = result['translatedText']

    voice_config = REGIONAL_VOICES.get(target_lang, REGIONAL_VOICES['en'])

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

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return {
        "resolved_language": target_lang,
        "translated_text": translated_text,
        "audio_bytes": response.audio_content
    }