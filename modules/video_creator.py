"""
modules/video_creator.py
Builds YouTube videos using FFmpeg + Pexels stock footage + PIL text overlays.
Director Agent plans scene keywords → Pexels downloads clips → FFmpeg assembles.
Fast, memory-safe, no MoviePy crashes. Works reliably on GitHub Actions.
"""

import logging
import os
import re
import subprocess
import textwrap
import random
import tempfile
import hashlib

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
#  MARKDOWN CLEANER — strips LLM formatting artifacts
# -----------------------------------------------------------------

def clean_markdown(text: str) -> str:
    """
    Remove markdown formatting that LLMs inject into titles/hooks.
    e.g. **BUILD YOUR OWN ROBOT** → BUILD YOUR OWN ROBOT
    """
    if not text:
        return text
    # Remove bold/italic markers: **, *, __, _
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    # Remove headers: ## Title → Title
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    # Remove backticks
    text = text.replace('`', '')
    # Collapse extra whitespace
    text = re.sub(r'  +', ' ', text)
    return text.strip()


# Encoding quality tuning for better YouTube output
FINAL_VIDEO_PRESET = "medium"
FINAL_VIDEO_CRF = 20
INTERMEDIATE_CLIP_PRESET = "fast"
INTERMEDIATE_CLIP_CRF = 24
FADE_DURATION = 0.55

try:
    import imageio_ffmpeg
    detected_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    if detected_ffmpeg and os.path.exists(detected_ffmpeg):
        FFMPEG_PATH = detected_ffmpeg
except Exception:
    pass


# -----------------------------------------------------------------
#  SLIDE IMAGE RENDERER (PIL only, no MoviePy)
# -----------------------------------------------------------------

