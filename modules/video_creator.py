"""
modules/video_creator.py
Builds a faceless YouTube video:
  • Animated gradient background
  • Text slides synced to voiceover duration
  • Background music (optional, from assets/bgm.mp3)
  • Subtle zoom / pan transitions
"""

import logging
import math
import os
import textwrap
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
)

log = logging.getLogger(__name__)
W, H = VIDEO_WIDTH, VIDEO_HEIGHT


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
                if len(chunk.split()) + len(s.split()) > 40:
                    slides.append(f"{current_host} {chunk.strip()}")
                    chunk = s
                else:
                    chunk += " " + s
            if chunk:
                slides.append(f"{current_host} {chunk.strip()}")

    slides.append("LIKE  •  SUBSCRIBE  •  TURN ON NOTIFICATIONS")
    return slides


# ─────────────────────────────────────────────────────────────────
#  BACKGROUND FRAME GENERATOR
# ─────────────────────────────────────────────────────────────────

# Color palettes — one chosen per video
PALETTES = [
    [(5, 10, 30), (20, 50, 120)],       # Deep blue
    [(10, 5, 30), (80, 20, 120)],       # Purple
    [(5, 20, 10), (10, 80, 50)],        # Deep green
    [(30, 10, 5), (120, 40, 10)],       # Deep orange
]

def make_gradient_frame(t: float, palette_idx: int = 0) -> np.ndarray:
    """Create an animated gradient background frame."""
    c1, c2 = PALETTES[palette_idx % len(PALETTES)]
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    # Animated gradient shift
    shift = int(50 * math.sin(t * 0.3))
    for y in range(H):
        ratio = y / H
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio + shift)
        b = max(0, min(255, b))
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return np.array(img)


# ─────────────────────────────────────────────────────────────────
#  SLIDE IMAGE RENDERER
# ─────────────────────────────────────────────────────────────────

def render_slide_image(text: str, is_title: bool = False) -> Image.Image:
    """Render a PIL image for a single text slide in Podcast style."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Detect Host
    host_label = ""
    if text.startswith("Host A:"):
        host_label = "Deep Dive Host"
        text = text.replace("Host A:", "").strip()
        card_color = (10, 30, 60, 180) # Blueish
    elif text.startswith("Host B:"):
        host_label = "Tech Expert"
        text = text.replace("Host B:", "").strip()
        card_color = (40, 10, 50, 180) # Purplish
    else:
        card_color = (0, 0, 0, 160)

    # Semi-transparent card
    card_x1, card_y1 = W // 10, H // 4
    card_x2, card_y2 = W - W // 10, H - H // 4
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.rounded_rectangle(
        [(card_x1, card_y1), (card_x2, card_y2)],
        radius=40,
        fill=card_color,
        outline=(255, 255, 255, 50),
        width=2
    )
    img = Image.alpha_composite(img, overlay)
    draw = ImageDraw.Draw(img)

    # Font
    try:
        font_size = 80 if is_title else 48
        font = ImageFont.truetype(FONT_PATH, font_size)
        label_font = ImageFont.truetype(FONT_PATH, 36)
        small_font = ImageFont.truetype(FONT_PATH, 32)
    except Exception:
        font = ImageFont.load_default()
        label_font = font
        small_font = font

    # Draw host label
    if host_label:
        draw.text((card_x1 + 50, card_y1 - 60), host_label.upper(), font=label_font, fill=(200, 200, 255, 255))

    # Wrap and center text
    max_chars = 25 if is_title else 50
    lines = textwrap.wrap(text, width=max_chars)
    line_height = font_size + 25
    total_h = line_height * len(lines)
    y = card_y1 + ( (card_y2 - card_y1) - total_h ) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        # Shadow
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200))
        # Main text with gradient color
        color = (255, 220, 50) if is_title else (240, 240, 255)
        draw.text((x, y), line, font=font, fill=color)
        y += line_height

    # Branding bar
    brand = "AGENTIC AI WORLD"
    bbox = draw.textbbox((0, 0), brand, font=small_font)
    bw = bbox[2] - bbox[0]
    draw.text(((W - bw) // 2, H - 80), brand, font=small_font, fill=(150, 150, 200, 220))

    return img.convert("RGB")


# ─────────────────────────────────────────────────────────────────
#  PARTICLE OVERLAY
# ─────────────────────────────────────────────────────────────────

def particles_frame(t: float) -> np.ndarray:
    """Small floating dots for visual interest."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = np.random.RandomState(42)  # fixed seed = stable positions
    positions = rng.rand(30, 2)
    for px, py in positions:
        x = int((px + 0.05 * math.sin(t * 0.5 + px * 10)) * W) % W
        y = int((py + 0.03 * math.cos(t * 0.4 + py * 8)) * H) % H
        r = rng.randint(2, 6)
        alpha = int(80 + 60 * math.sin(t + px * 6))
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(100, 150, 255, alpha))
    return np.array(img)


