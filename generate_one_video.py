import logging
import os
import subprocess
import sys
from PIL import Image, ImageDraw
from modules import asset_generator, video_creator
from modules.audio_generator import generate_audio
from modules.video_creator import create_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def simple_image_to_video_clip(image_path: str, duration: float, output_path: str, w: int, h: int, avatar_path: str = "", lower_third_text: str = "") -> bool:
    cmd = [
        video_creator.FFMPEG_PATH, "-y",
        "-loop", "1",
        "-i", image_path,
        "-t", str(max(duration, 1.0)),
        "-vf", f"scale={w}:{h},format=yuv420p",
        "-r", str(video_creator.VIDEO_FPS),
        "-c:v", "libx264",
        "-preset", video_creator.INTERMEDIATE_CLIP_PRESET,
        "-crf", str(video_creator.INTERMEDIATE_CLIP_CRF),
        "-an",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print("simple_image_to_video_clip failed:", result.stderr)
        return False
    return True

video_creator.image_to_video_clip = simple_image_to_video_clip


def local_fallback_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    save_path = os.path.join("output", f"{job_id}_img_{index}.jpg")
    os.makedirs("output", exist_ok=True)
    base = Image.new("RGB", (width, height), (18, 24, 48))
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(18 * (1 - ratio) + 58 * ratio)
        g = int(24 * (1 - ratio) + 110 * ratio)
        b = int(48 * (1 - ratio) + 170 * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    draw.text((width // 12, height // 4), prompt[:120], fill=(255, 255, 255))
    base.save(save_path, "JPEG", quality=85)
    return save_path

asset_generator.generate_ai_image = local_fallback_image
sys.modules['modules.asset_generator'].generate_ai_image = local_fallback_image
video_creator.create_presenter_avatar = lambda job_id, topic, is_shorts=False: ""

job_id = "one_video_test"
content = {
    "chosen_topic": "AI automation test",
    "seo_title": "AI Automation Test Video",
    "script": "Host A: Welcome to the AI automation test video. Host B: This video demonstrates the bot creating a sample clip from a simple script.",
    "thumbnail_prompt": "AI automation test background"
}

print("Starting sample video generation...")
try:
    audio_result = generate_audio(content["script"], job_id)
    print("Audio generated:", audio_result)
    video_path = create_video(content, audio_result["audio_path"], job_id, is_shorts=False, audio_chunk_timing=audio_result.get("audio_chunk_timing", []))
    print("Video generated at:", video_path)
except Exception as e:
    print("Generation failed:", type(e).__name__, e)
    raise
