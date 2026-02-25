"""
modules/asset_generator.py
Handles AI image generation for video backgrounds using Pollinations.ai.
"""

import os
import requests
import logging
from pathlib import Path
from config.settings import OUTPUT_DIR

log = logging.getLogger(__name__)

def generate_ai_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    """
    Generate an image using Pollinations.ai and save it locally.
    """
    try:
        # Sanitize prompt
        clean_prompt = "".join(c if c.isalnum() or c == " " else "" for c in prompt)[:200]
        # Pollinations.ai URL format: https://pollinations.ai/p/{prompt}?width={w}&height={h}&seed={s}&model=flux
        # Use a seed for some variety but stability within a job if needed. 
        # Actually, different prompt per slide is better.
        
        # We can add a "style" suffix to keep it cinematic
        full_prompt = f"{clean_prompt}, cinematic, 4k, photorealistic, premium tech aesthetic, blurred background style"
        
        url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}?width={width}&height={height}&seed={index}"
        
        save_path = os.path.join(OUTPUT_DIR, f"{job_id}_img_{index}.jpg")
        
        log.info(f"Generating AI image for: {clean_prompt}")
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(resp.content)
            
        return save_path
    except Exception as e:
        log.error(f"Image generation failed for {prompt}: {e}")
        return ""