# ─────────────────────────────────────────────────────────────────
#  MAIN VIDEO BUILDER
# ─────────────────────────────────────────────────────────────────

def create_video(content: dict, audio_path: str, job_id: str) -> str:
    """Build the final MP4 video."""
    log.info("═══ Building Video ═══")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}_video.mp4")

    # 1. Load voiceover
    voice = AudioFileClip(audio_path)
    total_duration = voice.duration
    log.info(f"Voiceover duration: {total_duration:.1f}s")

    # 2. Extract slides
    slides = script_to_slides(content["script"], content["seo_title"])
    slide_duration = total_duration / len(slides)
    palette = hash(content["chosen_topic"]) % len(PALETTES)

    # 3. Build slides
    slide_clips = []
    for i, text in enumerate(slides):
        slide_img = render_slide_image(text, is_title=(i == 0))
        img_array = np.array(slide_img)
        
        def make_bg(t, _p=palette, _st=i * slide_duration):
            return make_gradient_frame(_st + t, _p)
            
        bg = VideoClip(make_bg, duration=slide_duration).with_fps(VIDEO_FPS)
        bg = bg.with_effects([vfx.Resize((W, H))])

        slide_clip = (ImageClip(img_array).with_duration(slide_duration).with_fps(VIDEO_FPS))
        zoom_factor = lambda t: 1.0 + 0.03 * (t / slide_duration)
        slide_clip = slide_clip.with_effects([vfx.Resize(zoom_factor)])

        composite = CompositeVideoClip([bg, slide_clip.with_position("center")])
        slide_clips.append(composite)

    # 4. Concatenate
    final_video = concatenate_videoclips(slide_clips, method="compose")

    # 5. Audio Mix
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    if os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path)
            # Loop BGM if shorter than video
            if bgm.duration < total_duration:
                # In MoviePy 2, there isn't a direct loop method for audio easily, 
                # but we can just use the duration if we use the right effect.
                # Actually, the simplest is to just use what we had if it works.
                pass 
            bgm = bgm.with_duration(total_duration).with_volume(BACKGROUND_MUSIC_VOLUME)
            final_video = final_video.with_audio(CompositeAudioClip([voice, bgm]))
            log.info("BGM mixed in")
        except Exception as e:
            log.warning(f"BGM mixing failed: {e}")
            final_video = final_video.with_audio(voice)
    else:
        final_video = final_video.with_audio(voice)

    # 6. Export
    log.info(f"Rendering video → {output_path}")
    final_video.write_videofile(
        output_path,
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )
    return output_path


# ─────────────────────────────────────────────────────────────────
#  THUMBNAIL GENERATOR
# ─────────────────────────────────────────────────────────────────

def create_thumbnail(content: dict, job_id: str) -> str:
    """Generate a clickable 1280×720 thumbnail image."""
    log.info("Creating thumbnail…")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    img = Image.new("RGB", (1280, 720))
    draw = ImageDraw.Draw(img)

    # Gradient background
    palette = hash(content["chosen_topic"]) % len(PALETTES)
    c1, c2 = PALETTES[palette]
    for y in range(720):
        r = int(c1[0] + (c2[0] - c1[0]) * y / 720)
        g = int(c1[1] + (c2[1] - c1[1]) * y / 720)
        b = int(c1[2] + (c2[2] - c1[2]) * y / 720)
        draw.line([(0, y), (1280, y)], fill=(r, g, b))

    # Bold text overlay
    try:
        font_big = ImageFont.truetype(FONT_PATH, 90)
        font_mid = ImageFont.truetype(FONT_PATH, 50)
    except Exception:
        font_big = font_mid = ImageFont.load_default()

    thumb_text = content.get("thumbnail_text", content["seo_title"][:40])
    lines = textwrap.wrap(thumb_text.upper(), width=18)

    y = 720 // 2 - (len(lines) * 110) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_big)
        lw = bbox[2] - bbox[0]
        x = (1280 - lw) // 2
        draw.text((x + 4, y + 4), line, font=font_big, fill=(0, 0, 0))
        draw.text((x, y), line, font=font_big, fill=(255, 220, 50))
        y += 110

    # Subtitle
    sub = "AGENTIC AI WORLD"
    bbox = draw.textbbox((0, 0), sub, font=font_mid)
    sw = bbox[2] - bbox[0]
    draw.text(((1280 - sw) // 2, 650), sub, font=font_mid, fill=(200, 200, 255))

    img.save(thumb_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved → {thumb_path}")
    return thumb_path