def render_slide_image(text: str, bg_color: tuple, w: int, h: int,
                       is_title: bool = False, bg_image_path: str = "",
                       show_branding: bool = True, avatar_path: str = "",
                       paste_avatar: bool = True) -> str:
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
    if avatar_path and paste_avatar:
        img = _paste_presenter_avatar(img, avatar_path, w, h)

    draw = ImageDraw.Draw(img)

    # Font
    font_size = 90 if is_title else 68
    if avatar_path and h <= w:
        font_size = 60 if is_title else 52
    small_size = 36
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
        small_font = ImageFont.truetype(FONT_PATH, small_size)
    except Exception:
        font = ImageFont.load_default()
        small_font = font

    # Clean text — strip markdown AND host labels
    clean = clean_markdown(text.replace("Host A:", "").replace("Host B:", "")).strip()
    wrap_w = 24 if is_title else 32
    if avatar_path and h <= w:
        wrap_w = 24
    wrapped = textwrap.wrap(clean, width=wrap_w)[:5]

    total_h = len(wrapped) * (font_size + 15)
    y_pos = (h - total_h) // 2 if is_title else h - total_h - 130

    for line in wrapped:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        if avatar_path and h <= w:
            text_left = 45
            text_right = w - int(w * 0.42)
            x = text_left + max(0, (text_right - text_left - lw) // 2)
        else:
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
        draw.text((20, h - bar_h + 10), "AI NEWS DAILY", font=small_font, fill=(200, 200, 200))

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

def get_pexels_clip_for_scene(keyword: str, job_id: str, index: int, is_shorts: bool = False, alt_keyword: str = "") -> str:
    """
    Download a Pexels clip for the given keyword.
    Returns local path or empty string if unavailable.
    """
    try:
        from modules.pexels_manager import get_stock_video
        orient = "portrait" if is_shorts else "landscape"
        clip_path = get_stock_video(
            query=keyword,
            alt_query=alt_keyword,
            orientation=orient,
            min_duration=4,
            scene_index=index,
            job_id=job_id,
        )
        return clip_path or ""
    except Exception as e:
        log.warning(f"Pexels clip fetch failed for '{keyword}': {e}")
        return ""


def _ffmpeg_text_x(width: int, has_avatar: bool, is_title: bool) -> str:
    """Return drawtext x expression, reserving space for presenter in landscape."""
    if has_avatar:
        left = int(width * 0.035)
        area_w = int(width * 0.55)
        return f"{left}+({area_w}-text_w)/2"
    return "(w-text_w)/2"


def _talking_avatar_filter(input_label: str, output_label: str, avatar_w: int) -> str:
    """FFmpeg filter that makes the presenter card visibly 'talk' with mouth motion."""
    mouth_h = "if(lt(mod(t\\,0.36)\\,0.18)\\,ih*0.040\\,ih*0.014)"
    return (
        f"{input_label}scale={avatar_w}:-1,format=rgba,"
        f"drawbox=x=iw*0.41:y=ih*0.585:w=iw*0.18:h='{mouth_h}':color=black@0.72:t=fill,"
        f"drawbox=x=iw*0.435:y=ih*0.605:w=iw*0.11:h='ih*0.006':color=white@0.55:t=fill,"
        f"drawbox=x=iw*0.08:y=ih*0.91:w='if(lt(mod(t\\,0.50)\\,0.25)\\,iw*0.18\\,iw*0.08)':h=ih*0.012:color=white@0.72:t=fill,"
        f"drawbox=x=iw*0.30:y=ih*0.91:w='if(lt(mod(t\\,0.42)\\,0.21)\\,iw*0.22\\,iw*0.10)':h=ih*0.012:color=white@0.72:t=fill,"
        f"drawbox=x=iw*0.56:y=ih*0.91:w='if(lt(mod(t\\,0.58)\\,0.29)\\,iw*0.20\\,iw*0.07)':h=ih*0.012:color=white@0.72:t=fill"
        f"{output_label}"
    )


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
    ffmpeg_path: str = None,
    avatar_path: str = "",
    lower_third_text: str = ""
) -> bool:
    """
    Use FFmpeg to trim a video clip to 'duration' seconds and overlay text.
    Returns True on success.
    """
    ffmpeg = ffmpeg_path or FFMPEG_PATH
    clean_text = clean_markdown(text).replace("Host A:", "").replace("Host B:", "").strip()
    # Escape special characters for FFmpeg drawtext filter parsing
    # Commas must be escaped with a backslash in filter strings
    clean_text = clean_text.replace("\\", "/").replace("'", "").replace("%", "%%")
    clean_text = clean_text.replace(":", "\\:").replace(",", "\\,")

    has_avatar = bool(avatar_path and os.path.exists(avatar_path))

    # Wrap text; leave room for the presenter face-cam on landscape videos.
    wrap_chars = 24 if has_avatar and h <= w else 38
    wrapped = textwrap.wrap(clean_text, width=wrap_chars)[:4]
    joined = "\\n".join(wrapped)

    # Font settings
    font_size = 72 if is_title else 56
    if has_avatar and h <= w:
        font_size = 54 if is_title else 46
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
        f":x={_ffmpeg_text_x(w, has_avatar, is_title)}+3:y={text_y}+3:line_spacing=8"
    )
    main_text = (
        f"drawtext=text='{joined}'{font_arg}"
        f":fontsize={font_size}:fontcolor={text_color}@0.95"
        f":x={_ffmpeg_text_x(w, has_avatar, is_title)}:y={text_y}:line_spacing=8"
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
    lower_third = ""
    if lower_third_text:
        safe_lower = lower_third_text.replace("\\", "/").replace("'", "").replace("%", "%%")
        safe_lower = safe_lower.replace(":", "\\:").replace(",", "\\,")
        lower_third = (
            f"drawbox=x=0:y=h-100:w=w:h=100:color=black@0.45:t=fill,"
            f"drawbox=x=20:y=h-90:w=8:h=60:color=yellow@0.92:t=fill,"
            f"drawtext=text='{safe_lower}'{font_arg}"
            f":fontsize=32:fontcolor=white:x=40:y=h-70:line_spacing=6"
        )
    # Crop perfectly instead of squashing
    fade_st = max(duration - FADE_DURATION, 0.05)
    scale_crop = f"scale='max({w},a*{h})':'max({h},{w}/a)',crop={w}:{h}"
    text_filter = f"{scale_crop},setsar=1,{shadow},{main_text},{branding},{subscribe_cta}"
    if lower_third:
        text_filter = f"{text_filter},{lower_third}"
    text_filter = (
        f"{text_filter},fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={fade_st}:d={FADE_DURATION}"
    )

    if has_avatar:
        avatar_w = int(w * 0.34) if h <= w else int(w * 0.42)
        avatar_x = f"main_w-overlay_w-{int(w * 0.025)}"
        avatar_y = str(int(h * 0.10)) if h > w else f"(main_h-overlay_h)/2"
        full_filter = (
            f"[0:v]{text_filter}[base];"
            f"{_talking_avatar_filter('[1:v]', '[avatar]', avatar_w)};"
            f"[base][avatar]overlay=x={avatar_x}:y={avatar_y}:format=auto"
        )
        cmd = [
            ffmpeg, "-y",
            "-ss", "0",
            "-i", video_clip_path,
            "-loop", "1",
            "-t", str(max(duration, 1.0)),
            "-i", avatar_path,
            "-t", str(max(duration, 1.0)),
            "-filter_complex", full_filter,
            "-c:v", "libx264", "-preset", INTERMEDIATE_CLIP_PRESET, "-crf", str(INTERMEDIATE_CLIP_CRF),
            "-an",
            "-r", str(VIDEO_FPS),
            "-pix_fmt", "yuv420p",
            output_path
        ]
    else:
        cmd = [
            ffmpeg, "-y",
            "-ss", "0",
            "-i", video_clip_path,
            "-t", str(max(duration, 1.0)),
            "-vf", text_filter,
            "-c:v", "libx264", "-preset", INTERMEDIATE_CLIP_PRESET, "-crf", str(INTERMEDIATE_CLIP_CRF),
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
                        w: int, h: int, avatar_path: str = "",
                        lower_third_text: str = "") -> bool:
    """Convert a PIL image into a short video clip using FFmpeg."""
    # Added slow zoom (Ken Burns) effect for a premium cinematic feel
    base_filter = (
        f"scale=8000:-1,zoompan=z='min(zoom+0.001,1.1)':d={int(duration*VIDEO_FPS)}:s={w}x{h}:fps={VIDEO_FPS},setsar=1"
    )
    fade_st = max(duration - FADE_DURATION, 0.05)
    fade_filter = f"fade=t=in:st=0:d={FADE_DURATION},fade=t=out:st={fade_st}:d={FADE_DURATION}"
    font_arg = ""
    if FONT_PATH and os.path.exists(FONT_PATH):
        font_path_clean = FONT_PATH.replace("\\", "/")
        font_arg = f":fontfile='{font_path_clean}'"
    lower_third = ""
    if lower_third_text:
        safe_lower = lower_third_text.replace("\\", "/").replace("'", "").replace("%", "%%")
        safe_lower = safe_lower.replace(":", "\\:").replace(",", "\\,")
        lower_third = (
            f",drawbox=x=0:y=h-100:w=w:h=100:color=black@0.45:t=fill,"
            f"drawbox=x=20:y=h-90:w=8:h=60:color=yellow@0.92:t=fill,"
            f"drawtext=text='{safe_lower}'{font_arg}"
            f":fontsize=32:fontcolor=white:x=40:y=h-70"
        )
    has_avatar = bool(avatar_path and os.path.exists(avatar_path))
    if has_avatar:
        avatar_w = int(w * 0.34) if h <= w else int(w * 0.42)
        avatar_x = f"main_w-overlay_w-{int(w * 0.025)}"
        avatar_y = str(int(h * 0.10)) if h > w else f"(main_h-overlay_h)/2"
        full_filter = (
            f"[0:v]{base_filter},{fade_filter}{lower_third}[base];"
            f"{_talking_avatar_filter('[1:v]', '[avatar]', avatar_w)};"
            f"[base][avatar]overlay=x={avatar_x}:y={avatar_y}:format=auto"
        )
        cmd = [
            FFMPEG_PATH, "-y",
            "-loop", "1",
            "-i", image_path,
            "-loop", "1",
            "-t", str(max(duration, 1.0)),
            "-i", avatar_path,
            "-t", str(max(duration, 1.0)),
            "-filter_complex", full_filter,
            "-c:v", "libx264", "-preset", INTERMEDIATE_CLIP_PRESET, "-crf", str(INTERMEDIATE_CLIP_CRF),
            "-pix_fmt", "yuv420p",
            "-an",
            output_path
        ]
    else:
        cmd = [
            FFMPEG_PATH, "-y",
            "-loop", "1",
            "-i", image_path,
            "-t", str(max(duration, 1.0)),
            "-vf", f"{base_filter},{fade_filter}{lower_third}",
            "-c:v", "libx264", "-preset", INTERMEDIATE_CLIP_PRESET, "-crf", str(INTERMEDIATE_CLIP_CRF),
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

# ── Diverse themed color palettes so each video looks visually unique ──────
# Each tuple is (bg_color, accent_color) — used for slide backgrounds.
# Covers: deep red, electric blue, forest green, rich gold, violet,
#         teal, burnt orange, crimson, dark cyan, indigo, emerald, dark rose.
THEMED_PALETTES = [
    {"bg": (45,  5,  5), "name": "deep_red"},        # deep red
    {"bg": (5,  20, 60), "name": "electric_blue"},    # electric blue
    {"bg": (5,  40, 20), "name": "forest_green"},     # forest green
    {"bg": (50, 35,  0), "name": "rich_gold"},        # rich gold/amber
    {"bg": (35,  5, 55), "name": "violet"},           # violet/purple
    {"bg": (0,  45, 45), "name": "teal"},             # teal
    {"bg": (55, 25,  0), "name": "burnt_orange"},     # burnt orange
    {"bg": (50,  5, 20), "name": "crimson"},          # crimson
    {"bg": (0,  40, 50), "name": "dark_cyan"},        # dark cyan
    {"bg": (20,  5, 60), "name": "indigo"},           # indigo
    {"bg": (5,  50, 30), "name": "emerald"},          # emerald
    {"bg": (50, 10, 35), "name": "dark_rose"},        # dark rose/magenta
]


def _draw_tech_background(width: int, height: int, seed: int, accent: tuple) -> Image.Image:
    """Create a detailed tech-style fallback background instead of a plain gradient."""
    rng = random.Random(seed)
    palettes = [
        ((4, 10, 24), (16, 44, 70)),
        ((22, 2, 18), (70, 10, 48)),
        ((3, 24, 18), (12, 68, 48)),
        ((28, 18, 2), (78, 48, 8)),
        ((10, 6, 32), (42, 18, 86)),
    ]
    c0, c1 = palettes[seed % len(palettes)]
    img = Image.new("RGB", (width, height), c0)
    draw = ImageDraw.Draw(img, "RGBA")

    for y in range(height):
        ratio = y / max(1, height - 1)
        r = int(c0[0] * (1 - ratio) + c1[0] * ratio)
        g = int(c0[1] * (1 - ratio) + c1[1] * ratio)
        b = int(c0[2] * (1 - ratio) + c1[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    grid_color = (*accent, 34)
    for x in range(-80, width + 80, 80):
        draw.line([(x, 0), (x + 260, height)], fill=grid_color, width=1)
    for y in range(40, height, 70):
        draw.line([(0, y), (width, y + rng.randint(-40, 40))], fill=grid_color, width=1)

    # Large foreground tech object: chip/server block, positioned away from common text zones.
    object_side = "right" if seed % 2 == 0 else "left"
    cx = 950 if object_side == "right" else 300
    cy = 310 + rng.randint(-40, 60)
    chip_w, chip_h = 360, 250
    chip_box = [cx - chip_w // 2, cy - chip_h // 2, cx + chip_w // 2, cy + chip_h // 2]
    draw.rounded_rectangle(chip_box, radius=34, fill=(8, 18, 28, 220), outline=(*accent, 210), width=5)
    draw.rounded_rectangle(
        [chip_box[0] + 22, chip_box[1] + 22, chip_box[2] - 22, chip_box[3] - 22],
        radius=22,
        fill=(18, 36, 50, 230),
        outline=(255, 255, 255, 55),
        width=2,
    )
    for i in range(7):
        px = chip_box[0] + 44 + i * 44
        draw.line([(px, chip_box[1] - 45), (px, chip_box[1])], fill=(*accent, 170), width=4)
        draw.line([(px, chip_box[3]), (px, chip_box[3] + 45)], fill=(*accent, 170), width=4)
    for i in range(5):
        py = chip_box[1] + 42 + i * 40
        draw.line([(chip_box[0] - 55, py), (chip_box[0], py)], fill=(*accent, 160), width=4)
        draw.line([(chip_box[2], py), (chip_box[2] + 55, py)], fill=(*accent, 160), width=4)

    # Floating UI/data cards add visible context in empty areas.
    for i in range(6):
        card_w = rng.randint(130, 230)
        card_h = rng.randint(48, 86)
        x = rng.randint(40, width - card_w - 40)
        y = rng.randint(40, height - card_h - 80)
        if abs(x + card_w / 2 - cx) < 260 and abs(y + card_h / 2 - cy) < 190:
            continue
        draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=14, fill=(0, 0, 0, 82), outline=(*accent, 72), width=2)
        for j in range(3):
            line_w = rng.randint(45, card_w - 28)
            draw.rounded_rectangle([x + 14, y + 14 + j * 18, x + 14 + line_w, y + 20 + j * 18], radius=3, fill=(*accent, 135))

    for _ in range(36):
        x = rng.randint(20, width - 20)
        y = rng.randint(20, height - 20)
        r = rng.randint(2, 5)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(*accent, rng.randint(70, 180)))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for radius, alpha in [(360, 32), (250, 42), (140, 60)]:
        glow_draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(*accent, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")
    return img


def _paste_presenter_avatar(img: Image.Image, avatar_path: str, w: int, h: int) -> Image.Image:
    """Paste the synthetic presenter as a face-cam overlay."""
    if not avatar_path or not os.path.exists(avatar_path):
        return img
    try:
        avatar = Image.open(avatar_path).convert("RGBA")
        target_w = int(w * (0.28 if h > w else 0.23))
        target_h = int(target_w * avatar.height / max(1, avatar.width))
        avatar = avatar.resize((target_w, target_h), Image.LANCZOS)
        margin = int(w * 0.035)
        x = w - target_w - margin
        y = int(h * 0.13) if h > w else h - target_h - int(h * 0.12)
        base = img.convert("RGBA")
        base.alpha_composite(avatar, (x, y))
        return base.convert("RGB")
    except Exception as e:
        log.warning(f"Presenter avatar paste failed: {e}")
        return img


def create_presenter_avatar(job_id: str, topic: str = "", is_shorts: bool = False) -> str:
    """Create a synthetic AI presenter face-cam image for video overlays."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    avatar_path = os.path.join(OUTPUT_DIR, f"{job_id}_presenter.png")
    if os.path.exists(avatar_path):
        return avatar_path

    seed = int(hashlib.sha256(f"{job_id}:{topic}:presenter".encode("utf-8")).hexdigest()[:8], 16)
    portrait = None
    try:
        import requests
        prompt = (
            "synthetic AI news presenter, professional human face, shoulders visible, "
            "looking at camera, studio lighting, dark tech newsroom background, "
            "realistic but not a real person, high detail"
        )
        url = (
            f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}"
            f"?width=640&height=900&seed={seed}&nologo=true"
        )
        resp = requests.get(url, timeout=25)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            from io import BytesIO
            portrait = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        log.warning(f"Presenter image generation failed, using local avatar: {e}")

    card_w, card_h = (330, 470) if not is_shorts else (360, 520)
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card, "RGBA")
    accent = [(0, 220, 160), (255, 80, 60), (0, 190, 255), (255, 210, 0)][seed % 4]
    draw.rounded_rectangle([0, 0, card_w - 1, card_h - 1], radius=34, fill=(4, 9, 14, 215), outline=(*accent, 230), width=5)

    inner = [14, 14, card_w - 14, card_h - 70]
    mask = Image.new("L", (inner[2] - inner[0], inner[3] - inner[1]), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, mask.width - 1, mask.height - 1], radius=26, fill=255)
    if portrait:
        portrait = portrait.resize((mask.width, mask.height), Image.LANCZOS).convert("RGBA")
        card.paste(portrait, (inner[0], inner[1]), mask)
    else:
        # Local fallback: stylized host face, not a real identity.
        face = Image.new("RGBA", (mask.width, mask.height), (14, 24, 36, 255))
        fd = ImageDraw.Draw(face, "RGBA")
        cx, cy = mask.width // 2, int(mask.height * 0.42)
        fd.ellipse([cx - 92, cy - 118, cx + 92, cy + 118], fill=(214, 174, 140, 255), outline=(*accent, 150), width=4)
        fd.arc([cx - 88, cy - 126, cx + 88, cy + 58], 200, 340, fill=(28, 22, 20, 255), width=28)
        fd.ellipse([cx - 50, cy - 22, cx - 26, cy + 2], fill=(20, 28, 34, 255))
        fd.ellipse([cx + 26, cy - 22, cx + 50, cy + 2], fill=(20, 28, 34, 255))
        fd.rounded_rectangle([cx - 34, cy + 62, cx + 34, cy + 78], radius=8, fill=(92, 24, 32, 255))
        fd.polygon([(cx - 130, mask.height), (cx + 130, mask.height), (cx + 76, cy + 116), (cx - 76, cy + 116)], fill=(10, 18, 28, 255))
        fd.line([(cx - 56, cy + 126), (cx, mask.height - 18), (cx + 56, cy + 126)], fill=(*accent, 220), width=5)
        card.paste(face, (inner[0], inner[1]), mask)

    try:
        font = ImageFont.truetype(FONT_PATH, 30)
    except Exception:
        font = ImageFont.load_default()
    draw.rounded_rectangle([24, card_h - 54, card_w - 24, card_h - 14], radius=20, fill=(*accent, 220))
    draw.text((card_w // 2, card_h - 48), "AI HOST", font=font, fill=(255, 255, 255), anchor="ma")
    card.save(avatar_path)
    return avatar_path


def create_video(content: dict, audio_path: str, job_id: str,
                 is_shorts: bool = False,
                 audio_chunk_timing: list[dict] | None = None) -> str:
    """
    Build MP4 video using:
    - Director Agent → scene plan with Pexels keywords
    - Pexels stock video clips per scene
    - FFmpeg drawtext overlays for on-screen text
    - Audio voiceover + optional BGM
    Fast, memory-safe, reliable.
    """
    from mutagen.mp3 import MP3

    # Reset Pexels used-ID tracker so every scene in this job gets a unique clip
    try:
        from modules.pexels_manager import reset_used_ids
        reset_used_ids()
    except Exception:
        pass

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
        scenes = [
            {
                "text": s,
                "keyword": "data center" if i == 0 else "coding screen",
                "alt_keyword": "server room" if i == 0 else "office desk",
                "prompt": f"Cinematic stock footage background matching: {s[:120]}",
            }
            for i, s in enumerate(slides)
        ]

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

    avatar_path = create_presenter_avatar(
        job_id,
        topic=content.get("chosen_topic", content.get("seo_title", "AI host")),
        is_shorts=is_shorts,
    )

    scene_durations = _estimate_scene_durations(scenes, total_duration, audio_chunk_timing)

    # 4. Build each scene as a video clip
    clip_files = []
    clip_durations = []
    temp_files = []

    for i, scene in enumerate(scenes):
        scene_text = scene.get("text", "")
        keyword = scene.get("keyword", "data center")
        is_title_slide = (i == 0)
        
        clip_duration = scene_durations[i]

        clip_out = os.path.join(OUTPUT_DIR, f"{job_id}_clip_{i:04d}.mp4")

        log.info(f"Scene {i+1}/{n_scenes}: '{keyword}' → {clip_duration:.1f}s")

        # Try Pexels first (primary + alt keyword)
        alt_keyword = scene.get("alt_keyword", "")
        pexels_path = get_pexels_clip_for_scene(keyword, job_id, i, is_shorts, alt_keyword=alt_keyword)

        if pexels_path and os.path.exists(pexels_path):
            # Overlay text on Pexels clip
            ok = create_text_overlay_clip(
                pexels_path,
                scene_text,
                clip_duration,
                clip_out,
                w,
                h,
                is_title=is_title_slide,
                avatar_path=avatar_path,
                lower_third_text=f"{keyword} • AI NEWS DAILY",
            )
            if ok:
                clip_files.append(clip_out)
                clip_durations.append(clip_duration)
                temp_files.append(clip_out)
                continue
        log.warning(f"Text overlay failed for scene {i+1}, falling back to image slide")

        # Fallback: PIL image slide → video clip (Unique AI Background)
        try:
            from modules.asset_generator import generate_ai_image
            # Pollinations generates highly detailed scene image
            scene_bg = generate_ai_image(scene.get("prompt", keyword), job_id, i+100, width=w, height=h)
        except Exception:
            scene_bg = ""

        # Pick a palette: hash the job_id to get a consistent theme per video,
        # then rotate hue slightly per-scene so consecutive slides feel varied.
        palette_index = (hash(job_id) + i) % len(THEMED_PALETTES)
        base_bg = THEMED_PALETTES[palette_index]["bg"]
        # Slightly brighten every other scene for contrast
        scene_bg_color = tuple(min(255, c + (10 if i % 2 == 0 else 0)) for c in base_bg)

        img_path = render_slide_image(
            scene_text,
            bg_color=scene_bg_color,
            w=w, h=h,
            is_title=is_title_slide,
            bg_image_path=scene_bg if scene_bg else bg_path,
            avatar_path=avatar_path,
            paste_avatar=False,
        )
        temp_files.append(img_path)

        clip_ok = image_to_video_clip(
            img_path,
            clip_duration,
            clip_out,
            w,
            h,
            avatar_path=avatar_path,
            lower_third_text=f"{keyword} • AI NEWS DAILY",
        )
        if clip_ok:
            clip_files.append(clip_out)
            clip_durations.append(clip_duration)
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
    if len(clip_files) == 1:
        concat_cmd = [
            FFMPEG_PATH, "-y",
            "-i", clip_files[0],
            "-c:v", "libx264", "-preset", FINAL_VIDEO_PRESET, "-crf", str(FINAL_VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            raw_video
        ]
    else:
        inputs = []
        filter_parts = []
        for idx, cp in enumerate(clip_files):
            inputs.extend(["-i", cp])
            filter_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS[v{idx}];")

        current_label = "[v0]"
        for idx in range(1, len(clip_files)):
            offset = max(sum(clip_durations[:idx]) - idx * FADE_DURATION, 0.05)
            out_label = f"[xf{idx-1}]"
            filter_parts.append(
                f"{current_label}[v{idx}]xfade=transition=fade:duration={FADE_DURATION}:offset={offset}{out_label};"
            )
            current_label = out_label

        filter_complex = "".join(filter_parts)
        concat_cmd = [FFMPEG_PATH, "-y"] + inputs + [
            "-filter_complex", filter_complex,
            "-map", current_label,
            "-c:v", "libx264", "-preset", FINAL_VIDEO_PRESET, "-crf", str(FINAL_VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
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
            "-movflags", "+faststart",
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
            "-movflags", "+faststart",
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


def _estimate_scene_durations(scenes: list, total_duration: float, audio_chunk_timing: list[dict] | None) -> list[float]:
    """Estimate per-scene duration using audio timing and scene text relevance."""
    if not scenes:
        return []

    scene_word_sets = [set(re.findall(r"\w+", str(scene.get("text", "")).lower())) for scene in scenes]
    base_weights = [max(1, len(words)) for words in scene_word_sets]
    scene_weights = [w * 0.08 for w in base_weights]

    for chunk in audio_chunk_timing or []:
        chunk_words = set(re.findall(r"\w+", str(chunk.get("text", "")).lower()))
        duration = float(chunk.get("duration", 0) or 0)
        if duration <= 0 or not chunk_words:
            continue

        overlaps = [len(ws & chunk_words) for ws in scene_word_sets]
        total_overlap = sum(overlaps)
        if total_overlap == 0:
            continue

        for idx, overlap in enumerate(overlaps):
            scene_weights[idx] += duration * (overlap / total_overlap)

    total_weight = sum(scene_weights) or len(scene_weights)
    durations = [max((weight / total_weight) * total_duration, 2.0) for weight in scene_weights]
    scale = total_duration / sum(durations)
    return [d * scale for d in durations]


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
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")
    variant_seed = int(hashlib.sha256(
        f"{job_id}:{content.get('chosen_topic', '')}:{content.get('thumbnail_text', '')}".encode("utf-8")
    ).hexdigest()[:8], 16)
    layout_variant = variant_seed % 5
    accent_colors = [
        (0, 220, 140),
        (255, 80, 60),
        (255, 210, 0),
        (0, 190, 255),
        (180, 90, 255),
    ]
    accent = accent_colors[(variant_seed // 5) % len(accent_colors)]

    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).resize((1280, 720)).convert("RGB")
    else:
        img = _draw_tech_background(1280, 720, variant_seed, accent)

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

    # Main text: rotate layout every job so thumbnails never feel templated.
    raw_text = content.get("thumbnail_text") or content.get("seo_title") or "AI REVOLUTION"
    text = clean_markdown(raw_text).upper()
    lines = textwrap.wrap(text, width=13 if layout_variant in (1, 3) else 15)[:3]
    if layout_variant == 0:
        x_text, start_y, align = 70, 105, "left"
    elif layout_variant == 1:
        x_text, start_y, align = 1220, 110, "right"
    elif layout_variant == 2:
        x_text, start_y, align = 640, 90, "center"
    elif layout_variant == 3:
        x_text, start_y, align = 80, 320, "left"
    else:
        x_text, start_y, align = 640, 395, "center"

    if layout_variant in (3, 4):
        band = Image.new("RGBA", (1280, 210), (0, 0, 0, 150))
        img = img.convert("RGBA")
        img.paste(band, (0, start_y - 35), band)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)

    for line in lines:
        color = accent if ("AI" in line or len(lines) == 1) else (255, 255, 255)
        bbox = draw.textbbox((0, 0), line, font=font_main)
        line_w = bbox[2] - bbox[0]
        if align == "right":
            draw_x = x_text - line_w
        elif align == "center":
            draw_x = x_text - line_w // 2
        else:
            draw_x = x_text
        # Deep shadow layer
        draw.text((draw_x + 8, start_y + 8), line, font=font_main, fill=(0, 0, 0, 180))
        # Stroke + Fill layer
        try:
            draw.text((draw_x, start_y), line, font=font_main, fill=color, stroke_width=6, stroke_fill=(0, 0, 0))
        except TypeError:
            # Fallback for old pillow
            for off_x in [-3,0,3]:
                for off_y in [-3,0,3]:
                    draw.text((draw_x + off_x, start_y + off_y), line, font=font_main, fill=(0,0,0))
            draw.text((draw_x, start_y), line, font=font_main, fill=color)
        start_y += 115

    # Hook line
    hook = clean_markdown(content.get("hook_line", ""))[:80]
    if hook:
        wrapped_hook = textwrap.wrap(hook, width=38 if align != "center" else 48)[:2]
        y_hook = start_y + 18
        for hl in wrapped_hook:
            bbox = draw.textbbox((0, 0), hl, font=font_sub)
            hook_w = bbox[2] - bbox[0]
            if align == "right":
                hook_x = x_text - hook_w
            elif align == "center":
                hook_x = x_text - hook_w // 2
            else:
                hook_x = x_text
            # Black shadow + stroke for hook
            draw.text((hook_x + 2, y_hook + 3), hl, font=font_sub, fill=(0, 0, 0))
            try:
                draw.text((hook_x, y_hook), hl, font=font_sub, fill=(220, 255, 255), stroke_width=3, stroke_fill=(0,0,0))
            except TypeError:
                draw.text((hook_x, y_hook), hl, font=font_sub, fill=(220, 255, 255))
            y_hook += 55

    # Brand border
    draw.rectangle([8, 8, 1272, 712], outline=accent, width=7)

    # Channel branding pill
    try:
        pill_w, pill_h = 310, 55
        pill_img = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
        pill_draw = ImageDraw.Draw(pill_img)
        pill_draw.rounded_rectangle([0, 0, pill_w - 1, pill_h - 1], radius=27, fill=(255, 50, 50, 220))
        img = img.convert("RGBA")
        pill_pos = (950, 655) if layout_variant in (0, 2, 3) else (20, 655)
        img.paste(pill_img, pill_pos, pill_img)
        img = img.convert("RGB")
        draw = ImageDraw.Draw(img)
        draw.text((pill_pos[0] + 10, pill_pos[1] + 13), "AI NEWS DAILY", font=font_brand, fill=(255, 255, 255))
    except Exception:
        pass  # Older Pillow may not support rounded_rectangle

    img.save(thumb_path, "JPEG", quality=95)
    log.info(f"Thumbnail saved: {thumb_path}")
    return thumb_path
