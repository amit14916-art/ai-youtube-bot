"""
modules/asset_generator.py
Generates scene-matching background images via Pollinations.ai (free, no key needed).
Each image is built from the actual scene text so visuals match what is being spoken.
"""

import os
import requests
import logging
import hashlib
import random
from config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)


# Visual style templates — each maps a content keyword to a cinematic style
SCENE_STYLE_MAP = {
    "robot|humanoid|automati": "futuristic humanoid robot in industrial factory, dramatic lighting",
    "doctor|medical|hospital|health|surgery|scan": "modern hospital operating room, medical equipment, blue lighting",
    "stock|finance|invest|market|money|crypto|bitcoin": "stock market trading floor with glowing screens, financial data",
    "code|developer|programm|software|app|github": "programmer at dual monitor workstation, dark room, code on screen",
    "data|server|cloud|database|infrastructure": "massive data center corridor with blinking server racks, blue glow",
    "car|vehicle|driving|transport|highway": "self-driving car on highway at night, autonomous vehicle sensors",
    "space|satellite|rocket|nasa|orbit": "rocket launching into space, earth from orbit, dramatic sky",
    "camera|video|youtube|creator|content|thumbnail": "video creator studio with ring light and camera setup",
    "phone|mobile|app|social|instagram|tiktok": "smartphone with glowing apps, person scrolling, dark background",
    "security|hack|cyber|privacy|breach|password": "hacker in dark room with multiple monitors showing code",
    "education|student|learn|school|university": "modern university campus, student with laptop, bright study hall",
    "energy|solar|wind|green|climate|environment": "solar panel field at sunset, wind turbines, clean energy",
    "business|office|meeting|startup|entrepreneur": "modern glass office boardroom, business professionals meeting",
    "brain|neural|think|cogniti|conscious": "glowing human brain neural network visualization, dark background",
    "chip|processor|silicon|hardware|gpu|cpu": "extreme close-up silicon microchip with electric traces, macro shot",
    "job|work|employ|career|replace|worker": "office worker looking at AI on computer screen, modern workplace",
    "future|predict|2025|2026|next year": "futuristic smart city at night with holographic displays",
    "money|earn|income|salary|revenue|profit": "person at laptop with growth chart, financial success scene",
}


def _get_scene_style(prompt: str, keyword: str) -> str:
    """Match scene content to the most relevant cinematic visual style."""
    combined = (prompt + " " + keyword).lower()
    import re
    for pattern, style in SCENE_STYLE_MAP.items():
        if re.search(pattern, combined):
            return style
    return "cinematic data center corridor with glowing server racks, dramatic blue lighting"


def generate_ai_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    """
    Generate a scene-matching image using Pollinations.ai (free, no key needed).
    The prompt is derived from actual scene content for visual relevance.
    Falls back to a styled PIL image if Pollinations fails.
    """
    try:
        seed_base = int(hashlib.sha256(f"{job_id}:{index}:{prompt}".encode("utf-8")).hexdigest()[:8], 16)

        # Extract the core visual subject from the prompt
        clean_prompt = "".join(c if c.isalnum() or c in " ,.-" else "" for c in (prompt or ""))[:300]

        # Find the best matching cinematic style for this scene
        scene_style = _get_scene_style(clean_prompt, "")

        # Build a highly specific image prompt
        full_prompt = (
            f"{scene_style}, {clean_prompt[:120]}, "
            f"photorealistic 8K, cinematic dramatic lighting, sharp focus, "
            f"dark moody background, professional photography, no text, no watermark"
        )

        save_path = os.path.join(OUTPUT_DIR, f"{job_id}_img_{index}.jpg")
        if os.path.exists(save_path):
            return save_path

        log.info(f"Generating scene image: {scene_style[:60]}...")

        for attempt in range(3):
            try:
                seed = seed_base + attempt * 7919
                poll_url = (
                    f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}"
                    f"?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
                )
                resp = requests.get(poll_url, timeout=35)
                if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
                    os.makedirs(OUTPUT_DIR, exist_ok=True)
                    with open(save_path, "wb") as f:
                        f.write(resp.content)
                    log.info(f"✅ Scene image saved: {job_id}_img_{index}.jpg")
                    return save_path
            except Exception as e:
                log.warning(f"Pollinations attempt {attempt+1} failed: {e}")

        # Fallback: Picsum (random but better than solid color)
        try:
            picsum_url = f"https://picsum.photos/seed/{seed_base}/{width}/{height}"
            resp = requests.get(picsum_url, timeout=20)
            if resp.status_code == 200:
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return save_path
        except Exception:
            pass

        # Final fallback: Styled PIL gradient with tech elements
        return _generate_fallback_image(save_path, seed_base, width, height)

    except Exception as e:
        log.error(f"Image generation failed: {e}")
        return ""


