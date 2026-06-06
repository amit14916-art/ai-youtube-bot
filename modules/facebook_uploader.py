"""
modules/facebook_uploader.py
Handles uploading videos to a Facebook Page using the Meta Graph Video API.
"""

import logging
import os
import requests
from config.settings import FB_PAGE_ACCESS_TOKEN, FB_PAGE_ID, ENABLE_FACEBOOK_UPLOAD

log = logging.getLogger(__name__)

def upload_to_facebook(content: dict, video_path: str, is_reels: bool = False) -> str:
    """
    Upload a video file to the configured Facebook Page.
    Handles landscape videos and vertical reels.
    Returns the post URL or empty string on failure.
    """
    if not ENABLE_FACEBOOK_UPLOAD:
        log.info("Facebook upload is disabled in settings. Skipping.")
        return ""

    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        log.warning("Facebook credentials (FB_PAGE_ACCESS_TOKEN or FB_PAGE_ID) are missing. Skipping Facebook upload.")
        return ""

    if not os.path.exists(video_path):
        log.error(f"Facebook upload failed: Video file not found at '{video_path}'")
        return ""

    log.info(f"=== Uploading to Facebook Page ({'Reels' if is_reels else 'Video'}) ===")
    
    url = f"https://graph-video.facebook.com/v19.0/{FB_PAGE_ID}/videos"
    
    title = content.get("seo_title", "AI Tech Update")
    description = content.get("seo_description", "")
    
    try:
        data = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "title": title,
            "description": description,
        }
        
        # Post the video using multipart/form-data
        log.info(f"Sending video file '{os.path.basename(video_path)}' to Facebook API...")
        with open(video_path, "rb") as video_file:
            files = {"file": video_file}
            response = requests.post(url, data=data, files=files, timeout=300)
            
        response.raise_for_status()
        res_json = response.json()
        
        video_id = res_json.get("id")
        if video_id:
            fb_url = f"https://www.facebook.com/watch/?v={video_id}"
            log.info(f"✅ Facebook upload successful! Video URN/ID: {video_id} | Post: {fb_url}")
            return fb_url
        else:
            log.error(f"Facebook API completed upload but returned no ID. Response: {res_json}")
            return ""
            
    except Exception as e:
        log.error(f"❌ Facebook upload failed: {e}")
        return ""
