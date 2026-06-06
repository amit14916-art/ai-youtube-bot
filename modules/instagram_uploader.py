"""
modules/instagram_uploader.py
Handles uploading reels to Instagram using the Meta Graph API.
Instagram requires a publicly reachable video URL for publishing.
"""

import logging
import os
import time
import requests
from config.settings import FB_PAGE_ACCESS_TOKEN, IG_USER_ID, ENABLE_INSTAGRAM_UPLOAD

log = logging.getLogger(__name__)

def _get_public_video_url(video_path: str) -> str:
    """
    Upload local video to a free temporary host to get a public URL.
    Tries tmpfiles.org first, falls back to file.io.
    """
    filename = os.path.basename(video_path)
    
    # 1. Try tmpfiles.org (free, no account needed)
    try:
        log.info(f"Uploading '{filename}' to tmpfiles.org for temporary public hosting...")
        url = "https://tmpfiles.org/api/v1/upload"
        with open(video_path, "rb") as f:
            files = {"file": f}
            response = requests.post(url, files=files, timeout=60)
            
        response.raise_for_status()
        res_json = response.json()
        raw_url = res_json.get("data", {}).get("url", "")
        if raw_url:
            # Convert view link to direct download link:
            # e.g., 'https://tmpfiles.org/12345/video.mp4' -> 'https://tmpfiles.org/dl/12345/video.mp4'
            direct_url = raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
            log.info(f"✅ Temporary hosting success (tmpfiles.org): {direct_url}")
            return direct_url
    except Exception as e:
        log.warning(f"tmpfiles.org hosting failed: {e}. Trying file.io fallback...")

    # 2. Try file.io fallback
    try:
        log.info(f"Uploading '{filename}' to file.io for temporary public hosting...")
        url = "https://file.io"
        with open(video_path, "rb") as f:
            files = {"file": f}
            # Set expiry to 1 day
            data = {"expires": "1d"}
            response = requests.post(url, files=files, data=data, timeout=60)
            
        response.raise_for_status()
        res_json = response.json()
        direct_url = res_json.get("link", "")
        if direct_url:
            log.info(f"✅ Temporary hosting success (file.io): {direct_url}")
            return direct_url
    except Exception as e:
        log.error(f"❌ Temporary hosting fallback (file.io) also failed: {e}")
        
    return ""

def upload_to_instagram(content: dict, video_path: str) -> str:
    """
    Upload a vertical video to Instagram Reels.
    Instagram Graph API does not support local uploads directly;
    we host it temporarily, create a container, poll, and publish.
    """
    if not ENABLE_INSTAGRAM_UPLOAD:
        log.info("Instagram upload is disabled in settings. Skipping.")
        return ""

    if not FB_PAGE_ACCESS_TOKEN or not IG_USER_ID:
        log.warning("Instagram credentials (FB_PAGE_ACCESS_TOKEN or IG_USER_ID) are missing. Skipping Instagram upload.")
        return ""

    if not os.path.exists(video_path):
        log.error(f"Instagram upload failed: Video file not found at '{video_path}'")
        return ""

    log.info("=== Uploading to Instagram Reels ===")
    
    # Step 1: Upload to temporary public host
    public_url = _get_public_video_url(video_path)
    if not public_url:
        log.error("Failed to temporarily host video. Cannot proceed with Instagram upload.")
        return ""

    caption = f"{content.get('seo_title', '')}\n\n{content.get('seo_description', '')}"
    # Truncate caption if it exceeds Instagram's 2200 character limit
    if len(caption) > 2180:
        caption = caption[:2180] + "..."

    try:
        # Step 2: Create media container for Reels
        log.info("Creating Instagram Reels media container...")
        container_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
        params = {
            "media_type": "REELS",
            "video_url": public_url,
            "caption": caption,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        
        response = requests.post(container_url, params=params, timeout=30)
        response.raise_for_status()
        container_id = response.json().get("id")
        
        if not container_id:
            log.error(f"Failed to get container ID. Response: {response.text}")
            return ""
            
        log.info(f"Container created successfully. ID: {container_id}. Waiting for processing...")

        # Step 3: Poll status of the container until finished (timeout in ~5 mins)
        status_url = f"https://graph.facebook.com/v19.0/{container_id}"
        status_params = {
            "fields": "status_code",
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        
        processing = True
        attempts = 0
        max_attempts = 45 # 45 * 10 seconds = 7.5 mins
        
        while processing and attempts < max_attempts:
            attempts += 1
            time.sleep(10)
            
            status_resp = requests.get(status_url, params=status_params, timeout=20)
            status_resp.raise_for_status()
            status_code = status_resp.json().get("status_code", "")
            
            log.info(f"Reels processing status (attempt {attempts}): {status_code}")
            
            if status_code == "FINISHED":
                processing = False
                log.info("Reels video processing complete!")
            elif status_code == "ERROR":
                log.error("Instagram Reels video processing failed in container.")
                return ""
        
        if processing:
            log.error("Instagram Reels container processing timed out.")
            return ""

        # Step 4: Publish the completed container
        log.info("Publishing Instagram Reels media...")
        publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
        publish_params = {
            "creation_id": container_id,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        
        pub_response = requests.post(publish_url, params=publish_params, timeout=30)
        pub_response.raise_for_status()
        media_id = pub_response.json().get("id")
        
        if media_id:
            # Note: Graph API doesn't return the direct URL immediately, so we return a standard placeholder path.
            log.info(f"✅ Instagram Reels published successfully! Media ID: {media_id}")
            return f"https://instagram.com/p/{media_id}"
        else:
            log.error(f"Publish request completed but returned no Media ID. Response: {pub_response.text}")
            return ""

    except Exception as e:
        log.error(f"❌ Instagram Reels upload failed: {e}")
        return ""
