"""
main.py — AI Faceless YouTube Channel Automation Bot
===============================================================
Pipeline:
  1. Research trending AI topics (Google Trends + YouTube)
  2. Claude AI picks best topic + writes SEO content + script
  3. Text-to-Speech voiceover (ElevenLabs or gTTS)
  4. Build faceless video (animated slides + audio + BGM)
  5. Generate eye-catching thumbnail
  6. Upload everything to YouTube automatically
  7. Schedule to run daily at configured time

Usage:
  python main.py              # Run once immediately
  python main.py --schedule   # Run on schedule (daily)
  python main.py --dry-run    # Research + generate only, skip upload
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import schedule

from config.settings import (
    UPLOAD_HOUR, 
    UPLOAD_MINUTE, 
    LONG_ONLY_TIMES, 
    OUTPUT_DIR, 
    LOG_FILE
)


# -----------------------------------------------------------------
#  LOGGING & FFMPEG SETUP
# -----------------------------------------------------------------

os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# Try to find ffmpeg via imageio-ffmpeg if not in path
try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_exe:
        os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_exe
        # Set for pydub
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_exe
        log.info(f"FFMPEG found -> {ffmpeg_exe}")
except ImportError:
    log.warning("imageio-ffmpeg not installed, ffmpeg might not be found")
except Exception as e:
    log.warning(f"Error setting FFMPEG path: {e}")


# -----------------------------------------------------------------
#  CORE PIPELINE
# -----------------------------------------------------------------

def run_pipeline(dry_run: bool = False, shorts_only: bool = False, long_only: bool = False, topic: str = None) -> dict | None:
    """
    Execute the full content creation and upload pipeline.
    Returns a dict with results or None on failure.
    """
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log.info("=" * 60)
    log.info(f"  AI YouTube Bot - Job {job_id}")
    log.info("=" * 60)

    result = {"job_id": job_id, "status": "started", "timestamp": datetime.now().isoformat()}

    try:
        # -- PHASE 1: RESEARCH ----------------------------------
        from modules.researcher import run_research
        content = run_research(custom_topic=topic, shorts_only=shorts_only)

        log.info(f"\n{'-'*50}")
        log.info(f"  TOPIC   : {content['chosen_topic']}")
        log.info(f"  TITLE   : {content['seo_title']}")
        log.info(f"  SCRIPT  : {len(content['script'].split())} words")
        log.info(f"{'-'*50}\n")

        # Save content to JSON for debugging/reference
        content_file = os.path.join(OUTPUT_DIR, f"{job_id}_content.json")
        with open(content_file, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        log.info(f"Content saved -> {content_file}")

        # -- PHASE 2: AUDIO -------------------------------------
        from modules.audio_generator import generate_audio
        audio_path = generate_audio(content["script"], job_id)
        result["audio_path"] = audio_path

        # -- PHASE 3: VIDEO (Long) ------------------------------
        from modules.video_creator import create_video, create_thumbnail
        video_path = None
        thumbnail_path = None
        
        if not shorts_only:
            # Generate dedicated thumbnail background
            from modules.asset_generator import generate_ai_image
            thumb_bg = generate_ai_image(content.get("thumbnail_prompt", content["chosen_topic"]), job_id, 999) # 999 for thumb
            video_path    = create_video(content, audio_path, job_id, is_shorts=False)
            thumbnail_path = create_thumbnail(content, job_id, thumb_bg)
            result["video_path"]     = video_path
            result["thumbnail_path"] = thumbnail_path
        
        # -- PHASE 4: VIDEO (Shorts) -----------------------------
        if not long_only:
            log.info("Generating Vertical Shorts version...")
            shorts_path = create_video(content, audio_path, job_id, is_shorts=True)
            result["shorts_path"] = shorts_path

        # -- PHASE 5: UPLOAD -------------------------------------
        if dry_run:
            log.info("DRY RUN — skipping YouTube upload")
            result["status"] = "dry_run_complete"
            log.info(f"\n✅ Dry run complete! Files saved in: {OUTPUT_DIR}/")
        else:
            from modules.uploader import upload_to_youtube
            from modules.notifier import send_whatsapp_notification
            
            # Upload Long Video
            if not shorts_only:
                if not video_path or not os.path.exists(video_path):
                    raise ValueError("Long video generation failed (missing video file).")
                log.info("🚀 Uploading Long Video...")
                url = upload_to_youtube(content, video_path, thumbnail_path)
                result["youtube_url"] = url
                # Send WhatsApp notification
                send_whatsapp_notification(url, content["seo_title"])
            
            # Upload Shorts
            if not long_only:
                if not shorts_path or not os.path.exists(shorts_path):
                    raise ValueError("Shorts video generation failed (missing short video file).")
                log.info("🚀 Uploading Shorts Video...")
                content_shorts = content.copy()
                content_shorts["seo_title"] = f"{content['seo_title'][:50]}... #shorts"
                content_shorts["seo_description"] += "\n\n#shorts #ai #tech"
                shorts_url = upload_to_youtube(content_shorts, shorts_path, "")
                result["shorts_url"] = shorts_url

            result["status"] = "uploaded"
            log.info(f"\n🎉 SUCCESS!")
            if not shorts_only: log.info(f"Long: {result.get('youtube_url')}")
            if not long_only: log.info(f"Shorts: {result.get('shorts_url')}")

        # Save result summary
        summary_file = os.path.join(OUTPUT_DIR, f"{job_id}_result.json")
        with open(summary_file, "w") as f:
            json.dump(result, f, indent=2)

        return result

    except Exception as e:
        log.exception(f"Pipeline failed: {e}")
        result["status"] = "failed"
        result["error"] = str(e)
        return result


# -----------------------------------------------------------------
#  SCHEDULER
# -----------------------------------------------------------------

def run_shorts_only():
    """Run pipeline but only for Shorts."""
    run_pipeline(dry_run=False, shorts_only=True)

def run_long_only():
    """Run pipeline but only for Long videos."""
    run_pipeline(dry_run=False, shorts_only=False, long_only=True)

def start_scheduler():
    """Start the daily scheduler with multiple upload times."""
    from config.settings import LONG_ONLY_TIMES, SHORTS_ONLY_TIMES
    log.info(f"📅 Scheduler started")
    log.info(f"  Long Only  : {LONG_ONLY_TIMES}")
    log.info(f"  Shorts Only: {SHORTS_ONLY_TIMES}")

    for t in LONG_ONLY_TIMES:
        schedule.every().day.at(t).do(run_long_only)
        
    for t in SHORTS_ONLY_TIMES:
        schedule.every().day.at(t).do(run_shorts_only)

    while True:
        schedule.run_pending()
        time.sleep(30)


# -----------------------------------------------------------------
#  ENTRY POINT
# -----------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Faceless YouTube Channel Automation Bot"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run on daily schedule (keeps process alive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate content and video but skip YouTube upload",
    )
    parser.add_argument(
        "--shorts-only",
        action="store_true",
        help="Only generate and upload the Vertical Short",
    )
    parser.add_argument(
        "--long-only",
        action="store_true",
        help="Only generate and upload the Long-form video (no Shorts)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Custom topic for this run",
    )
    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    else:
        for attempt in range(3):
            try:
                result = run_pipeline(dry_run=args.dry_run, shorts_only=args.shorts_only, long_only=args.long_only, topic=args.topic)
                if result and result.get("status") in ("uploaded", "dry_run_complete"):
                    sys.exit(0)
                log.warning(f"Run failed with status {result.get('status')} (attempt {attempt+1}/3). Retrying in 60s...")
            except Exception as e:
                log.error(f"Critical error in main wrapper: {e}")
            
            if attempt < 2:
                import time
                time.sleep(60)
                
        sys.exit(1)
