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
              response_format="verbose_json",
              timestamp_granularities=["word"]
            )
            
        words_data = []
        
        # If the SDK returns a dictionary
        if isinstance(transcription, dict):
            words = transcription.get("words", [])
            segments = transcription.get("segments", [])
            
            if words:
                for w in words:
                    words_data.append({
                        "word": w.get("word", ""),
                        "start": w.get("start", 0),
                        "end": w.get("end", 0)
                    })
            elif segments:
                for s in segments:
                    text_arr = s.get("text", "").strip().split()
                    dur = (s.get("end", 1) - s.get("start", 0)) / max(1, len(text_arr))
                    cur = s.get("start", 0)
                    for t in text_arr:
                        words_data.append({"word": t, "start": cur, "end": cur + dur})
                        cur += dur
        # If it returns an object
        else:
            if hasattr(transcription, "words") and transcription.words:
                 for w in transcription.words:
                     words_data.append({
                         "word": w.word if hasattr(w, "word") else w.get("word", ""),
                         "start": w.start if hasattr(w, "start") else w.get("start", 0),
                         "end": w.end if hasattr(w, "end") else w.get("end", 0)
                     })
            elif hasattr(transcription, "segments") and transcription.segments:
                 for s in transcription.segments:
                     text_val = s.text if hasattr(s, "text") else s.get("text", "")
                     start_val = s.start if hasattr(s, "start") else s.get("start", 0)
                     end_val = s.end if hasattr(s, "end") else s.get("end", 1)
                     
                     text_arr = text_val.strip().split()
                     dur = (end_val - start_val) / max(1, len(text_arr))
                     cur = start_val
                     for t in text_arr:
                         words_data.append({"word": t, "start": cur, "end": cur + dur})
                         cur += dur
                         
        return words_data

    except Exception as e:
        log.error(f"Whisper transcription failed: {e}")
        return []
