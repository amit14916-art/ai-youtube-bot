"""
modules/video_creator.py
Builds YouTube videos using pure FFmpeg — fast, memory-safe, no MoviePy crashes.
Works reliably on GitHub Actions with zero memory issues.
"""

import logging
import os
import subprocess
import textwrap
import random

from PIL import Image, ImageDraw, ImageFont

from config.settings import (
    ASSETS_DIR,
    FONT_PATH,
    OUTPUT_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
    FFMPEG_PATH,
)

log = logging.getLogger(__name__)


# -----------------------------------------------------------------
#  SLIDE IMAGE RENDERER (PIL only, no MoviePy)
# -----------------------------------------------------------------

def render_slide_image(text: str, bg_color: tuple, w: int, h: int,
                       is_title: bool = False, bg_image_path: str = "") -> str:
    """Render a single slide as a JPEG image using PIL."""
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            img = Image.open(bg_image_path).resize((w, h)).convert("RGB")
        except Exception:
            img = Image.new("RGB", (w, h), bg_color)
    else:
        img = Image.new("RGB", (w, h), bg_color)

    # Dark gradient overlay for readability
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_ov = ImageDraw.Draw(overlay)
    for y in range(h):
        alpha = int(160 * (y / h))
        draw_ov.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Font
    font_size = 90 if is_title else 72
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        small_font = ImageFont.truetype(FONT_PATH, 36)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Clean text
    clean = text.replace("Host A:", "").replace("Host B:", "").strip()
    wrapped = textwrap.wrap(clean, width=28 if is_title else 32)[:4]

    total_h = len(wrapped) * (font_size + 15)
    y = (h - total_h) // 2 if is_title else h - total_h - 120

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (w - lw) // 2
        # Shadow
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0, 200))
        # Text
        color = (255, 215, 0) if is_title else (255, 255, 255)
        draw.text((x, y), line, font=font, fill=color)
        y += font_size + 15

    # Branding
    draw.text((20, h - 50), "AI NEWS DAILY", font=small_font, fill=(255, 255, 255, 120))

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp = os.path.join(OUTPUT_DIR, f"_slide_{random.randint(10000,99999)}.jpg")
    img.save(tmp, "JPEG", quality=90)
    return tmp


# -----------------------------------------------------------------
#  SLIDE CONTENT SPLITTER
# -----------------------------------------------------------------

def script_to_slides(script: str, seo_title: str) -> list[str]:
    """Break script into chunks for slides."""
    import re
    lines = re.split(r'(Host [AB]:)', script)
    slides = [seo_title.upper()]
    current_host = ""
    for item in lines:
        item = item.strip()
        if not item:
            continue
        if item in ["Host A:", "Host B:"]:
            current_host = item
        else:
            words = item.split()
            for i in range(0, len(words), 20):
                chunk = " ".join(words[i:i + 20])
                slides.append(f"{current_host} {chunk}".strip())
    slides.append("LIKE  •  SUBSCRIBE  •  AI NEWS DAILY")
    return slides


# -----------------------------------------------------------------
#  FFMPEG VIDEO BUILDER — MAIN FUNCTION
# -----------------------------------------------------------------

