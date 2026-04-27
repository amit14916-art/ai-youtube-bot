"""
modules/asset_generator.py
Handles AI image generation for video backgrounds.
Uses Pollinations.ai (free, no API key needed).
Fal.ai has been removed.
"""

import os
import requests
import logging
from config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)


def generate_ai_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    """
    Generate an image using Pollinations.ai (free, no key needed).
    Falls back to a solid gradient PIL image if Pollinations fails.
    """
    try:
        clean_prompt = "".join(c if c.isalnum() or c in " ,.-" else "" for c in prompt)[:500]
        full_prompt = (
            f"{clean_prompt}, epic YouTube thumbnail background, highly detailed complex 3D render, "
            f"glowing neon nodes, abstract tech diagrams, UI elements, Unreal Engine 5 render, "
            f"cinematic dramatic lighting, 8k resolution, premium tech aesthetic, trending on ArtStation"
        )
        save_path = os.path.join(OUTPUT_DIR, f"{job_id}_img_{index}.jpg")

        # Try Pollinations.ai (free, no key needed)
        log.info(f"Generating image via Pollinations.ai for: {clean_prompt[:60]}")
        for seed_offset in range(2):
            try:
                seed = index + seed_offset * 100
                p_text = full_prompt if seed_offset == 0 else "AI technology futuristic background, highly detailed complex 3D render, Unreal Engine 5"
                poll_url = (
                    f"https://image.pollinations.ai/prompt/{requests.utils.quote(p_text)}"
                    f"?width={width}&height={height}&seed={seed}&nologo=true"
                )
                resp = requests.get(poll_url, timeout=30)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    return save_path
            except Exception as poll_err:
                log.warning(f"Pollinations.ai attempt {seed_offset+1} failed: {poll_err}")

        # Final Fallback: Unsplash/Picsum random tech image
        try:
            log.info("Try Picsum tech fallback...")
            picsum_url = f"https://picsum.photos/seed/{index}/{width}/{height}"
            resp = requests.get(picsum_url, timeout=20)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return save_path
        except:
            pass

        # Fallback: varied gradient PIL image (different color per index)
        log.warning("All image providers failed. Generating gradient fallback image.")
        from PIL import Image, ImageDraw
        # 8 distinct themed gradient palettes
        GRAD_PALETTES = [
            ((10, 15, 30),  (20, 40, 80)),   # navy blue
            ((30, 5,  5),   (80, 20, 20)),   # deep red
            ((5,  30, 10),  (20, 80, 40)),   # forest green
            ((30, 20, 0),   (80, 55, 0)),    # amber gold
            ((20, 5,  35),  (55, 10, 90)),   # violet
            ((0,  30, 30),  (0,  80, 80)),   # teal
            ((35, 15, 0),   (90, 45, 0)),    # burnt orange
            ((25, 0,  15),  (70, 0,  40)),   # dark rose
        ]
        c0, c1 = GRAD_PALETTES[index % len(GRAD_PALETTES)]
        img = Image.new("RGB", (width, height), c0)
        draw = ImageDraw.Draw(img)
        for y in range(height):
            ratio = y / height
            r = int(c0[0] * (1 - ratio) + c1[0] * ratio)
            g = int(c0[1] * (1 - ratio) + c1[1] * ratio)
            b = int(c0[2] * (1 - ratio) + c1[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        img.save(save_path, "JPEG", quality=85)
        return save_path

    except Exception as e:
        log.error(f"Image generation failed for '{prompt}': {e}")
        return ""


def generate_ai_video(prompt: str, job_id: str, index: int, is_shorts: bool = False) -> str:
    """Fal.ai video generation removed. Returns empty string."""
    log.info("AI video b-roll disabled (Fal.ai removed). Using Pexels stock video.")
    return ""
