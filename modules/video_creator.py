"""
modules/video_creator.py
Builds high-quality faceless YouTube videos & Shorts:
  • AI-generated background images per slide (cinematic style)
  • Smooth Ken Burns zoom/pan transitions
  • Dynamic text overlays with semi-transparent backdrops
  • Optimized for both 16:9 Landscape and 9:16 Shorts
  • Integrated BGM with looping
"""

import logging
import math
import os
import shutil
import textwrap
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config.settings import (
    ASSETS_DIR,
    BACKGROUND_MUSIC_VOLUME,
    FONT_PATH,
    OUTPUT_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    NICHE,
)
from modules.asset_generator import generate_ai_image
from modules.pexels_manager import get_stock_video

log = logging.getLogger(__name__)

# -----------------------------------------------------------------
#  SLIDE CONTENT EXTRACTION
# -----------------------------------------------------------------

def script_to_slides(script: str, seo_title: str) -> list[str]:
    """
    Break podcast script into small, punchy chunks for dynamic captions.
    """
    import re
    # Split by Host turns
    lines = re.split(r'(Host [AB]:)', script)
    
    slides = [seo_title.upper()] # Title slide
    
    current_host = ""
    for item in lines:
        item = item.strip()
        if not item: continue
        if item in ["Host A:", "Host B:"]:
            current_host = item
        else:
            # Split into very short visual chunks (5-8 words) for "Hormozi" style captions
            words = item.split()
            chunk_size = 6
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                slides.append(f"{current_host} {chunk}")

    slides.append("LIKE  •  SUBSCRIBE  •  AI NEWS DAILY")
    return slides


# -----------------------------------------------------------------
#  KEN BURNS EFFECT (SMOOTH ZOOM)
# -----------------------------------------------------------------

def apply_ken_burns(clip, duration):
    """Apply a smooth zoom effect to an ImageClip."""
    # Randomly choose zoom in or zoom out
    zoom_in = random.choice([True, False])
    
    def effect(t):
        if zoom_in:
            scale = 1.0 + (0.15 * (t / duration)) # Zoom from 1.0 to 1.15
        else:
            scale = 1.15 - (0.15 * (t / duration)) # Zoom from 1.15 to 1.0
        return scale

    return clip.with_effects([vfx.Resize(effect)])


# -----------------------------------------------------------------
#  SLIDE IMAGE OVERLAY RENDERER
# -----------------------------------------------------------------

