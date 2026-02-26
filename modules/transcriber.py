import os
import logging
from groq import Groq
from config.settings import GROQ_API_KEY
from pydub import AudioSegment

log = logging.getLogger(__name__)

def transcribe_audio_with_words(audio_path: str) -> list[dict]:
    """
    Uses Groq's local Whisper to transcribe the audio and return word-level timestamps.
    Returns: [{"word": "hello", "start": 0.0, "end": 0.5}, ...]
    """
    log.info(f"🎙️ Generating exact word timestamps using Whisper for {audio_path}...")
    
    if not GROQ_API_KEY:
        log.warning("No GROQ_API_KEY. Cannot generate word timestamps.")
        return []

    client = Groq(api_key=GROQ_API_KEY)

    # Groq has a 25MB limit. MP3s from PlayHT shouldn't exceed this unless they are huge.
    # To be safe, we check size:
    if os.path.getsize(audio_path) > 24 * 1024 * 1024:
        log.warning("Audio file too large for standard whisper request. Please implement chunking.")
        return []

    try:
        with open(audio_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
              file=(os.path.basename(audio_path), file.read()),
              model="whisper-large-v3",
              response_format="verbose_json"
            )
            
        words_data = []
        
        # Groq returns standard format for verbose_json if words are enabled
        # Note: Depending on integration, we might need to parse segments
        if hasattr(transcription, "words") and transcription.words:
             for w in transcription.words:
                 words_data.append({
                     "word": w.word,
                     "start": w.start,
                     "end": w.end
                 })
        elif hasattr(transcription, "segments") and transcription.segments:
             for s in transcription.segments:
                 # If words array is missing but we have segments, fake word spacing
                 text = s.text.strip().split()
                 dur = (s.end - s.start) / max(1, len(text))
                 cur = s.start
                 for t in text:
                     words_data.append({"word": t, "start": cur, "end": cur + dur})
                     cur += dur
                     
        return words_data

    except Exception as e:
        log.error(f"Whisper transcription failed: {e}")
        return []
