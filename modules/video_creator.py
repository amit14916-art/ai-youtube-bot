"""
modules/video_creator.py
Builds YouTube videos using FFmpeg + Pexels stock footage + PIL text overlays.
Director Agent plans scene keywords → Pexels downloads clips → FFmpeg assembles.
Fast, memory-safe, no MoviePy crashes. Works reliably on GitHub Actions.
"""

import logging
import os
import subprocess
import textwrap
import random
import tempfile

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
                       is_title: bool = False, bg_image_path: str = "",
                       show_branding: bool = True) -> str:
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
        alpha = int(170 * (y / h))
        draw_ov.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # Font
    font_size = 90 if is_title else 68
    small_size = 36
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        small_font = ImageFont.truetype(FONT_PATH, small_size)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Clean text
    clean = text.replace("Host A:", "").replace("Host B:", "").strip()
    wrap_w = 24 if is_title else 32
    wrapped = textwrap.wrap(clean, width=wrap_w)[:5]

    total_h = len(wrapped) * (font_size + 15)
    y_pos = (h - total_h) // 2 if is_title else h - total_h - 130

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        x = (w - lw) // 2
        # Shadow
        draw.text((x + 3, y_pos + 3), line, font=font, fill=(0, 0, 0, 200))
        draw.text((x + 6, y_pos + 6), line, font=font, fill=(0, 0, 0, 100))
        # Text
        color = (255, 215, 0) if is_title else (255, 255, 255)
        draw.text((x, y_pos), line, font=font, fill=color)
        y_pos += font_size + 15

    # Branding bar
    if show_branding:
        bar_h = 55
        bar_rect = Image.new("RGBA", (w, bar_h), (0, 0, 0, 0))
        bar_draw = ImageDraw.Draw(bar_rect)
        bar_draw.rectangle([0, 0, w, bar_h], fill=(0, 0, 0, 160))
        img_rgba = img.convert("RGBA")
        img_rgba.paste(bar_rect, (0, h - bar_h), bar_rect)
        img = img_rgba.convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.text((20, h - bar_h + 10), "🤖  AI NEWS DAILY", font=small_font, fill=(200, 200, 200))

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tmp = os.path.join(OUTPUT_DIR, f"_slide_{random.randint(100000, 999999)}.jpg")
    img.save(tmp, "JPEG", quality=92)
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
            for i in range(0, len(words), 22):
                chunk = " ".join(words[i:i + 22])
                slides.append(f"{current_host} {chunk}".strip())
    slides.append("LIKE  •  SUBSCRIBE  •  AI NEWS DAILY")
    return slides


# -----------------------------------------------------------------
#  PEXELS CLIP DOWNLOADER (with scene keywords)
# -----------------------------------------------------------------

def get_pexels_clip_for_scene(keyword: str, job_id: str, index: int, is_shorts: bool = False) -> str:
    """
    Download a Pexels clip for the given keyword.
    Returns local path or empty string if unavailable.
    """
    try:
        from modules.pexels_manager import get_stock_video
        orient = "portrait" if is_shorts else "landscape"
        clip_path = get_stock_video(keyword, orientation=orient, min_duration=4)
        return clip_path or ""
    except Exception as e:
        log.warning(f"Pexels clip fetch failed for '{keyword}': {e}")
        return ""


# -----------------------------------------------------------------
#  OVERLAY TEXT ON VIDEO CLIP (FFmpeg drawtext)
# -----------------------------------------------------------------

