"""
modules/asset_generator.py
Handles AI image generation for video backgrounds.
Uses Pollinations.ai (free, no API key needed).
Fal.ai has been removed.
"""

import os
import requests
import logging
import hashlib
import random
from config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)


def generate_ai_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    """
    Generate an image using Pollinations.ai (free, no key needed).
    Falls back to a solid gradient PIL image if Pollinations fails.
    """
    try:
        clean_prompt = "".join(c if c.isalnum() or c in " ,.-" else "" for c in prompt)[:500]
        seed_base = int(hashlib.sha256(f"{job_id}:{index}:{clean_prompt}".encode("utf-8")).hexdigest()[:8], 16)
        style_variants = [
            "close-up human hand using futuristic holographic interface",
            "wide cinematic newsroom with glowing data screens",
            "dramatic low-angle robot and server racks",
            "macro shot of silicon chip with electric traces",
            "split-depth office desk with laptop dashboard",
            "cinematic city skyline with data streams",
            "over-the-shoulder developer workstation",
            "high contrast laboratory research scene",
        ]
        color_variants = [
            "cyan and red contrast",
            "emerald and gold contrast",
            "blue and orange contrast",
            "magenta and teal contrast",
            "white neon on dark graphite",
            "green matrix highlights with warm rim light",
        ]
        style = style_variants[seed_base % len(style_variants)]
        color = color_variants[(seed_base // 7) % len(color_variants)]
        full_prompt = (
            f"{clean_prompt}, {style}, {color}, epic YouTube thumbnail background, "
            f"highly detailed complex 3D render, sharp foreground subject, visible depth, "
            f"cinematic dramatic lighting, 8k resolution, premium tech aesthetic"
        )
        save_path = os.path.join(OUTPUT_DIR, f"{job_id}_img_{index}.jpg")

        # Try Pollinations.ai (free, no key needed)
        log.info(f"Generating image via Pollinations.ai for: {clean_prompt[:60]}")
        for seed_offset in range(2):
            try:
                seed = seed_base + seed_offset * 9973
                p_text = full_prompt if seed_offset == 0 else (
                    f"{clean_prompt}, {random_style(seed)}, premium tech editorial background, "
                    "clear foreground subject, cinematic lighting"
                )
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
            picsum_url = f"https://picsum.photos/seed/{seed_base}/{width}/{height}"
            resp = requests.get(picsum_url, timeout=20)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return save_path
        except:
            pass

        # Fallback: varied gradient PIL image (different color per index)
        log.warning("All image providers failed. Generating detailed fallback image.")
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
        c0, c1 = GRAD_PALETTES[seed_base % len(GRAD_PALETTES)]
        rng = random.Random(seed_base)
        img = Image.new("RGB", (width, height), c0)
        draw = ImageDraw.Draw(img, "RGBA")
        for y in range(height):
            ratio = y / height
            r = int(c0[0] * (1 - ratio) + c1[0] * ratio)
            g = int(c0[1] * (1 - ratio) + c1[1] * ratio)
            b = int(c0[2] * (1 - ratio) + c1[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        accent = [
            (0, 220, 255),
            (0, 235, 150),
            (255, 210, 0),
            (255, 80, 80),
            (170, 90, 255),
        ][seed_base % 5]
        for x in range(0, width, max(60, width // 18)):
            draw.line([(x, 0), (x + width // 5, height)], fill=(*accent, 42), width=max(1, width // 640))
        for y in range(0, height, max(50, height // 12)):
            draw.line([(0, y), (width, y + rng.randint(-height // 12, height // 12))], fill=(*accent, 34), width=max(1, height // 360))

        cx = int(width * (0.72 if seed_base % 2 == 0 else 0.28))
        cy = int(height * 0.46)
        chip_w = int(width * 0.28)
        chip_h = int(height * 0.28)
        box = [cx - chip_w // 2, cy - chip_h // 2, cx + chip_w // 2, cy + chip_h // 2]
        draw.rounded_rectangle(box, radius=max(14, width // 42), fill=(4, 12, 20, 215), outline=(*accent, 210), width=max(3, width // 260))
        inner = [box[0] + chip_w // 11, box[1] + chip_h // 9, box[2] - chip_w // 11, box[3] - chip_h // 9]
        draw.rounded_rectangle(inner, radius=max(10, width // 70), fill=(18, 32, 48, 220), outline=(255, 255, 255, 50), width=2)
        for i in range(8):
            px = box[0] + int((i + 1) * chip_w / 9)
            draw.line([(px, box[1] - chip_h // 5), (px, box[1])], fill=(*accent, 160), width=max(2, width // 360))
            draw.line([(px, box[3]), (px, box[3] + chip_h // 5)], fill=(*accent, 160), width=max(2, width // 360))
        for i in range(5):
            py = box[1] + int((i + 1) * chip_h / 6)
            draw.line([(box[0] - chip_w // 7, py), (box[0], py)], fill=(*accent, 150), width=max(2, width // 360))
            draw.line([(box[2], py), (box[2] + chip_w // 7, py)], fill=(*accent, 150), width=max(2, width // 360))

        for _ in range(10):
            card_w = rng.randint(width // 11, width // 5)
            card_h = rng.randint(height // 18, height // 9)
            x = rng.randint(20, max(21, width - card_w - 20))
            y = rng.randint(20, max(21, height - card_h - 20))
            draw.rounded_rectangle([x, y, x + card_w, y + card_h], radius=12, fill=(0, 0, 0, 70), outline=(*accent, 65), width=2)
            for j in range(3):
                draw.rounded_rectangle(
                    [x + 12, y + 12 + j * 16, x + rng.randint(card_w // 2, card_w - 16), y + 18 + j * 16],
                    radius=3,
                    fill=(*accent, 115),
                )

        img.save(save_path, "JPEG", quality=85)
        return save_path

    except Exception as e:
        log.error(f"Image generation failed for '{prompt}': {e}")
        return ""


def random_style(seed: int) -> str:
    """Return a deterministic visual style variant for retry prompts."""
    styles = [
        "photorealistic tech conference stage",
        "cinematic startup office war room",
        "dramatic data center aisle",
        "futuristic robotics lab",
        "macro motherboard and processor scene",
        "news documentary style AI control room",
    ]
    return styles[seed % len(styles)]


def generate_ai_video(prompt: str, job_id: str, index: int, is_shorts: bool = False) -> str:
    """Fal.ai video generation removed. Returns empty string."""
    log.info("AI video b-roll disabled (Fal.ai removed). Using Pexels stock video.")
    return ""