def create_video(content: dict, audio_path: str, job_id: str,
                 is_shorts: bool = False) -> str:
    """Build MP4 video using pure FFmpeg. Fast, memory-safe, reliable."""
    from mutagen.mp3 import MP3

    w = 1080 if is_shorts else VIDEO_WIDTH
    h = 1920 if is_shorts else VIDEO_HEIGHT
    fps = VIDEO_FPS

    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log.info(f"=== Building {'Short' if is_shorts else 'Long'} Video (FFmpeg) ===")

    # 1. Audio duration
    try:
        total_duration = MP3(audio_path).info.length
    except Exception:
        total_duration = 120.0
    log.info(f"Audio duration: {total_duration:.1f}s")

    # 2. Create slides
    slides = script_to_slides(content["script"], content["seo_title"])
    n_slides = max(len(slides), 1)
    sec_per_slide = total_duration / n_slides

    # Try to get one background image
    from modules.asset_generator import generate_ai_image
    bg_path = generate_ai_image(
        content.get("thumbnail_prompt", content["chosen_topic"]),
        job_id, 0, width=w, height=h
    )

    # 3. Render each slide as image
    bg_colors = [
        (10, 15, 40), (15, 10, 40), (10, 30, 30),
        (30, 10, 20), (5, 20, 50), (20, 5, 35)
    ]
    slide_images = []
    for i, text in enumerate(slides):
        color = bg_colors[i % len(bg_colors)]
        # Only use bg_image for first 3 slides to save time
        bg = bg_path if i < 3 else ""
        img_path = render_slide_image(
            text, color, w, h,
            is_title=(i == 0),
            bg_image_path=bg
        )
        slide_images.append((img_path, sec_per_slide))
        log.info(f"Slide {i+1}/{n_slides} rendered")

    # 4. Create concat input file for FFmpeg
    concat_file = os.path.join(OUTPUT_DIR, f"{job_id}_concat.txt")
    with open(concat_file, "w") as f:
        for img_path, dur in slide_images:
            f.write(f"file '{os.path.abspath(img_path)}'\n")
            f.write(f"duration {dur:.3f}\n")
        # FFmpeg concat needs last file repeated
        if slide_images:
            f.write(f"file '{os.path.abspath(slide_images[-1][0])}'\n")

    # 5. Build with FFmpeg
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    has_bgm = os.path.exists(bgm_path)

    if has_bgm:
        # Mix voiceover + bgm
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-i", audio_path,
            "-i", bgm_path,
            "-filter_complex",
            f"[2:a]volume=0.08,aloop=loop=-1:size=2e+09[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-t", str(int(total_duration) + 2),
            output_path
        ]
    else:
        cmd = [
            FFMPEG_PATH, "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-vf", f"fps={fps},format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            output_path
        ]

    log.info(f"Running FFmpeg to render video...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"FFmpeg failed:\n{result.stderr[-2000:]}")
        # Cleanup
        _cleanup_slides(slide_images, concat_file)
        return ""

    log.info(f"Video rendered: {output_path}")
    _cleanup_slides(slide_images, concat_file)
    return output_path


def _cleanup_slides(slide_images, concat_file):
    """Remove temp slide images and concat file."""
    for img_path, _ in slide_images:
        try:
            os.remove(img_path)
        except Exception:
            pass
    try:
        os.remove(concat_file)
    except Exception:
        pass


# -----------------------------------------------------------------
#  THUMBNAIL GENERATOR
# -----------------------------------------------------------------

def create_thumbnail(content: dict, job_id: str, bg_path: str = "") -> str:
    """Generate a high-quality thumbnail."""
    log.info("Creating thumbnail...")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).resize((1280, 720))
    else:
        img = Image.new("RGB", (1280, 720), (10, 15, 40))

    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for x in range(0, 800):
        alpha = int(220 * (1 - x / 800))
        o_draw.line([(x, 0), (x, 720)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    try:
        font_main = ImageFont.truetype(FONT_PATH, 110)
        font_sub = ImageFont.truetype(FONT_PATH, 55)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = font_main

    text = content.get("thumbnail_text", "AI REVOLUTION").upper()
    lines = textwrap.wrap(text, width=12)
    start_y = 120
    for line in lines:
        # Shadow
        for off in range(2, 8, 2):
            draw.text((80 + off, start_y + off), line, font=font_main,
                      fill=(0, 0, 0, 150))
        color = (255, 215, 0) if "AI" in line or len(lines) == 1 else (255, 255, 255)
        draw.text((80, start_y), line, font=font_main, fill=color)
        start_y += 130

    draw.rectangle([10, 10, 1270, 710], outline=(0, 255, 127), width=8)
    img.save(thumb_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {thumb_path}")
    return thumb_path
