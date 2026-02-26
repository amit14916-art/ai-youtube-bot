"""
modules/asset_generator.py
Handles AI image generation for video backgrounds using Pollinations.ai.
"""

import os
import requests
import json
import logging
from config.settings import OUTPUT_DIR, FAL_API_KEY

log = logging.getLogger(__name__)

def generate_ai_image(prompt: str, job_id: str, index: int, width: int = 1920, height: int = 1080) -> str:
    """
    Generate an image using Fal.ai (FLUX) and save it locally.
    Uses pollinations.ai as a fallback if Fal key is missing or API fails.
    """
    try:
        # Sanitize prompt
        clean_prompt = "".join(c if c.isalnum() or c in " ,.-" else "" for c in prompt)[:500]
        full_prompt = f"{clean_prompt}, cinematic lighting, 8k resolution, highly detailed, professional photography, premium tech aesthetic, clean sharp focus, bokeh background, dramatic atmosphere"
        
        save_path = os.path.join(OUTPUT_DIR, f"{job_id}_img_{index}.jpg")
        
        # Try Fal.ai (FLUX) first if API key is provided
        if FAL_API_KEY:
            log.info(f"Generating image via Fal.ai (FLUX) for: {clean_prompt}")
            
            if width > height:
                image_size = "landscape_16_9"
            elif height > width:
                image_size = "portrait_16_9"
            else:
                image_size = "square_hd"
                
            url = "https://fal.run/fal-ai/flux/schnell"
            headers = {
                "Authorization": f"Key {FAL_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "prompt": full_prompt,
                "image_size": image_size,
                "num_inference_steps": 4, # Schnell model uses 4 steps
            }
            
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                img_url = data.get("images", [{}])[0].get("url")
                if img_url:
                    img_data = requests.get(img_url, timeout=30)
                    with open(save_path, "wb") as f:
                        f.write(img_data.content)
                    return save_path
            
            log.warning(f"Fal.ai failed with status {resp.status_code}: {resp.text}. Falling back to Pollinations.ai...")
        
        # Fallback to Pollinations.ai 
        log.info(f"Generating fallback image via Pollinations.ai for: {clean_prompt}")
        poll_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(full_prompt)}?width={width}&height={height}&seed={index}"
        
        resp = requests.get(poll_url, timeout=30)
        resp.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(resp.content)
            
        return save_path
    except Exception as e:
        log.error(f"Image generation failed for {prompt}: {e}")
        return ""
