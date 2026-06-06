#!/usr/bin/env python
"""
Diagnostic Testing Utility — Multi-Platform Uploads
Run this script to verify your credentials and upload functionality for Facebook, Instagram, and LinkedIn.
"""

import os
import sys
import logging
from pathlib import Path

# Add root folder to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

def test_uploads():
    log.info("=" * 70)
    log.info("  🚀 AI YouTube Bot - Multi-Platform Upload Test Utility")
    log.info("=" * 70)

    # 1. Load settings and verify environment toggles
    try:
        from config import settings
        log.info("Loading configurations...")
        
        log.info(f"  Facebook Upload:  {'✅ ENABLED' if settings.ENABLE_FACEBOOK_UPLOAD else '❌ DISABLED'}")
        log.info(f"  Instagram Upload: {'✅ ENABLED' if settings.ENABLE_INSTAGRAM_UPLOAD else '❌ DISABLED'}")
        log.info(f"  LinkedIn Upload:  {'✅ ENABLED' if settings.ENABLE_LINKEDIN_UPLOAD else '❌ DISABLED'}")
    except Exception as e:
        log.error(f"Error loading settings: {e}")
        sys.exit(1)

    # 2. Locate a sample video to upload
    # Search output directory for any valid .mp4 video to use for testing
    output_dir = Path("output")
    test_video = None
    
    if output_dir.exists():
        mp4_files = list(output_dir.glob("*.mp4"))
        if mp4_files:
            # Sort by size to pick a relatively small one for faster test uploads
            mp4_files.sort(key=lambda x: x.stat().st_size)
            test_video = str(mp4_files[0])
            log.info(f"Found sample video for testing: {test_video} ({mp4_files[0].stat().st_size / 1024 / 1024:.2f} MB)")
            
    if not test_video:
        # If no sample video is cached, create a dummy 2-second silent test file
        test_video = os.path.join("output", "test_diagnostic_video.mp4")
        log.warning(f"No sample video found in 'output/'. Creating dummy test video: {test_video}...")
        
        # We can construct a simple silent video using FFMPEG directly
        try:
            cmd = [
                settings.FFMPEG_PATH, "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=1280x720:d=3",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-c:v", "libx264", "-t", "3", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest",
                test_video
            ]
            import subprocess
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0 and os.path.exists(test_video):
                log.info("✅ Dummy test video created successfully.")
            else:
                log.error(f"Failed to create dummy video via FFmpeg: {res.stderr}")
                sys.exit(1)
        except Exception as e:
            log.error(f"FFmpeg failed to generate test dummy: {e}")
            sys.exit(1)

    # Mock content data structure
    test_content = {
        "chosen_topic": "AI Automation Diagnostic Test",
        "seo_title": "AI Automation Diagnostic Test #shorts",
        "seo_description": "Diagnostic run for multi-platform publishing. This video was published automatically by the AI Faceless Channel Automation Bot.",
        "tags": ["testing", "ai", "automation", "meta", "linkedin"]
    }

    # 3. Trigger Facebook Upload
    if settings.ENABLE_FACEBOOK_UPLOAD:
        log.info("\n----------------------------------------------------------------------")
        log.info("Starting Facebook Page Video Upload Test...")
        log.info("----------------------------------------------------------------------")
        from modules.facebook_uploader import upload_to_facebook
        fb_url = upload_to_facebook(test_content, test_video, is_reels=True)
        if fb_url:
            log.info(f"🎉 Facebook Upload Test Successful! Link: {fb_url}")
        else:
            log.error("❌ Facebook Upload Test Failed.")

    # 4. Trigger Instagram Upload
    if settings.ENABLE_INSTAGRAM_UPLOAD:
        log.info("\n----------------------------------------------------------------------")
        log.info("Starting Instagram Reels Upload Test...")
        log.info("----------------------------------------------------------------------")
        from modules.instagram_uploader import upload_to_instagram
        ig_url = upload_to_instagram(test_content, test_video)
        if ig_url:
            log.info(f"🎉 Instagram Reels Test Successful! Link: {ig_url}")
        else:
            log.error("❌ Instagram Reels Test Failed.")

    # 5. Trigger LinkedIn Upload
    if settings.ENABLE_LINKEDIN_UPLOAD:
        log.info("\n----------------------------------------------------------------------")
        log.info("Starting LinkedIn Video Post Test...")
        log.info("----------------------------------------------------------------------")
        from modules.linkedin_uploader import upload_to_linkedin
        li_url = upload_to_linkedin(test_content, test_video)
        if li_url:
            log.info(f"🎉 LinkedIn Upload Test Successful! Link: {li_url}")
        else:
            log.error("❌ LinkedIn Upload Test Failed.")

    log.info("\n" + "=" * 70)
    log.info("  📊 DIAGNOSTIC TEST FINISHED")
    log.info("=" * 70)

if __name__ == "__main__":
    test_uploads()
