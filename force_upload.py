import os
import glob
import logging
from modules.uploader import upload_to_youtube
from modules.video_creator import create_thumbnail # If needed
import json

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def force_upload_latest():
    # Find latest video in output (either long or short)
    videos = glob.glob("output/*_shorts.mp4") + glob.glob("output/*_video.mp4")
    if not videos:
        log.error("No short or long videos found in output folder.")
        return

    latest_video = max(videos, key=os.path.getctime)
    job_id = os.path.basename(latest_video).replace("_shorts.mp4", "").replace("_video.mp4", "")
    
    # Try to find content json
    content_file = os.path.join("output", f"{job_id}_content.json")
    if not os.path.exists(content_file):
        log.error(f"Content file missing for {job_id}")
        return
        
    with open(content_file, "r") as f:
        content = json.load(f)
        
    log.info(f"Force uploading: {latest_video}")
    thumbnail = os.path.join("output", f"{job_id}_thumbnail.jpg")
    if not os.path.exists(thumbnail):
        thumbnail = "" # Optional
        
    url = upload_to_youtube(content, latest_video, thumbnail)
    print(f"\n✅ SUCCESS! Video uploaded to: {url}")

if __name__ == "__main__":
    force_upload_latest()
