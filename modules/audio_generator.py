"""
modules/audio_generator.py
Converts script text to voiceover audio.
Tries ElevenLabs first (premium quality), falls back to gTTS (free).
"""

import logging
import os
import tempfile
from pathlib import Path

from config.settings import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    ELEVENLABS_VOICE_ID_2,
    OPENAI_API_KEY,
    TTS_PROVIDER,
    EDGE_VOICE_A,
    EDGE_VOICE_B,
    OPENAI_VOICE_A,
    OPENAI_VOICE_B,
    OUTPUT_DIR,
    FFMPEG_PATH,
)
import asyncio
import edge_tts

import subprocess

log = logging.getLogger(__name__)


# -----------------------------------------------------------------
#  ELEVENLABS (premium, natural-sounding)
# -----------------------------------------------------------------

def tts_elevenlabs(text: str, output_path: str, voice_id: str = None) -> bool:
    """Generate audio via ElevenLabs API. Returns True on success."""
    if not ELEVENLABS_API_KEY:
        return False
    vid = voice_id or ELEVENLABS_VOICE_ID
    try:
        import requests
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        log.info(f"ElevenLabs audio ({vid}) saved -> {output_path}")
        return True
    except Exception as e:
        log.warning(f"ElevenLabs failed for voice {vid}: {e}")
        return False


# -----------------------------------------------------------------
#  EDGE-TTS (Free, Microsoft Neural Voices - Highly Recommended)
# -----------------------------------------------------------------

def tts_edge(text: str, output_path: str, voice: str = None) -> bool:
    """Generate high-quality audio for FREE using Microsoft Edge TTS."""
    async def _gen():
        v = voice or EDGE_VOICE_A
        communicate = edge_tts.Communicate(text, v)
        await communicate.save(output_path)
        log.info(f"Edge-TTS audio ({v}) saved -> {output_path}")
    
    try:
        asyncio.run(_gen())
        return True
    except Exception as e:
        log.error(f"Edge-TTS failed: {e}")
        return False


# -----------------------------------------------------------------
#  OPENAI TTS (Premium, smooth)
# -----------------------------------------------------------------

def tts_openai(text: str, output_path: str, voice: str = None) -> bool:
    """Generate audio via OpenAI TTS API."""
    if not OPENAI_API_KEY or "YOUR_OPENAI" in OPENAI_API_KEY:
        return False
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        v = voice or OPENAI_VOICE_A
        response = client.audio.speech.create(
            model="tts-1",
            voice=v,
            input=text
        )
        response.stream_to_file(output_path)
        log.info(f"OpenAI TTS audio ({v}) saved -> {output_path}")
        return True
    except Exception as e:
        log.error(f"OpenAI TTS failed: {e}")
        return False


# -----------------------------------------------------------------
#  GTTS (free Google Text-to-Speech)
# -----------------------------------------------------------------