def render_slide_overlay(text: str, w: int, h: int, is_title: bool = False, is_shorts: bool = False) -> Image.Image:
    """Render a premium caption overlay (no boxes, bold modern style)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Detect Host
    host_color = (255, 255, 255)
    host_label = ""
    if text.startswith("Host A:"):
        host_label = "HOST A"
        text = text.replace("Host A:", "").strip()
        host_color = (0, 255, 100) # Neon Green for Host A
    elif text.startswith("Host B:"):
        host_label = "HOST B"
        text = text.replace("Host B:", "").strip()
        host_color = (255, 100, 0) # Neon Orange for Host B
    
    # Scale font sizes (Bigger for captions)
    scale_factor = 1.0 if is_shorts else 1.2
    caption_size = int(85 * scale_factor)
    if is_title: caption_size = int(120 * scale_factor)
    
    try:
        font_main = ImageFont.truetype(FONT_PATH, caption_size)
        font_host = ImageFont.truetype(FONT_PATH, int(40 * scale_factor))
    except Exception:
        font_main = ImageFont.load_default()
        font_host = font_main

    # --- DRAW TEXT (Premium Subtitles Style) ---
    words = text.split()
    lines = []
    # Dynamic word grouping for impact
    n = 2 if is_shorts else 3
    for i in range(0, len(words), n):
        lines.append(" ".join(words[i:i+n]))
        
    line_h = caption_size + 20
    total_h = line_h * len(lines)
    
    # Position: Bottom-center for Shorts, Middle-bottom for Landscape
    if is_shorts:
        y = h - total_h - 250
    else:
        y = h - total_h - 200

    for line in lines:
        line_words = line.upper().split()
        
        # 1. Background Capsule (Semi-transparent dark backdrop)
        full_line_text = " ".join(line_words)
        bbox_full = draw.textbbox((0, 0), full_line_text, font=font_main)
        lw = bbox_full[2] - bbox_full[0]
        padding = 40
        
        bx1, by1 = (w - lw) // 2 - padding, y - 10
        bx2, by2 = (w + lw) // 2 + padding, y + line_h - 10
        
        # Draw rounded rectangle for text backing
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=20, fill=(0, 0, 0, 160))
        
        cur_x = (w - lw) // 2
        
        for i, word in enumerate(line_words):
            # Highlight Logic (Agentic style)
            highlights = ["AI", "MCP", "DATA", "ROBOT", "GPT", "OPENAI", "ANTHROPIC", "TECH", "FUTURE", "IMPACT", "WORLD", "AUTO", "AGENT", "MONEY", "SCALE"]
            is_highlight = is_title or word in highlights or word.endswith("S")
            
            color = (0, 255, 127) if is_highlight else (255, 255, 255) # Spring Green or White
            if is_title: color = (255, 215, 0) # Gold
            
            # Simple soft drop shadow
            draw.text((cur_x + 3, y + 3), word, font=font_main, fill=(0, 0, 0, 200))
            draw.text((cur_x, y), word, font=font_main, fill=color)
            
            # Move x
            bbox_word = draw.textbbox((0, 0), word, font=font_main)
            word_w = bbox_word[2] - bbox_word[0]
            cur_x += word_w + 25 # spacing
            
        y += line_h

    # --- PREMIUM HOST INDICATOR ---
    if host_label:
        label = f"🎙️ {host_label}"
        lx, ly = (100, 100) if not is_shorts else (w // 2 - 150, 200)
        # Glow effect
        for r in range(1, 4):
            draw.text((lx, ly), label, font=font_host, fill=(0,0,0,80))
        draw.text((lx, ly), label, font=font_host, fill=host_color)

    # Brander
    if not is_shorts:
        brand = f"@{NICHE}"
        draw.text((w - 250, h - 80), brand, font=font_host, fill=(255,255,255, 80))

    return img

# -----------------------------------------------------------------
#  MAIN VIDEO BUILDER (REMOTION BASED)
# -----------------------------------------------------------------

def create_video(content: dict, audio_path: str, job_id: str, is_shorts: bool = False) -> str:
    """Build high-quality MP4 video using React Remotion engine."""
    import json
    import subprocess
    from mutagen.mp3 import MP3
    
    log.info(f"=== Building {'Short' if is_shorts else 'Long'} Video (Remotion) ===")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")
    
    # 1. Get audio duration
    try:
        audio = MP3(audio_path)
        total_duration = audio.info.length
    except Exception as e:
        log.error(f"Could not read audio duration: {e}")
        total_duration = 60.0 # fallback

    if is_shorts and total_duration > 60:
         log.info("Warning: Audio is longer than 60s. For shorts, it should ideally be trimmed. Left as is for Remotion.")
         
    log.info(f"Voiceover duration: {total_duration:.1f}s")
    
    # 2. Extract word timings via Groq Whisper
    from modules.transcriber import transcribe_audio_with_words
    word_timings = transcribe_audio_with_words(audio_path)
    
    fps = 30
    total_frames = int(total_duration * fps)

    # 3. Handle Graphics via Director Agent
    from modules.director_agent import generate_scene_data
    from config.settings import USE_AI_VIDEO_BROLL
    from modules.asset_generator import generate_ai_video
    
    raw_scenes = generate_scene_data(content["chosen_topic"], content["seo_title"], content["script"], is_shorts)
    log.info(f"Director Agent created {len(raw_scenes)} dynamic scenes.")
    
    # Filter/Truncate for Shorts
    if is_shorts and total_duration <= 60:
         # Limit scenes if it's too long
         pass

    slide_data_list = []
    
    def to_file_url(path):
        if not path: return ""
        p = os.path.abspath(path).replace("\\", "/")
        return f"file:///{p}"
        
    current_frame = 0
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")

    for idx, scene in enumerate(raw_scenes):
        # Calculate duration based on words in this scene over total words
        # (This is approximate; precise timing comes from word_timings in Remotion)
        scene_word_count = max(len(scene["text"].split()), 1)
        total_word_count = sum([max(len(s["text"].split()), 1) for s in raw_scenes])
        bg_duration_sec = (scene_word_count / total_word_count) * total_duration
        bg_frames = int(bg_duration_sec * fps)
        
        # Ensure we don't exceed total_frames due to rounding
        if idx == len(raw_scenes) - 1:
            bg_frames = total_frames - current_frame

        h = scene["keyword"]
        orientation = "portrait" if is_shorts else "landscape"
        log.info(f"Finding footage for scene {idx}: {h}")
        
        stock_path = ""
        is_video = False
        
        if idx > 0:
             stock_path = get_stock_video(h, orientation=orientation, min_duration=int(bg_duration_sec))
             
        bg_path = stock_path
        is_video = bool(stock_path)
            
        if not bg_path:
            prompt = scene["prompt"]
            if USE_AI_VIDEO_BROLL:
                vid_path = generate_ai_video(prompt, job_id, idx, is_shorts=is_shorts)
                if vid_path and os.path.exists(vid_path):
                    bg_path = vid_path
                    is_video = True
                    
            if not bg_path:
                img_path = generate_ai_image(prompt, job_id, idx, width=(1080 if is_shorts else 1920), height=(1920 if is_shorts else 1080))
                if img_path and os.path.exists(img_path):
                    bg_path = img_path
                    is_video = False

        slide_data_list.append({
            "bgPath": to_file_url(bg_path),
            "isVideo": is_video,
            "durationInFrames": bg_frames,
            "startFrame": current_frame,
            "text": scene["text"] # We pass exact text to remotion for parsing
        })
        
        current_frame += bg_frames

    # Build Props dict
    title = content.get("title", "")
    script_text = content.get("script", "")
    # Generate a hook from first sentence of script, max 10 words
    first_sentence = script_text.split(".")[0].strip() if script_text else ""
    hook_words = first_sentence.split()
    hook_text = " ".join(hook_words[:10]) + ("..." if len(hook_words) > 10 else "") if first_sentence else "You NEED to see this!"

    props = {
        "slides": slide_data_list,
        "audioUrl": to_file_url(audio_path),
        "bgmUrl": to_file_url(bgm_path) if os.path.exists(bgm_path) else "",
        "wordTimings": word_timings,
        "isShorts": is_shorts,
        "hookText": hook_text,
        "title": title,
    }
    
    remotion_dir = os.path.abspath("remotion_app")
    public_dir = os.path.join(remotion_dir, "public")
    os.makedirs(public_dir, exist_ok=True)
    
    def file_url_to_path(url: str) -> str:
        """Convert file:/// URL to OS path."""
        if not isinstance(url, str):
            return ""
        if url.startswith("file:///"):
            p = url.replace("file:///", "")
            if os.name == "nt":
                return p.replace("/", "\\")
            return "/" + p
        return url

    def to_public_path(url_or_path: str) -> str:
        """Copy a file to remotion_app/public and return the absolute path from public dir.
        Remotion with --public-dir expects filenames relative to public dir using staticFile() in TSX.
        Since we're passing filenames via props.json we use just the filename.
        """
        real_path = file_url_to_path(url_or_path)
        if not real_path or not os.path.exists(real_path):
            return ""
        fname = os.path.basename(real_path)
        dest = os.path.join(public_dir, fname)
        if not os.path.exists(dest):
            shutil.copy2(real_path, dest)
        # Return just the filename - Remotion's staticFile() will resolve against public dir
        return fname
    
    # Update all paths in props to use just filename (resolved by staticFile in TSX)
    for slide in props["slides"]:
        slide["bgPath"] = to_public_path(str(slide.get("bgPath", "")))
    props["audioUrl"] = to_public_path(str(props.get("audioUrl", "")))
    if props.get("bgmUrl"):
        props["bgmUrl"] = to_public_path(str(props.get("bgmUrl", "")))
    
    props_path = os.path.join(remotion_dir, "props.json")
    with open(props_path, "w", encoding="utf-8") as f:
         json.dump(props, f, indent=2)
         
    # 4. Render using Remotion CLI
    abs_out_path = os.path.abspath(output_path)
    log.info(f"Triggering Remotion Renderer -> {abs_out_path}")
    
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [
        npx_cmd, "remotion", "render",
        "src/index.ts", "MainVideo",
        abs_out_path,
        "--props", "props.json",
        "--public-dir", public_dir,
        "--concurrency", "2",          # Limit CPU threads to avoid OOM on CI
        "--log", "verbose",
    ]
    
    try:
        subprocess.run(cmd, cwd=remotion_dir, check=True, timeout=4800)  # 80-min hard cap
        log.info("Remotion render completed successfully!")
    except subprocess.TimeoutExpired:
        log.error("Remotion render TIMED OUT after 80 minutes. Video not created.")
        return ""
    except subprocess.CalledProcessError as e:
        log.error(f"Remotion rendering failed with exit code {e.returncode}")
        return ""
    
    return output_path

