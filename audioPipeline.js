import { TranslationServiceClient } from '@google-cloud/translate';
import { TextToSpeechClient } from '@google-cloud/text-to-speech';
import 'dotenv/config';

const translationClient = new TranslationServiceClient();
const ttsClient = new TextToSpeechClient();

const PROJECT_ID = process.env.GOOGLE_CLOUD_PROJECT || 'krishi-twin-audio';
const LOCATION = 'global';

const REGIONAL_VOICES = {
  hi: { languageCode: 'hi-IN', name: 'hi-IN-Neural2-A', ssmlGender: 'FEMALE' },
  te: { languageCode: 'te-IN', name: 'te-IN-Standard-A', ssmlGender: 'FEMALE' },
  mr: { languageCode: 'mr-IN', name: 'mr-IN-Standard-A', ssmlGender: 'FEMALE' },
  ta: { languageCode: 'ta-IN', name: 'ta-IN-Standard-A', ssmlGender: 'FEMALE' },
  en: { languageCode: 'en-IN', name: 'en-IN-Neural2-A', ssmlGender: 'FEMALE' }
};

export async function processAdvisoryAudio(rawText, targetLang = 'hi') {
  try {
    let translatedText = rawText;

    if (targetLang !== 'en') {
      const transRequest = {
        parent: `projects/${PROJECT_ID}/locations/${LOCATION}`,
        contents: [rawText],
        mimeType: 'text/plain',
        sourceLanguageCode: 'en',
        targetLanguageCode: targetLang
      };
      const [transResponse] = await translationClient.translateText(transRequest);
      translatedText = transResponse.translations[0].translatedText;
    }

    const voiceConfig = REGIONAL_VOICES[targetLang] || REGIONAL_VOICES['en'];
    const ttsRequest = {
      input: { text: translatedText },
      voice: {
        languageCode: voiceConfig.languageCode,
        name: voiceConfig.name,
        ssmlGender: voiceConfig.ssmlGender
      },
      audioConfig: {
        audioEncoding: 'MP3',
        speakingRate: 0.90
      }
    };

    const [ttsResponse] = await ttsClient.synthesizeSpeech(ttsRequest);

    return {
      language: targetLang,
      translatedText,
      audioBuffer: ttsResponse.audioContent
    };
  } catch (err) {
    console.error(`Pipeline error for [${targetLang}]:`, err);
    throw err;
  }
}