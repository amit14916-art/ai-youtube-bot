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
import textwrap
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ColorClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    VideoClip,
    concatenate_videoclips,
    vfx
)

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
#  MAIN VIDEO BUILDER
# -----------------------------------------------------------------

def create_video(content: dict, audio_path: str, job_id: str, is_shorts: bool = False) -> str:
    """Build high-quality MP4 video with optimized memory usage."""
    import gc
    log.info(f"=== Building {'Short' if is_shorts else 'Long'} Video ===")
    
    cw, ch = (1080, 1920) if is_shorts else (VIDEO_WIDTH, VIDEO_HEIGHT)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")

    # 1. Load voiceover
    voice = AudioFileClip(audio_path)
    if is_shorts and voice.duration > 60:
        log.info("Trimming voiceover to 60s for Shorts...")
        voice = voice.subclipped(0, 59.5)
        
    total_duration = voice.duration
    log.info(f"Voiceover duration: {total_duration:.1f}s")
    
    # 2. Extract slides
    all_slides = script_to_slides(content["script"], content["seo_title"])
    
    if is_shorts:
        # For shorts, we force a specific duration to keep it fast
        slide_duration = 1.5 
        max_slides = int(total_duration / slide_duration)
        slides = all_slides[:max_slides]
        slide_duration = total_duration / len(slides)
    else:
        slides = all_slides
        slide_duration = total_duration / len(slides)
    
    # 3. Handle Graphics
    max_imgs = min(len(slides), 30 if not is_shorts else 15)
    log.info(f"Using {max_imgs} background images for {len(slides)} slides...")
    
    # 4. Create Clips in Batches (to save memory)
    final_clips = []
    
    # Group slides by background to reduce CompositeVideoClip count
    # Each background will last for (slides_per_bg * slide_duration) seconds
    slides_per_bg = max(1, len(slides) // max_imgs)
    
    for bg_idx in range(0, len(slides), slides_per_bg):
        current_slides = slides[bg_idx : bg_idx + slides_per_bg]
        total_bg_duration = len(current_slides) * slide_duration
        
        # Background: Try Real Stock Footage first, then AI Image
        img_idx = (bg_idx // slides_per_bg)
        hints = content.get("visual_hints", [content["chosen_topic"]])
        h = hints[img_idx % len(hints)]
        
        orientation = "portrait" if is_shorts else "landscape"
        log.info(f"Finding footage for sector {img_idx}: {h}")
        
        # Search Pexels for a video clip (only for tech/topic slides)
        stock_path = ""
        if img_idx > 0: # Title always AI Cinematic
             stock_path = get_stock_video(h, orientation=orientation, min_duration=int(total_bg_duration))
        
        if stock_path and os.path.exists(stock_path):
            try:
                log.info(f"Using stock footage: {stock_path}")
                bg = VideoFileClip(stock_path).with_duration(total_bg_duration).with_fps(VIDEO_FPS)
                # Resize and Crop to fill screen
                target_ratio = cw / ch
                current_ratio = bg.w / bg.h
                if current_ratio > target_ratio:
                    bg = bg.with_effects([vfx.Resize(height=ch)]).with_position(("center", "center"))
                else:
                    bg = bg.with_effects([vfx.Resize(width=cw)]).with_position(("center", "center"))
            except Exception as e:
                log.error(f"Stock footage load failed: {e}")
                stock_path = "" # Fallback
        
        if not stock_path:
            # Fallback to AI Image
            if img_idx == 0:
                prompt = f"Futuristic cinematic title screen, {content['chosen_topic']}, high tech, 4k"
            else:
                prompt = f"Cinematic AI visual: {h}, macro tech, futuristic, high quality"
                
            img_path = generate_ai_image(prompt, job_id, img_idx, width=cw, height=ch)
            if img_path and os.path.exists(img_path):
                pil_img = Image.open(img_path).convert("RGB")
                bg = ImageClip(np.array(pil_img)).with_duration(total_bg_duration).with_fps(VIDEO_FPS)
                bg = apply_ken_burns(bg, total_bg_duration)
            else:
                bg = ColorClip((cw, ch), color=(20, 20, 30)).with_duration(total_bg_duration)

        # Overlays for this background
        text_clips = []
        for s_idx, text in enumerate(current_slides):
            overlay_img = render_slide_overlay(text, cw, ch, is_title=(bg_idx == 0 and s_idx == 0), is_shorts=is_shorts)
            txt = ImageClip(np.array(overlay_img)).with_duration(slide_duration).with_start(s_idx * slide_duration).with_fps(VIDEO_FPS)
            text_clips.append(txt.with_position("center"))
        
        # Composite text clips over the single background clip
        batch_composite = CompositeVideoClip([bg] + text_clips)
        final_clips.append(batch_composite)
        
        # Cleanup temporary clips to free memory immediately
        # We can't close bg or text_clips yet because they are used in batch_composite
        # but we can call gc
        gc.collect()

    # 5. Concatenate & Audio
    # Memory optimization: using method="chain" prevents huge RAM spikes,
    # and all our clips are guaranteed to be the exact same dimensions!
    final_video = concatenate_videoclips(final_clips, method="chain")
    
    # BGM
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    if os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path)
            bgm = bgm.with_effects([vfx.AudioLoop(duration=total_duration)])
            bgm = bgm.with_volume(BACKGROUND_MUSIC_VOLUME)
            final_video = final_video.with_audio(CompositeAudioClip([voice, bgm]))
        except Exception as e:
            log.warning(f"BGM mixing failed: {e}")
            final_video = final_video.with_audio(voice)
    else:
        final_video = final_video.with_audio(voice)

    # 6. Render
    log.info(f"Exporting to: {output_path}")
    final_video.write_videofile(
        output_path,
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        logger="bar",  # Enable progress bar so we can see if it hangs
        threads=1      # Reduced from 4 to 1 to prevent Out-Of-Memory crashes
    )
    
    # Cleanup memory
    for c in final_clips: c.close()
    final_video.close()
    gc.collect()
    
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