def _generate_fallback_image(save_path: str, seed: int, width: int, height: int) -> str:
    """Generate a styled tech background image using PIL when all APIs fail."""
    try:
        from PIL import Image, ImageDraw
        PALETTES = [
            ((10, 15, 30), (20, 40, 80),  (0, 180, 255)),    # blue tech
            ((30, 5,  5),  (80, 20, 20),  (255, 60, 60)),    # red alert
            ((5,  30, 10), (20, 80, 40),  (0, 220, 100)),    # green matrix
            ((30, 20, 0),  (80, 55, 0),   (255, 200, 0)),    # amber gold
            ((20, 5,  35), (55, 10, 90),  (180, 90, 255)),   # purple neural
            ((0,  25, 30), (0,  70, 80),  (0, 220, 220)),    # teal data
        ]
        c0, c1, accent = PALETTES[seed % len(PALETTES)]
        rng = random.Random(seed)

        img = Image.new("RGB", (width, height), c0)
        draw = ImageDraw.Draw(img, "RGBA")

        # Gradient background
        for y in range(height):
            ratio = y / height
            r = int(c0[0] * (1 - ratio) + c1[0] * ratio)
            g = int(c0[1] * (1 - ratio) + c1[1] * ratio)
            b = int(c0[2] * (1 - ratio) + c1[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Grid lines
        for x in range(0, width + 80, 80):
            draw.line([(x, 0), (x + 200, height)], fill=(*accent, 28), width=1)
        for y in range(0, height, 70):
            draw.line([(0, y), (width, y + rng.randint(-30, 30))], fill=(*accent, 22), width=1)

        # Main tech object (chip/server)
        cx = int(width * (0.72 if seed % 2 == 0 else 0.28))
        cy = int(height * 0.46)
        cw, ch = int(width * 0.26), int(height * 0.30)
        box = [cx - cw//2, cy - ch//2, cx + cw//2, cy + ch//2]
        draw.rounded_rectangle(box, radius=20, fill=(4, 12, 20, 220), outline=(*accent, 200), width=4)
        inner = [box[0]+18, box[1]+16, box[2]-18, box[3]-16]
        draw.rounded_rectangle(inner, radius=14, fill=(18, 32, 50, 225), outline=(255, 255, 255, 45), width=2)
        # Pin traces
        for i in range(7):
            px = box[0] + int((i+1) * cw / 8)
            draw.line([(px, box[1]-35), (px, box[1])], fill=(*accent, 160), width=3)
            draw.line([(px, box[3]), (px, box[3]+35)], fill=(*accent, 160), width=3)
        for i in range(5):
            py = box[1] + int((i+1) * ch / 6)
            draw.line([(box[0]-40, py), (box[0], py)], fill=(*accent, 150), width=3)
            draw.line([(box[2], py), (box[2]+40, py)], fill=(*accent, 150), width=3)

        # Floating data cards
        for _ in range(5):
            crd_w = rng.randint(width//10, width//5)
            crd_h = rng.randint(height//16, height//8)
            x = rng.randint(30, max(31, width - crd_w - 30))
            y = rng.randint(30, max(31, height - crd_h - 60))
            draw.rounded_rectangle([x, y, x+crd_w, y+crd_h], radius=10, fill=(0, 0, 0, 75), outline=(*accent, 60), width=2)
            for j in range(3):
                lw = rng.randint(crd_w//3, crd_w-20)
                draw.rounded_rectangle([x+12, y+12+j*16, x+12+lw, y+17+j*16], radius=3, fill=(*accent, 120))

        # Glow
        glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for radius, alpha in [(int(min(width, height)*0.35), 28), (int(min(width, height)*0.22), 40)]:
            gd.ellipse([cx-radius, cy-radius, cx+radius, cy+radius], fill=(*accent, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), glow).convert("RGB")

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        img.save(save_path, "JPEG", quality=88)
        return save_path
    except Exception as e:
        log.error(f"Fallback image generation failed: {e}")
        return ""


def random_style(seed: int) -> str:
    styles = [
        "photorealistic tech conference stage",
        "cinematic startup office war room",
        "dramatic data center aisle",
        "futuristic robotics laboratory",
        "macro motherboard and processor scene",
        "news documentary AI control room",
    ]
    return styles[seed % len(styles)]


def generate_ai_video(prompt: str, job_id: str, index: int, is_shorts: bool = False) -> str:
    """Fal.ai video generation removed. Returns empty string — Pexels handles b-roll."""
    log.info("AI video b-roll disabled. Using Pexels stock video.")
    return ""
