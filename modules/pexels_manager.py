"""
modules/pexels_manager.py
Handles fetching free stock footage from Pexels API to replace static images.
"""

import os
import requests
import random
import logging
from pathlib import Path
from config.settings import OUTPUT_DIR, PEXELS_API_KEY

log = logging.getLogger(__name__)

def get_stock_video(query: str, orientation: str = "landscape", min_duration: int = 5) -> str:
    """
    Search Pexels for a stock video and return the local path to the downloaded file.
    """
    if not PEXELS_API_KEY:
        log.warning("Pexels API key missing. Falling back to AI images.")
        return ""

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "per_page": 10,
        "orientation": orientation,
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        videos = data.get("videos", [])
        if not videos:
            log.info(f"No Pexels videos found for: {query}")
            return ""

        # Filter for videos with decent quality and duration
        # Sort by duration and pick a random one from top 5
        valid_videos = [v for v in videos if v.get("duration", 0) >= min_duration]
        if not valid_videos: valid_videos = videos
        
        chosen_video = random.choice(valid_videos[:5])
        
        # Pick the right resolution link
        # Look for HD (1920x1080) or similar
        video_files = chosen_video.get("video_files", [])
        best_file = None
        
        # Sort by quality: we want something around 1080p if possible, or at least 720p
        target_width = 1920 if orientation == "landscape" else 1080
        for vf in video_files:
            if vf.get("width") == target_width:
                best_file = vf
                break
        
        if not best_file:
            best_file = video_files[0] # Fallback to first

        download_url = best_file.get("link")
        if not download_url: return ""

        # Save locally
        filename = f"pexels_{chosen_video['id']}_{orientation}.mp4"
        save_path = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(save_path):
            return save_path

        log.info(f"Downloading Pexels video: {query} -> {save_path}")
        v_resp = requests.get(download_url, stream=True, timeout=30)
        v_resp.raise_for_status()
        
        with open(save_path, "wb") as f:
            for chunk in v_resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return save_path

    except Exception as e:
        log.error(f"Pexels search/download failed: {e}")
        return ""