def create_text_overlay_clip(
    video_clip_path: str,
    text: str,
    duration: float,
    output_path: str,
    w: int,
    h: int,
    is_title: bool = False,
    ffmpeg_path: str = None
) -> bool:
    """
    Use FFmpeg to trim a video clip to 'duration' seconds and overlay text.
    Returns True on success.
    """
    ffmpeg = ffmpeg_path or FFMPEG_PATH
    clean_text = text.replace("Host A:", "").replace("Host B:", "").strip()
    # Escape special characters for FFmpeg drawtext filter parsing
    # Commas must be escaped with a backslash in filter strings
    clean_text = clean_text.replace("\\", "/").replace("'", "").replace("%", "%%")
    clean_text = clean_text.replace(":", "\\:").replace(",", "\\,")

    # Wrap text at ~38 chars for overlay
    wrapped = textwrap.wrap(clean_text, width=38)[:4]
    joined = "\\n".join(wrapped)

    # Font settings
    font_size = 72 if is_title else 56
    text_color = "yellow" if is_title else "white"

    # Try to find a font that exists
    font_arg = ""
    for fp in [FONT_PATH,
               "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
               "/usr/share/fonts/truetype/open-sans/OpenSans-Bold.ttf",
               "C:/Windows/Fonts/arialbd.ttf"]:
        if fp and os.path.exists(fp):
            # Replace backslashes with forward slashes for FFmpeg filter parsing
            fp_clean = fp.replace("\\", "/")
            font_arg = f":fontfile='{fp_clean}'"
            break

    # Text position: center-bottom area
    text_y = "h-text_h-100" if not is_title else "(h-text_h)/2"

    # Build drawtext filter with shadow
    shadow = (
        f"drawtext=text='{joined}'{font_arg}"
        f":fontsize={font_size}:fontcolor=black@0.8"
        f":x=(w-text_w)/2+3:y={text_y}+3:line_spacing=8"
    )
    main_text = (
        f"drawtext=text='{joined}'{font_arg}"
        f":fontsize={font_size}:fontcolor={text_color}@0.95"
        f":x=(w-text_w)/2:y={text_y}:line_spacing=8"
    )
    branding = (
        f"drawtext=text='AI NEWS DAILY'{font_arg}"
        f":fontsize=30:fontcolor=white@0.6"
        f":x=20:y=h-45"
    )
    subscribe_cta = (
        f"drawtext=text='SUBSCRIBE'{font_arg}"
        f":fontsize=35:fontcolor=white@0.95"
        f":x=w-text_w-30:y=h-50"
        f":box=1:boxcolor=red@0.8:boxborderw=10"
    )
    # Crop perfectly instead of squashing
    scale_crop = f"scale='max({w},a*{h})':'max({h},{w}/a)',crop={w}:{h}"
    full_filter = f"{scale_crop},setsar=1,{shadow},{main_text},{branding},{subscribe_cta}"

    cmd = [
        ffmpeg, "-y",
        "-ss", "0",
        "-i", video_clip_path,
        "-t", str(max(duration, 1.0)),
        "-vf", full_filter,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-an",  # No audio (we'll mix later)
        "-r", str(VIDEO_FPS),
        "-pix_fmt", "yuv420p",
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log.warning(f"FFmpeg drawtext failed (scene): {result.stderr[-600:]}")
        return False
    return True


# -----------------------------------------------------------------
#  IMAGE SLIDE → VIDEO CLIP (fallback when no Pexels)
# -----------------------------------------------------------------

def image_to_video_clip(image_path: str, duration: float, output_path: str,
                        w: int, h: int) -> bool:
    """Convert a PIL image into a short video clip using FFmpeg."""
    cmd = [
        FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", image_path,
        "-t", str(max(duration, 1.0)),
        "-vf", f"scale={w}:{h},setsar=1",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        log.warning(f"image_to_video_clip failed: {result.stderr[-400:]}")
        return False
    return True


# -----------------------------------------------------------------
#  FFMPEG VIDEO BUILDER — MAIN FUNCTION
# -----------------------------------------------------------------

def create_video(content: dict, audio_path: str, job_id: str,
                 is_shorts: bool = False) -> str:
    """
    Build MP4 video using:
    - Director Agent → scene plan with Pexels keywords
    - Pexels stock video clips per scene
    - FFmpeg drawtext overlays for on-screen text
    - Audio voiceover + optional BGM
    Fast, memory-safe, reliable.
    """
    from mutagen.mp3 import MP3

    w = 1080 if is_shorts else VIDEO_WIDTH
    h = 1920 if is_shorts else VIDEO_HEIGHT
    fps = VIDEO_FPS

    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    log.info(f"=== Building {'Short' if is_shorts else 'Long'} Video (FFmpeg+Pexels) ===")

    # 1. Audio duration
    try:
        total_duration = MP3(audio_path).info.length
    except Exception:
        total_duration = 120.0
    log.info(f"Audio duration: {total_duration:.1f}s")

    # 2. Director Agent — plan scenes
    try:
        from modules.director_agent import generate_scene_data
        scenes = generate_scene_data(
            content.get("chosen_topic", "AI"),
            content.get("seo_title", "AI Video"),
            content.get("script", ""),
            is_shorts
        )
        log.info(f"Director planned {len(scenes)} scenes")
    except Exception as e:
        log.warning(f"Director agent failed ({e}), using slide fallback")
        scenes = []

    # Fallback to simple slides if no scenes
    if not scenes:
        slides = script_to_slides(content["script"], content["seo_title"])
        scenes = [{"text": s, "keyword": "technology artificial intelligence"} for s in slides]

    # 3. Word-count proportional timing to sync text precisely to audio
    total_words = sum(max(1, len(str(scene.get("text", "")).split())) for scene in scenes)
    n_scenes = max(len(scenes), 1)
    sec_per_scene = total_duration / n_scenes
    log.info(f"Scenes: {n_scenes}, Expected Words: {total_words}, Duration: {total_duration:.1f}s")

    # 3. Get background image for fallback
    try:
        from modules.asset_generator import generate_ai_image
        bg_path = generate_ai_image(
            content.get("thumbnail_prompt", content.get("chosen_topic", "AI technology")),
            job_id, 0, width=w, height=h
        )
    except Exception:
        bg_path = ""

    # 4. Build each scene as a video clip
    clip_files = []
    temp_files = []

    for i, scene in enumerate(scenes):
        scene_text = scene.get("text", "")
        keyword = scene.get("keyword", "technology")
        is_title_slide = (i == 0)
        
        # Exact proportional clip duration
        words_in_scene = max(1, len(str(scene_text).split()))
        clip_duration = max((words_in_scene / total_words) * total_duration, 2.0)

        clip_out = os.path.join(OUTPUT_DIR, f"{job_id}_clip_{i:04d}.mp4")

        log.info(f"Scene {i+1}/{n_scenes}: '{keyword}' → {clip_duration:.1f}s")

        # Try Pexels first
        pexels_path = get_pexels_clip_for_scene(keyword, job_id, i, is_shorts)

        if pexels_path and os.path.exists(pexels_path):
            # Overlay text on Pexels clip
            ok = create_text_overlay_clip(
                pexels_path, scene_text, clip_duration, clip_out, w, h,
                is_title=is_title_slide
            )
            if ok:
                clip_files.append(clip_out)
                temp_files.append(clip_out)
                continue
            else:
                log.warning(f"Text overlay failed for scene {i+1}, falling back to image slide")

        # Fallback: PIL image slide → video clip (Unique AI Background)
        try:
            from modules.asset_generator import generate_ai_image
            # Pollinations generates highly detailed scene image
            scene_bg = generate_ai_image(scene.get("prompt", keyword), job_id, i+100, width=w, height=h)
        except Exception:
            scene_bg = ""

        img_path = render_slide_image(
            scene_text,
            bg_color=[(10, 15, 40), (15, 10, 45), (10, 30, 30), (30, 10, 20), (5, 20, 50), (20, 5, 35)][i % 6],
            w=w, h=h,
            is_title=is_title_slide,
            bg_image_path=scene_bg if scene_bg else bg_path
        )
        temp_files.append(img_path)

        clip_ok = image_to_video_clip(img_path, clip_duration, clip_out, w, h)
        if clip_ok:
            clip_files.append(clip_out)
            temp_files.append(clip_out)
        else:
            log.warning(f"Scene {i+1} clip creation failed, skipping")

    if not clip_files:
        log.error("No clips were created! Cannot build video.")
        _cleanup_temp(temp_files)
        return ""

    # 5. Concatenate all clips
    log.info(f"Concatenating {len(clip_files)} clips...")
    concat_file = os.path.join(OUTPUT_DIR, f"{job_id}_concat.txt")
    with open(concat_file, "w") as f:
        for cp in clip_files:
            abs_path = os.path.abspath(cp).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")
    temp_files.append(concat_file)

    raw_video = os.path.join(OUTPUT_DIR, f"{job_id}_raw.mp4")
    concat_cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "26",
        "-pix_fmt", "yuv420p",
        raw_video
    ]
    result = subprocess.run(concat_cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log.error(f"Concat failed:\n{result.stderr[-2000:]}")
        _cleanup_temp(temp_files)
        return ""
    temp_files.append(raw_video)

    # 6. Mix audio (voiceover + optional BGM)
    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    has_bgm = os.path.exists(bgm_path)

    log.info("Mixing audio into final video...")
    if has_bgm:
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", raw_video,
            "-i", audio_path,
            "-i", bgm_path,
            "-filter_complex",
            "[2:a]volume=0.08,aloop=loop=-1:size=2e+09[bgm];[1:a][bgm]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-t", str(int(total_duration) + 3),
            output_path
        ]
    else:
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", raw_video,
            "-i", audio_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest",
            "-t", str(int(total_duration) + 3),
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log.error(f"Audio mix failed:\n{result.stderr[-2000:]}")
        _cleanup_temp(temp_files)
        return ""

    log.info(f"✅ Video rendered: {output_path}")
    _cleanup_temp(temp_files)
    return output_path


def _cleanup_temp(files: list):
    """Remove temp files."""
    for f in files:
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass


def create_thumbnail(content: dict, job_id: str, bg_path: str = "") -> str:
    """Generate a high-quality, eye-catching thumbnail."""
    log.info("Creating thumbnail...")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).resize((1280, 720)).convert("RGB")
    else:
        img = Image.new("RGB", (1280, 720), (10, 15, 40))

    # Add a subtle vignette instead of a heavy black block to preserve the AI background details
    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for y in range(0, 150):
        alpha = int(120 * (1 - y / 150))
        o_draw.line([(0, y), (1280, y)], fill=(0, 0, 0, alpha))
        o_draw.line([(0, 720 - y), (1280, 720 - y)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    
    draw = ImageDraw.Draw(img)
    try:
        font_main = ImageFont.truetype(FONT_PATH, 105)
        font_sub = ImageFont.truetype(FONT_PATH, 50)
        font_brand = ImageFont.truetype(FONT_PATH, 38)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub = font_main
        font_brand = font_main

    # Main text
    text = content.get("thumbnail_text", "AI REVOLUTION").upper()
    lines = textwrap.wrap(text, width=15)
    start_y = 120
    for line in lines:
        color = (255, 230, 0) if ("AI" in line or len(lines) == 1) else (255, 255, 255)
        # Deep shadow layer
        draw.text((70 + 8, start_y + 8), line, font=font_main, fill=(0, 0, 0, 180))
        # Stroke + Fill layer
        try:
            draw.text((70, start_y), line, font=font_main, fill=color, stroke_width=6, stroke_fill=(0, 0, 0))
        except TypeError:
            # Fallback for old pillow
            for off_x in [-3,0,3]:
                for off_y in [-3,0,3]:
                    draw.text((70 + off_x, start_y + off_y), line, font=font_main, fill=(0,0,0))
            draw.text((70, start_y), line, font=font_main, fill=color)
        start_y += 115

    # Hook line
    hook = content.get("hook_line", "")[:80]
    if hook:
        wrapped_hook = textwrap.wrap(hook, width=45)[:2]
        y_hook = start_y + 20
        for hl in wrapped_hook:
            # Black shadow + stroke for hook
            draw.text((72, y_hook + 3), hl, font=font_sub, fill=(0, 0, 0))
            try:
                draw.text((70, y_hook), hl, font=font_sub, fill=(200, 255, 255), stroke_width=3, stroke_fill=(0,0,0))
            except TypeError:
                draw.text((70, y_hook), hl, font=font_sub, fill=(200, 255, 255))
            y_hook += 55

    # Brand border
    draw.rectangle([8, 8, 1272, 712], outline=(0, 200, 100), width=7)

    # Channel branding pill
    try:
        pill_img = Image.new("RGBA", (260, 55), (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_img)
        pill_draw.rounded_rectangle([0, 0, 259, 54], radius=27, fill=(255, 50, 50, 220))
        img = img.convert("RGBA")
        img.paste(pill_img, (1000, 655), pill_img)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.text((1010, 668), "AI NEWS DAILY", font=font_brand, fill=(255, 255, 255))
    except Exception:
        pass  # Older Pillow may not support rounded_rectangle

    img.save(thumb_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {thumb_path}")
    return thumb_path
