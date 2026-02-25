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

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────
#  SLIDE CONTENT EXTRACTION
# ─────────────────────────────────────────────────────────────────

def script_to_slides(script: str, seo_title: str) -> list[str]:
    """
    Break podcast script into slide-sized chunks, keeping host labels.
    """
    import re
    # Match the dialogue parts
    lines = re.split(r'(Host [AB]:)', script)
    
    slides = [seo_title.upper()] # Title slide
    
    current_host = ""
    for item in lines:
        item = item.strip()
        if not item: continue
        if item in ["Host A:", "Host B:"]:
            current_host = item
        else:
            # For each host's turn, break into readable sub-chunks if very long
            sentences = re.split(r'(?<=[.!?])\s+', item)
            chunk = ""
            for s in sentences:
                if len(chunk.split()) + len(s.split()) > 25: # Shorter chunks for better visuals
                    slides.append(f"{current_host} {chunk.strip()}")
                    chunk = s
                else:
                    chunk += " " + s
            if chunk:
                slides.append(f"{current_host} {chunk.strip()}")

    slides.append("LIKE  •  SUBSCRIBE  •  TURN ON NOTIFICATIONS")
    return slides


# ─────────────────────────────────────────────────────────────────
#  KEN BURNS EFFECT (SMOOTH ZOOM)
# ─────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────
#  SLIDE IMAGE OVERLAY RENDERER
# ─────────────────────────────────────────────────────────────────

