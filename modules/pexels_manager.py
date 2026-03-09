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
        "per_page": 15,
        # Remove orientation restriction because our FFmpeg already center-crops perfectly!
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        log.info(f"Pexels search status for '{query}': {resp.status_code}")
        if resp.status_code != 200:
            log.warning(f"Pexels API error {resp.status_code}: {resp.text[:100]}")
            return ""

        data = resp.json()
        videos = data.get("videos", [])
        
        # Fallback 1: Broaden to first word if multi-word query fails
        if not videos and len(query.split()) > 1:
            fallback_query = query.split()[0]
            log.info(f"No Pexels videos found for '{query}', trying: '{fallback_query}'...")
            params["query"] = fallback_query
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            data = resp.json()
            videos = data.get("videos", [])

        # Fallback 2: Technology generic (always works)
        if not videos and query != "technology":
            log.info(f"No videos found, falling back to 'technology'...")
            params["query"] = "technology"
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            data = resp.json()
            videos = data.get("videos", [])

        # Fallback 3: Nature/Abstract
        if not videos:
            fallback_query = random.choice(["nature bokeh", "abstract light", "cyber city", "blue background"])
            log.info(f"Complete failure, trying random fallback: {fallback_query}")
            params["query"] = fallback_query
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            data = resp.json()
            videos = data.get("videos", [])
            
        if not videos:
            log.error("ABSOLUTE FAILURE: Pexels found nothing even with fallbacks.")
            return ""

        # Filter for videos with decent quality and duration
        valid_videos = [v for v in videos if v.get("duration", 0) >= min_duration]
        if not valid_videos: valid_videos = videos
        
        chosen_video = random.choice(valid_videos[:5])
        video_files = chosen_video.get("video_files", [])
        
        # INCREASED LIMIT to 10,000,000 (10MP) to allow 4K videos if needed, but still avoid massive files
        safe_files = [x for x in video_files if ((x.get("width") or 0) * (x.get("height") or 0)) <= 10000000]
        if not safe_files:
            safe_files = video_files # fallback to all if none exist
            
        safe_files.sort(key=lambda x: ((x.get("width") or 0) * (x.get("height") or 0)), reverse=True)
        best_file = safe_files[0] if safe_files else None

        if not best_file: return ""
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