def tts_gtts(text: str, output_path: str) -> bool:
    """Generate audio via gTTS. Returns True on success."""
    try:
        from gtts import gTTS
        
        tmp = output_path.replace(".mp3", "_raw.mp3")
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(tmp)

        # Speed up slightly (1.15x) using direct ffmpeg call
        cmd = [
            FFMPEG_PATH, "-y", "-i", tmp,
            "-filter:a", "atempo=1.15",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        if os.path.exists(tmp):
            os.remove(tmp)

        log.info(f"gTTS audio saved -> {output_path}")
        return True
    except Exception as e:
        log.error(f"gTTS failed: {e}")
        return False


# -----------------------------------------------------------------
#  CHUNK LONG SCRIPTS (APIs have char limits)
# -----------------------------------------------------------------

def chunk_text(text: str, max_chars: int = 4500) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += " " + s
        else:
            if current:
                chunks.append(current.strip())
            current = s
    if current:
        chunks.append(current.strip())
    return chunks


def parse_podcast_script(script: str) -> list[dict]:
    """Parse dialogue script into list of (voice_id, text) chunks."""
    import re
    # Pattern to match "Host A: text" or "Host B: text"
    lines = re.split(r'(Host [AB]:)', script)
    chunks = []
    
    # Determine default voices based on provider
    if TTS_PROVIDER == "openai":
        v1, v2 = OPENAI_VOICE_A, OPENAI_VOICE_B
    elif TTS_PROVIDER == "elevenlabs":
        v1, v2 = ELEVENLABS_VOICE_ID, ELEVENLABS_VOICE_ID_2
    else: # edge
        v1, v2 = EDGE_VOICE_A, EDGE_VOICE_B
        
    current_voice = v1
    for item in lines:
        item = item.strip()
        if not item: continue
        if item == "Host A:":
            current_voice = v1
        elif item == "Host B:":
            current_voice = v2
        else:
            chunks.append({"voice_id": current_voice, "text": item})
    
    if not chunks:
        chunks = [{"voice_id": v1, "text": script}]
        
    return chunks


def generate_audio(script: str, job_id: str) -> str:
    """
    Convert full podcast script to audio file.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_voice.mp3")

    log.info("=== Generating Podcast Voiceover Audio ===")

    # Parse dialogue
    dialogue_chunks = parse_podcast_script(script)
    chunk_files = []
    
    # Try Configured Provider
    all_ok = True
    for i, chunk in enumerate(dialogue_chunks):
        cp = output_path.replace(".mp3", f"_chunk{i}.mp3")
        
        ok = False
        if TTS_PROVIDER == "elevenlabs" and ELEVENLABS_API_KEY:
            ok = tts_elevenlabs(chunk["text"], cp, voice_id=chunk["voice_id"])
        elif TTS_PROVIDER == "openai" and OPENAI_API_KEY:
            ok = tts_openai(chunk["text"], cp, voice=chunk["voice_id"])
        elif TTS_PROVIDER == "edge":
            ok = tts_edge(chunk["text"], cp, voice=chunk["voice_id"])
            
        if ok:
            chunk_files.append(cp)
        else:
            all_ok = False
            break
    
    if all_ok:
        _stitch_mp3(chunk_files, output_path)
        return output_path
    else:
        # Fallback to Edge if it wasn't the primary choice
        if TTS_PROVIDER != "edge":
            log.info("Primary TTS failed, falling back to Edge-TTS...")
            for f in chunk_files: 
                if os.path.exists(f): os.remove(f)
            chunk_files = []
            all_ok = True
            for i, chunk in enumerate(dialogue_chunks):
                cp = output_path.replace(".mp3", f"_chunk{i}.mp3")
                # Map Host A/B to Edge voices
                ev = EDGE_VOICE_A if i % 2 == 0 else EDGE_VOICE_B # Simplified fallback
                if tts_edge(chunk["text"], cp, voice=ev):
                    chunk_files.append(cp)
                else:
                    all_ok = False
                    break
            if all_ok:
                _stitch_mp3(chunk_files, output_path)
                return output_path

        # Worst Case: gTTS
        for f in chunk_files:
            if os.path.exists(f): os.remove(f)
        chunk_files = []

    # Fallback: gTTS (One voice only for now)
    log.info("Falling back to gTTS for podcast (single voice)...")
    full_text = " ".join([c["text"] for c in dialogue_chunks])
    text_chunks = chunk_text(full_text, max_chars=4500)
    chunk_files = []
    for i, ct in enumerate(text_chunks):
        cp = output_path.replace(".mp3", f"_chunk{i}.mp3")
        tts_gtts(ct, cp)
        chunk_files.append(cp)

    _stitch_mp3(chunk_files, output_path)
    return output_path


def _stitch_mp3(files: list[str], output: str):
    """Concatenate MP3 chunk files into one using ffmpeg."""
    try:
        # Create a temp file for ffmpeg concat filter
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            for file_path in files:
                # Need to escape backslashes for Windows paths in concat file
                p = os.path.abspath(file_path).replace("\\", "/")
                f.write(f"file '{p}'\n")
            list_path = f.name

        cmd = [
            FFMPEG_PATH, "-y", "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", output
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Cleanup
        os.remove(list_path)
        for f in files:
            if os.path.exists(f):
                os.remove(f)
                
        log.info(f"Stitched {len(files)} audio chunks -> {output}")
    except Exception as e:
        log.error(f"Stitching failed: {e}")
        # Fallback: simple binary concat (risky but often works for MP3)
        with open(output, "wb") as outfile:
            for f in files:
                with open(f, "rb") as infile:
                    outfile.write(infile.read())
                os.remove(f)