def render_slide_overlay(text: str, w: int, h: int, is_title: bool = False, is_shorts: bool = False) -> Image.Image:
    """Render a transparent PIL image for text overlays."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)

    # Detect Host
    host_color = (100, 200, 255) # Default
    host_label = ""
    if text.startswith("Host A:"):
        host_label = "HOST A"
        text = text.replace("Host A:", "").strip()
        host_color = (0, 255, 255) # Cyan
    elif text.startswith("Host B:"):
        host_label = "HOST B"
        text = text.replace("Host B:", "").strip()
        host_color = (255, 100, 255) # Magenta
    
    # Scale font sizes for Shorts vs Landscape
    scale_factor = 0.8 if is_shorts else 1.0
    
    try:
        title_size = int(110 * scale_factor)
        caption_size = int(75 * scale_factor)
        label_size = int(45 * scale_factor)
        font_main = ImageFont.truetype(FONT_PATH, title_size if is_title else caption_size)
        font_host = ImageFont.truetype(FONT_PATH, label_size)
    except Exception:
        font_main = ImageFont.load_default()
        font_host = font_main

    # ─── DRAW TEXT (Subtitles Style) ───
    max_width_chars = 20 if is_shorts else (30 if is_title else 45)
    lines = textwrap.wrap(text, width=max_width_chars)
    line_h = (title_size if is_title else caption_size) + 15
    total_h = line_h * len(lines)
    
    # Vertically center for both
    y = (h - total_h) // 2
    if not is_shorts and not is_title:
        y += (h // 4) # Lower third for long landscape videos

    # Semi-transparent box for readability
    padding = 40
    box_w = int(w * 0.9) if is_shorts else int(w * 0.7)
    box_x_start = (w - box_w) // 2
    
    if not is_title and len(text) > 10:
        draw_overlay.rounded_rectangle(
            [box_x_start, y - padding, box_x_start + box_w, y + total_h + padding],
            radius=20,
            fill=(0, 0, 0, 160)
        )
        img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        lw = bbox[2] - bbox[0]
        x = (w - lw) // 2
        
        # Shadow
        draw.text((x + 2, y + 2), line, font=font_main, fill=(0, 0, 0, 200))
        
        # Main text
        color = (255, 220, 50) if is_title else (255, 255, 255)
        draw.text((x, y), line, font=font_main, fill=color)
        y += line_h

    # ─── HOST LABEL ───
    if host_label:
        label_text = f"🎙️ {host_label}"
        lx = 100 if not is_shorts else (w - 300) // 2
        ly = 150
        draw.text((lx + 2, ly + 2), label_text, font=font_host, fill=(0, 0, 0, 180))
        draw.text((lx, ly), label_text, font=font_host, fill=host_color)

    # ─── BRANDING ───
    if not is_shorts:
        brand = f"@{NICHE}"
        bbox = draw.textbbox((0, 0), brand, font=font_host)
        draw.text((w - (bbox[2]-bbox[0]) - 100, h - 100), brand, font=font_host, fill=(255,255,255, 80))

    return img

# ─────────────────────────────────────────────────────────────────
#  MAIN VIDEO BUILDER
# ─────────────────────────────────────────────────────────────────

def create_video(content: dict, audio_path: str, job_id: str, is_shorts: bool = False) -> str:
    """Build high-quality MP4 video with AI graphics."""
    log.info(f"═══ Building {'Short' if is_shorts else 'Long'} Video ═══")
    
    cw, ch = (1080, 1920) if is_shorts else (VIDEO_WIDTH, VIDEO_HEIGHT)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")

    # 1. Load voiceover
    voice = AudioFileClip(audio_path)
    total_duration = voice.duration
    log.info(f"Voiceover duration: {total_duration:.1f}s")
    
    # 2. Extract slides
    slides = script_to_slides(content["script"], content["seo_title"])
    slide_duration = total_duration / len(slides)
    
    # 3. Handle Graphics
    hints = content.get("visual_hints", [])
    if not hints: hints = [content["chosen_topic"]]
    
    bg_images = []
    # Generate background images - limit to 15 to save time/resources
    max_imgs = min(len(slides), 15)
    log.info(f"Generating up to {max_imgs} AI graphics...")
    
    for i in range(len(slides)):
        if i < max_imgs:
            if i == 0: 
                prompt = f"Futuristic cinematic title screen for {content['chosen_topic']}"
            else:
                h = hints[i % len(hints)]
                prompt = f"3D render, high quality, tech: {h}"
            
            img_path = generate_ai_image(prompt, job_id, i, width=cw, height=ch)
            bg_images.append(img_path)
            import time
            time.sleep(1.5) # Be polite to Pollinations.ai
        else:
            # Re-use generated images
            bg_images.append(bg_images[i % max_imgs])

    # 4. Create Clips
    slide_clips = []
    for i, text in enumerate(slides):
        # Background Clip
        img_path = bg_images[i]
        if img_path and os.path.exists(img_path):
            try:
                # Load with PIL first for robustness
                pil_img = Image.open(img_path).convert("RGB")
                bg = ImageClip(np.array(pil_img)).with_duration(slide_duration).with_fps(VIDEO_FPS)
            except Exception as e:
                log.error(f"Failed to load image {img_path}: {e}")
                bg = ColorClip((cw, ch), color=(20, 20, 30)).with_duration(slide_duration)
        else:
            bg = ColorClip((cw, ch), color=(20, 20, 30)).with_duration(slide_duration)
        
        # Transitions
        bg = apply_ken_burns(bg, slide_duration)
        
        # Text
        overlay_img = render_slide_overlay(text, cw, ch, is_title=(i == 0), is_shorts=is_shorts)
        txt = ImageClip(np.array(overlay_img)).with_duration(slide_duration).with_fps(VIDEO_FPS)
        
        composite = CompositeVideoClip([bg, txt.with_position("center")])
        slide_clips.append(composite)

    # 5. Concatenate & Audio
    final_video = concatenate_videoclips(slide_clips, method="compose")
    
    # BGM
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    if os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path)
            bgm = bgm.with_effects([vfx.AudioLoop(duration=total_duration)])
            bgm = bgm.with_volume(BACKGROUND_MUSIC_VOLUME)
            final_video = final_video.with_audio(CompositeAudioClip([voice, bgm]))
            log.info("BGM mixed in")
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
        logger=None,
        threads=4
    )
    return output_path

# ─────────────────────────────────────────────────────────────────
#  THUMBNAIL GENERATOR
# ─────────────────────────────────────────────────────────────────

def create_thumbnail(content: dict, job_id: str) -> str:
    """Generate a high-quality branded thumbnail."""
    log.info("Creating premium thumbnail…")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    # Use first AI image
    bg_img = os.path.join(OUTPUT_DIR, f"{job_id}_img_0.jpg")
    if os.path.exists(bg_img):
        img = Image.open(bg_img).resize((1280, 720))
        # Add slight darkening
        overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 80))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    else:
        img = Image.new("RGB", (1280, 720), (30, 40, 60))

    draw = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.truetype(FONT_PATH, 100)
    except:
        font_big = ImageFont.load_default()

    text = content.get("thumbnail_text", content["seo_title"][:40]).upper()
    lines = textwrap.wrap(text, width=15)
    y = 360 - (len(lines) * 60)
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        lw = bbox[2] - bbox[0]
        x = (1280 - lw) // 2
        # Outline
        for o in range(1, 5):
            draw.text((x+o, y+o), line, font=font_big, fill=(0,0,0))
        draw.text((x, y), line, font=font_big, fill=(255, 230, 0))
        y += 120

    img.save(thumb_path, "JPEG", quality=95)
    return thumb_path
