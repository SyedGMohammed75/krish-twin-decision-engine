import { processAdvisoryAudio } from './audioPipeline.js';
import fs from 'fs/promises';

const sampleAdvisory = "Do not spray pesticides today as upcoming rain will wash away the chemical. Wait 48 hours for clear weather.";

async function run() {
  console.log("Starting Audio & Translation Test...\n");

  const languages = ['hi', 'te', 'mr'];

  for (const lang of languages) {
    console.log(`Processing [${lang}]...`);
    const result = await processAdvisoryAudio(sampleAdvisory, lang);
    console.log(`Translated: ${result.translatedText}`);
    
    await fs.writeFile(`advisory_${lang}.mp3`, result.audioBuffer, 'binary');
    console.log(`Saved audio file: advisory_${lang}.mp3\n`);
  }

  console.log("All audio generated successfully!");
}

run();