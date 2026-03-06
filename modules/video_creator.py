"""
modules/video_creator.py
Builds high-quality faceless YouTube videos & Shorts using MoviePy (fast render):
  • Pexels HD stock video backgrounds per scene
  • Dynamic text overlays with semi-transparent backdrops
  • Background music mixing
  • Optimized for both 16:9 Landscape and 9:16 Shorts
  • Renders in 5-8 minutes (no Chrome/Remotion needed)
"""

import logging
import math
import os
import textwrap
import random

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
    """Break podcast script into small, punchy chunks for dynamic captions."""
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
            chunk_size = 6
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i + chunk_size])
                slides.append(f"{current_host} {chunk}")
    slides.append("LIKE  •  SUBSCRIBE  •  AI NEWS DAILY")
    return slides


# -----------------------------------------------------------------
#  SLIDE IMAGE OVERLAY RENDERER
# -----------------------------------------------------------------

def render_slide_overlay(text: str, w: int, h: int,
                         is_title: bool = False, is_shorts: bool = False) -> Image.Image:
    """Render a premium caption overlay (bold modern style, no boxes)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    host_color = (255, 255, 255)
    host_label = ""
    if text.startswith("Host A:"):
        host_label = "HOST A"
        text = text.replace("Host A:", "").strip()
        host_color = (0, 255, 100)
    elif text.startswith("Host B:"):
        host_label = "HOST B"
        text = text.replace("Host B:", "").strip()
        host_color = (255, 100, 0)

    scale_factor = 1.0 if is_shorts else 1.2
    caption_size = int(85 * scale_factor)
    if is_title:
        caption_size = int(120 * scale_factor)

    try:
        font_main = ImageFont.truetype(FONT_PATH, caption_size)
        font_host = ImageFont.truetype(FONT_PATH, int(40 * scale_factor))
    except Exception:
        font_main = ImageFont.load_default()
        font_host = font_main

    words = text.split()
    lines = []
    n = 2 if is_shorts else 3
    for i in range(0, len(words), n):
        lines.append(" ".join(words[i:i + n]))

    line_h = caption_size + 20
    total_h = line_h * len(lines)

    if is_shorts:
        y = h - total_h - 250
    else:
        y = h - total_h - 200

    for line in lines:
        line_words = line.upper().split()
        full_line_text = " ".join(line_words)
        bbox_full = draw.textbbox((0, 0), full_line_text, font=font_main)
        lw = bbox_full[2] - bbox_full[0]
        padding = 40

        bx1, by1 = (w - lw) // 2 - padding, y - 10
        bx2, by2 = (w + lw) // 2 + padding, y + line_h - 10
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=20, fill=(0, 0, 0, 160))

        cur_x = (w - lw) // 2
        for word in line_words:
            highlights = ["AI", "MCP", "DATA", "ROBOT", "GPT", "OPENAI",
                          "ANTHROPIC", "TECH", "FUTURE", "IMPACT", "WORLD",
                          "AUTO", "AGENT", "MONEY", "SCALE"]
            is_highlight = is_title or word in highlights or word.endswith("S")
            color = (0, 255, 127) if is_highlight else (255, 255, 255)
            if is_title:
                color = (255, 215, 0)

            draw.text((cur_x + 3, y + 3), word, font=font_main, fill=(0, 0, 0, 200))
            draw.text((cur_x, y), word, font=font_main, fill=color)

            bbox_word = draw.textbbox((0, 0), word, font=font_main)
            word_w = bbox_word[2] - bbox_word[0]
            cur_x += word_w + 25

        y += line_h

    if host_label:
        label = f"🎙 {host_label}"
        lx, ly = (100, 100) if not is_shorts else (w // 2 - 150, 200)
        for _ in range(1, 4):
            draw.text((lx, ly), label, font=font_host, fill=(0, 0, 0, 80))
        draw.text((lx, ly), label, font=font_host, fill=host_color)

    if not is_shorts:
        brand = f"@{NICHE}"
        draw.text((w - 250, h - 80), brand, font=font_host, fill=(255, 255, 255, 80))

    return img


# -----------------------------------------------------------------
#  MAIN VIDEO BUILDER (MOVIEPY - FAST, NO CHROME)
# -----------------------------------------------------------------

def create_video(content: dict, audio_path: str, job_id: str, is_shorts: bool = False) -> str:
    """Build high-quality MP4 video using MoviePy — fast render, no Chrome needed."""
    from mutagen.mp3 import MP3

    log.info(f"=== Building {'Short' if is_shorts else 'Long'} Video (MoviePy) ===")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    suffix = "_shorts.mp4" if is_shorts else "_video.mp4"
    output_path = os.path.join(OUTPUT_DIR, f"{job_id}{suffix}")

    # 1. Audio duration
    try:
        audio_obj = MP3(audio_path)
        total_duration = audio_obj.info.length
    except Exception as e:
        log.error(f"Could not read audio duration: {e}")
        total_duration = 60.0

    log.info(f"Voiceover duration: {total_duration:.1f}s")

    fps = VIDEO_FPS
    total_frames = int(total_duration * fps)

    # 2. Director Agent: scene breakdown
    from modules.director_agent import generate_scene_data
    from config.settings import USE_AI_VIDEO_BROLL
    from modules.asset_generator import generate_ai_video

    raw_scenes = generate_scene_data(
        content["chosen_topic"], content["seo_title"], content["script"], is_shorts
    )
    log.info(f"Director Agent created {len(raw_scenes)} scenes.")

    bgm_path = os.path.join(ASSETS_DIR, "bgm.mp3")
    slide_data_list = []
    current_frame = 0

    for idx, scene in enumerate(raw_scenes):
        scene_word_count = max(len(scene["text"].split()), 1)
        total_word_count  = sum(max(len(s["text"].split()), 1) for s in raw_scenes)
        bg_duration_sec   = (scene_word_count / total_word_count) * total_duration
        bg_frames         = int(bg_duration_sec * fps)
        if idx == len(raw_scenes) - 1:
            bg_frames = total_frames - current_frame

        orientation = "portrait" if is_shorts else "landscape"
        log.info(f"Fetching footage for scene {idx}: {scene['keyword']}")
        bg_path  = get_stock_video(scene["keyword"], orientation=orientation,
                                   min_duration=int(bg_duration_sec))
        is_video = bool(bg_path)

        if not bg_path:
            prompt = scene["prompt"]
            if USE_AI_VIDEO_BROLL:
                vid = generate_ai_video(prompt, job_id, idx, is_shorts=is_shorts)
                if vid and os.path.exists(vid):
                    bg_path, is_video = vid, True
            if not bg_path:
                img_p = generate_ai_image(
                    prompt, job_id, idx,
                    width=(1080 if is_shorts else VIDEO_WIDTH),
                    height=(1920 if is_shorts else VIDEO_HEIGHT),
                )
                if img_p and os.path.exists(img_p):
                    bg_path, is_video = img_p, False

        slide_data_list.append({
            "bgPath": bg_path, "isVideo": is_video,
            "durationInFrames": bg_frames, "durationInSecs": bg_duration_sec,
            "startFrame": current_frame, "text": scene["text"],
        })
        current_frame += bg_frames

    # 3. MoviePy render
    success = _render_with_moviepy(
        slide_data_list, audio_path, output_path,
        is_shorts, bgm_path, VIDEO_WIDTH, VIDEO_HEIGHT, fps
    )
    return output_path if success else ""


def _render_with_moviepy(slide_data_list, audio_path, output_path,
                          is_shorts, bgm_path, w, h, fps):
    """Fast MoviePy renderer — no browser required."""
    try:
        from moviepy.editor import (
            VideoFileClip, ImageClip, AudioFileClip,
            CompositeVideoClip, CompositeAudioClip,
            concatenate_videoclips, concatenate_audioclips,
        )
    except ImportError:
        log.error("moviepy not installed. Run: pip install moviepy")
        return False

    scene_clips = []

    for idx, slide in enumerate(slide_data_list):
        bg_path   = slide.get("bgPath", "")
        is_video  = slide.get("isVideo", False)
        dur       = max(slide.get("durationInSecs", 5.0), 1.0)
        text      = slide.get("text", "")
        is_title  = (idx == 0)

        # Background
        try:
            if is_video and bg_path and os.path.exists(bg_path):
                raw = VideoFileClip(bg_path).without_audio()
                if raw.duration < dur:
                    loops = math.ceil(dur / raw.duration)
                    raw = concatenate_videoclips([raw] * loops)
                bg_clip = raw.subclip(0, dur).resize((w, h))
            elif bg_path and os.path.exists(bg_path):
                bg_clip = ImageClip(bg_path).set_duration(dur).resize((w, h))
            else:
                arr = np.zeros((h, w, 3), dtype=np.uint8)
                arr[:, :] = [10, 15, 30]
                bg_clip = ImageClip(arr).set_duration(dur)
        except Exception as e:
            log.warning(f"Scene {idx} bg error: {e}")
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            bg_clip = ImageClip(arr).set_duration(dur)

        bg_clip = bg_clip.set_fps(fps)

        # Text overlay
        try:
            pil_img   = render_slide_overlay(text, w, h, is_title=is_title, is_shorts=is_shorts)
            rgba_arr  = np.array(pil_img)
            rgb_arr   = rgba_arr[:, :, :3]
            mask_arr  = rgba_arr[:, :, 3]
            txt_clip  = ImageClip(rgb_arr).set_duration(dur)
            mask_clip = ImageClip(mask_arr, ismask=True).set_duration(dur)
            txt_clip  = txt_clip.set_mask(mask_clip)
            composite = CompositeVideoClip([bg_clip, txt_clip], size=(w, h))
        except Exception as e:
            log.warning(f"Scene {idx} overlay error: {e}")
            composite = bg_clip

        scene_clips.append(composite.set_duration(dur).set_fps(fps))
        log.info(f"Scene {idx+1}/{len(slide_data_list)} ready ({dur:.1f}s)")

    if not scene_clips:
        log.error("No scenes!")
        return False

    log.info("Concatenating scenes...")
    final = concatenate_videoclips(scene_clips, method="compose")

    # Voiceover
    audio_tracks = []
    try:
        vo = AudioFileClip(audio_path)
        if vo.duration > final.duration:
            vo = vo.subclip(0, final.duration)
        audio_tracks.append(vo)
    except Exception as e:
        log.warning(f"Voiceover error: {e}")

    # BGM
    if bgm_path and os.path.exists(bgm_path):
        try:
            bgm = AudioFileClip(bgm_path).volumex(BACKGROUND_MUSIC_VOLUME)
            if bgm.duration < final.duration:
                loops = math.ceil(final.duration / bgm.duration)
                bgm = concatenate_audioclips([bgm] * loops)
            audio_tracks.append(bgm.subclip(0, final.duration))
        except Exception as e:
            log.warning(f"BGM error: {e}")

    if audio_tracks:
        final = final.set_audio(CompositeAudioClip(audio_tracks))

    log.info(f"Exporting -> {output_path}")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    final.write_videofile(
        output_path, fps=fps,
        codec="libx264", audio_codec="aac",
        preset="ultrafast", threads=4, logger=None,
    )
    log.info(f"Video rendered: {output_path}")
    return True


# -----------------------------------------------------------------
#  THUMBNAIL GENERATOR
# -----------------------------------------------------------------

def create_thumbnail(content: dict, job_id: str, bg_path: str = "") -> str:
    """Generate a high-quality eye-catching thumbnail."""
    log.info("Creating eye-catching SEO thumbnail...")
    thumb_path = os.path.join(OUTPUT_DIR, f"{job_id}_thumbnail.jpg")

    if bg_path and os.path.exists(bg_path):
        img = Image.open(bg_path).resize((1280, 720))
    else:
        bg_img = os.path.join(OUTPUT_DIR, f"{job_id}_img_0.jpg")
        if os.path.exists(bg_img):
            img = Image.open(bg_img).resize((1280, 720))
        else:
            img = Image.new("RGB", (1280, 720), (10, 15, 30))

    overlay = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    o_draw = ImageDraw.Draw(overlay)
    for x in range(0, 800):
        alpha = int(220 * (1 - x / 800))
        o_draw.line([(x, 0), (x, 720)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    try:
        font_main = ImageFont.truetype(FONT_PATH, 110)
        font_sub  = ImageFont.truetype(FONT_PATH, 60)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub  = font_main

    text  = content.get("thumbnail_text", "AI REVOLUTION").upper()
    lines = textwrap.wrap(text, width=12)

    start_y = 150
    for line in lines:
        for off in range(2, 10, 2):
            draw.text((80 + off, start_y + off), line, font=font_main, fill=(0, 0, 0, 150))
        draw.text((80, start_y), line, font=font_main, fill=(255, 255, 255))
        if "AI" in line or "2025" in line or len(lines) == 1:
            draw.text((80, start_y), line, font=font_main, fill=(255, 215, 0))
        start_y += 130

    border_color = (0, 255, 127)
    draw.rectangle([10, 10, 1270, 710], outline=border_color, width=8)

    img.save(thumb_path, "JPEG", quality=98)
    return thumb_path
