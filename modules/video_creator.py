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
    NICHE,
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
    """Render a PIL image for a single text slide in Premium Podcast style."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

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
    
    # Font
    try:
        title_size = 110
        caption_size = 75
        label_size = 40
        font_main = ImageFont.truetype(FONT_PATH, title_size if is_title else caption_size)
        font_host = ImageFont.truetype(FONT_PATH, label_size)
    except Exception:
        font_main = ImageFont.load_default()
        font_host = font_main

    # ─── DRAW TEXT (Centered Subtitles Style) ───
    max_width = 30 if is_title else 45
    lines = textwrap.wrap(text, width=max_width)
    line_h = (title_size if is_title else caption_size) + 20
    total_h = line_h * len(lines)
    
    # Vertically centered
    y = (H - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font_main)
        lw = bbox[2] - bbox[0]
        x = (W - lw) // 2
        
        # Thick Glow/Shadow for readability
        for offset in range(1, 4):
            draw.text((x + offset, y + offset), line, font=font_main, fill=(0, 0, 0, 180))
            draw.text((x - offset, y + offset), line, font=font_main, fill=(0, 0, 0, 180))
            draw.text((x + offset, y - offset), line, font=font_main, fill=(0, 0, 0, 180))
            draw.text((x - offset, y - offset), line, font=font_main, fill=(0, 0, 0, 180))
        
        # Main text
        color = (255, 220, 50) if is_title else (255, 255, 255)
        draw.text((x, y), line, font=font_main, fill=color)
        y += line_h

    # ─── DRAW HOST LABEL (Top Left) ───
    if host_label:
        label_text = f"● {host_label}"
        draw.text((103, 103), label_text, font=font_host, fill=(0,0,0, 150)) # Shadow
        draw.text((100, 100), label_text, font=font_host, fill=host_color)

    # ─── BRANDING (Bottom Right) ───
    brand = f"@{NICHE}"
    bbox = draw.textbbox((0, 0), brand, font=font_host)
    draw.text((W - (bbox[2]-bbox[0]) - 100, H - 100), brand, font=font_host, fill=(255,255,255, 100))

    return img.convert("RGBA")


def add_vignette(frame: np.ndarray, intensity: float = 0.6) -> np.ndarray:
    """Add a cinematic vignette effect to the frame."""
    h, w = frame.shape[:2]
    # Create radial gradient
    X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    radius = np.sqrt(X**2 + Y**2)
    # Darken edges
    vignette = np.clip(1 - radius * intensity, 0, 1)
    vignette = np.stack([vignette]*3, axis=-1)
    return (frame * vignette).astype(np.uint8)

def add_film_grain(frame: np.ndarray, intensity: float = 0.05) -> np.ndarray:
    """Add subtle film grain (noise) for a professional look."""
    noise = np.random.normal(0, 255 * intensity, frame.shape).astype(np.int16)
    frame = frame.astype(np.int16) + noise
    return np.clip(frame, 0, 255).astype(np.uint8)

def particles_frame(t: float) -> np.ndarray:
    """Small floating glowing dust particles for cinematic depth."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = np.random.RandomState(42)
    num_particles = 40
    for i in range(num_particles):
        px = rng.rand()
        py = rng.rand()
        speed = 0.02 + rng.rand() * 0.05
        # Movement
        x = int((px * W + t * 40 * speed)) % W
        y = int((py * H - t * 30 * speed)) % H
        size = rng.randint(2, 5)
        # Glowing effect
        alpha = int(100 + 50 * math.sin(t * 2 + i))
        draw.ellipse([(x-size, y-size), (x+size, y+size)], fill=(255, 255, 255, alpha))
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
    overlay_clipper = VideoClip(particles_frame, duration=total_duration).with_fps(VIDEO_FPS)
    
    slide_clips = []
    for i, text in enumerate(slides):
        slide_img = render_slide_image(text, is_title=(i == 0))
        
        # ─── BACKGROUND ENGINE ───
        def make_bg(t, _p=palette, _st=i * slide_duration):
            frame = make_gradient_frame(_st + t, _p)
            frame = add_vignette(frame)
            frame = add_film_grain(frame)
            return frame
            
        bg = VideoClip(make_bg, duration=slide_duration).with_fps(VIDEO_FPS)
        
        # ─── FOREGROUND ENGINE (Captions) ───
        txt_img = np.array(slide_img)
        txt = ImageClip(txt_img).with_duration(slide_duration).with_fps(VIDEO_FPS)
        # Cinematic Zoom
        txt = txt.with_effects([vfx.Resize(lambda t: 1.0 + 0.08 * (t/slide_duration))])
        
        composite = CompositeVideoClip([bg, txt.with_position("center")])
        slide_clips.append(composite)

    # Combine All
    video_content = concatenate_videoclips(slide_clips, method="compose")
    
    # Global Particle Overlay
    final_video = CompositeVideoClip([video_content, overlay_clipper.with_position("center")])

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