# -----------------------------------------------------------------
#  THUMBNAIL GENERATOR
# -----------------------------------------------------------------

def create_thumbnail(content: dict, job_id: str, bg_path: str = "") -> str:
    """Generate a high-quality eye-catching thumbnail."""
    log.info("Creating eye-catching SEO thumbnail…")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    # 1. LOAD BACKGROUND
    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).resize((1280, 720))
    else:
        # Fallback to first slide or solid color
        bg_img = os.path.join(OUTPUT_DIR, f"{job_id}_img_0.jpg")
        if os.path.exists(bg_img):
            img = Image.open(bg_img).resize((1280, 720))
        else:
            img = Image.new("RGB", (1280, 720), (10, 15, 30))

    # 2. ENHANCE BACKGROUND (Vibrance/Darken Left for Text)
    # Add a darkening gradient on the left side to make text readable
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for x in range(0, 800):
        alpha = int(220 * (1 - x/800))
        o_draw.line([(x, 0), (x, 720)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # 3. DRAW TEXT
    draw = ImageDraw.Draw(img)
    try:
        font_main = ImageFont.truetype(FONT_PATH, 110)
        font_sub  = ImageFont.truetype(FONT_PATH, 60)
    except:
        font_main = ImageFont.load_default()
        font_sub  = font_main

    text = content.get("thumbnail_text", "AI REVOLUTION").upper()
    lines = textwrap.wrap(text, width=12)
    
    start_y = 150
    for line in lines:
        # Drawing with deep shadow for depth
        for off in range(2, 10, 2):
            draw.text((80+off, start_y+off), line, font=font_main, fill=(0, 0, 0, 150))
        
        # Main text (High Contrast)
        draw.text((80, start_y), line, font=font_main, fill=(255, 255, 255))
        
        # Add a colored highlight to specific lines or words
        if "AI" in line or "2025" in line or len(lines) == 1:
            draw.text((80, start_y), line, font=font_main, fill=(255, 215, 0)) # Gold
            
        start_y += 130

    # 4. BRADING / BORDER
    # Simple neon border
    border_color = (0, 255, 127) # Spring Green
    draw.rectangle([10, 10, 1270, 710], outline=border_color, width=8)

    img.save(thumb_path, "JPEG", quality=98)
    return thumb_path
