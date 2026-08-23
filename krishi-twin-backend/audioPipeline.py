import os
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech

# Point to J's credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "gcp-key.json"

# Voice configuration mapping for Indian regional languages
REGIONAL_VOICES = {
    'hi': {'language_code': 'hi-IN', 'name': 'hi-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'te': {'language_code': 'te-IN', 'name': 'te-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'mr': {'language_code': 'mr-IN', 'name': 'mr-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'ta': {'language_code': 'ta-IN', 'name': 'ta-IN-Standard-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE},
    'en': {'language_code': 'en-IN', 'name': 'en-IN-Neural2-A', 'ssml_gender': texttospeech.SsmlVoiceGender.FEMALE}
}

# Initialize Google Cloud Clients
translate_client = translate.Client()
tts_client = texttospeech.TextToSpeechClient()

def process_advisory_audio(raw_text: str, target_lang: str = 'hi') -> dict:
    """
    Translates raw English advisory text into target Indian regional language 
    and synthesizes an MP3 voice file.
    """
    try:
        translated_text = raw_text

        # 1. Translate text if target language is not English
        if target_lang != 'en':
            result = translate_client.translate(
                raw_text,
                target_language=target_lang,
                source_language='en'
            )
            translated_text = result['translatedText']

        # 2. Select regional voice profile
        voice_config = REGIONAL_VOICES.get(target_lang, REGIONAL_VOICES['en'])

        # 3. Configure Text-to-Speech synthesis
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

        # 4. Synthesize speech
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        return {
            "language": target_lang,
            "translated_text": translated_text,
            "audio_bytes": response.audio_content
        }

    except Exception as err:
        print(f"Pipeline error for [{target_lang}]: {err}")
        raise err


# Test Runner matching J's test script
if __name__ == "__main__":
    sample_advisory = "Do not spray pesticides today as upcoming rain will wash away the chemical. Wait 48 hours for clear weather."
    print("Starting Audio & Translation Test...\n")

    languages = ['hi', 'te', 'mr']

    for lang in languages:
        print(f"Processing [{lang}]...")
        result = process_advisory_audio(sample_advisory, lang)
        print(f"Translated: {result['translated_text']}")

        output_filename = f"advisory_{lang}.mp3"
        with open(output_filename, "wb") as out_file:
            out_file.write(result['audio_bytes'])
            print(f"Saved audio file: {output_filename}\n")

    print("All audio generated successfully!")