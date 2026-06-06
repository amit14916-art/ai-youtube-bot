"""
modules/linkedin_uploader.py
Handles uploading videos and sharing them on LinkedIn using the UGC (User Generated Content) API.
"""

import logging
import os
import time
import requests
from config.settings import LINKEDIN_ACCESS_TOKEN, LINKEDIN_OWNER_URN, ENABLE_LINKEDIN_UPLOAD

log = logging.getLogger(__name__)

def upload_to_linkedin(content: dict, video_path: str) -> str:
    """
    Upload a video file to LinkedIn and share it on the user's feed.
    Returns the post share URN or empty string on failure.
    """
    if not ENABLE_LINKEDIN_UPLOAD:
        log.info("LinkedIn upload is disabled in settings. Skipping.")
        return ""

    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_OWNER_URN:
        log.warning("LinkedIn credentials (LINKEDIN_ACCESS_TOKEN or LINKEDIN_OWNER_URN) are missing. Skipping LinkedIn upload.")
        return ""

    if not os.path.exists(video_path):
        log.error(f"LinkedIn upload failed: Video file not found at '{video_path}'")
        return ""

    log.info("=== Uploading to LinkedIn Feed ===")

    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    try:
        # Step 1: Register video asset
        log.info("Registering video asset with LinkedIn...")
        register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        register_body = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                "owner": LINKEDIN_OWNER_URN,
                "supportedUploadMechanisms": ["SYNCHRONOUS_UPLOAD"]
            }
        }
        
        reg_resp = requests.post(register_url, headers=headers, json=register_body, timeout=30)
        reg_resp.raise_for_status()
        reg_data = reg_resp.json()
        
        value = reg_data.get("value", {})
        asset_urn = value.get("asset", "")
        upload_mechanism = value.get("uploadMechanism", {})
        upload_http = upload_mechanism.get("com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest", {})
        upload_url = upload_http.get("uploadUrl", "")
        
        if not asset_urn or not upload_url:
            log.error(f"Failed to get registration values. Response: {reg_data}")
            return ""
            
        log.info(f"Asset registered. URN: {asset_urn}. Uploading video binary...")

        # Step 2: Upload binary file
        # LinkedIn PUT request requires binary octet-stream
        with open(video_path, "rb") as video_file:
            upload_headers = {"Content-Type": "application/octet-stream"}
            # Merge extra headers from registration if any returned
            reg_headers = upload_http.get("headers", {})
            upload_headers.update(reg_headers)
            
            upload_resp = requests.put(upload_url, data=video_file, headers=upload_headers, timeout=300)
            upload_resp.raise_for_status()
            
        log.info("Video binary upload finished. Waiting for LinkedIn to process the video...")

        # Step 3: Poll asset status until READY
        asset_id = asset_urn.split(":")[-1]
        check_url = f"https://api.linkedin.com/v2/assets/{asset_id}"
        
        ready = False
        attempts = 0
        max_attempts = 15 # 15 * 10 seconds = 2.5 mins
        
        while not ready and attempts < max_attempts:
            attempts += 1
            time.sleep(10)
            
            check_resp = requests.get(check_url, headers=headers, timeout=20)
            check_resp.raise_for_status()
            asset_status = check_resp.json().get("status", "")
            
            log.info(f"LinkedIn video status (attempt {attempts}): {asset_status}")
            
            if asset_status == "AVAILABLE" or asset_status == "READY":
                ready = True
                log.info("LinkedIn video asset processing ready!")
            elif asset_status == "PROCESSING_FAILED":
                log.error("LinkedIn video processing failed in assets system.")
                return ""

        # Step 4: Share video asset in UGC Post
        log.info("Creating UGC Share post on LinkedIn...")
        share_url = "https://api.linkedin.com/v2/ugcPosts"
        
        title = content.get("seo_title", "AI Automation Update")
        caption = f"{title}\n\n{content.get('seo_description', '')}"
        
        share_body = {
            "author": LINKEDIN_OWNER_URN,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": caption
                    },
                    "shareMediaCategory": "VIDEO",
                    "media": [
                        {
                            "media": asset_urn,
                            "status": "READY",
                            "title": {
                                "text": title
                            }
                        }
                    ]
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        share_resp = requests.post(share_url, headers=headers, json=share_body, timeout=30)
        share_resp.raise_for_status()
        share_data = share_resp.json()
        
        post_urn = share_data.get("id", "")
        if post_urn:
            log.info(f"✅ LinkedIn post shared successfully! Post URN: {post_urn}")
            # Format typical LinkedIn post link:
            return f"https://www.linkedin.com/feed/update/{post_urn}"
        else:
            log.error(f"Share request completed but returned no post URN. Response: {share_data}")
            return ""

    except Exception as e:
        log.error(f"❌ LinkedIn upload failed: {e}")
        return ""
