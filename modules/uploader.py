"""
modules/uploader.py
Uploads video + thumbnail to YouTube using the Data API v3.
Uses OAuth 2.0 — first run opens a browser for authorization.
Token is saved to config/token.json for subsequent runs.
"""

import logging
import os
import time

from config.settings import (
    CATEGORY_ID,
    DEFAULT_LANGUAGE,
    PRIVACY_STATUS,
    TAGS_EXTRA,
    YOUTUBE_CLIENT_SECRETS_FILE,
)

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
TOKEN_FILE = "config/token.json"


# -----------------------------------------------------------------
#  AUTHENTICATION
# -----------------------------------------------------------------

def get_authenticated_service():
    """Return an authorized YouTube API service object."""
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                YOUTUBE_CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=8080)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    service = build("youtube", "v3", credentials=creds)
    log.info("YouTube API authenticated [OK]")
    return service


# -----------------------------------------------------------------
#  VIDEO UPLOAD
# -----------------------------------------------------------------

def upload_video(service, content: dict, video_path: str) -> str:
    """Upload video file. Returns YouTube video ID."""
    from googleapiclient.http import MediaFileUpload

    tags = list(set(content.get("tags", []) + TAGS_EXTRA))[:30]

    body = {
        "snippet": {
            "title": content["seo_title"],
            "description": content["seo_description"],
            "tags": tags,
            "categoryId": CATEGORY_ID,
            "defaultLanguage": DEFAULT_LANGUAGE,
        },
        "status": {
            "privacyStatus": PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        chunksize=10 * 1024 * 1024,  # 10 MB chunks
        resumable=True,
        mimetype="video/mp4",
    )

    log.info(f"Uploading '{content['seo_title']}' to YouTube…")
    request = service.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                log.info(f"Upload progress: {pct}%")
        except Exception as e:
            retry += 1
            if retry > 5:
                raise
            wait = 2 ** retry
            log.warning(f"Upload error (retry {retry}): {e} — waiting {wait}s")
            time.sleep(wait)

    video_id = response["id"]
    log.info(f"Video uploaded! ID: {video_id}  ->  https://youtu.be/{video_id}")
    return video_id


# -----------------------------------------------------------------
#  THUMBNAIL UPLOAD
# -----------------------------------------------------------------

def upload_thumbnail(service, video_id: str, thumbnail_path: str):
    """Set custom thumbnail for a video."""
    from googleapiclient.http import MediaFileUpload
    try:
        media = MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
        service.thumbnails().set(videoId=video_id, media_body=media).execute()
        log.info(f"Thumbnail set for video {video_id} [OK]")
    except Exception as e:
        log.warning(f"Thumbnail upload failed: {e}")


# -----------------------------------------------------------------
#  ADD VIDEO TO PLAYLIST (optional)
# -----------------------------------------------------------------

def add_to_playlist(service, video_id: str, playlist_id: str):
    """Add video to a specific playlist."""
    if not playlist_id:
        return
    try:
        service.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        log.info(f"Added to playlist {playlist_id} [OK]")
    except Exception as e:
        log.warning(f"Playlist insert failed: {e}")


# -----------------------------------------------------------------
#  PUBLIC ENTRY POINT
# -----------------------------------------------------------------

def upload_to_youtube(content: dict, video_path: str, thumbnail_path: str) -> str:
    """
    Full upload pipeline.
    Returns YouTube video URL.
    """
    log.info("=== Uploading to YouTube ===")
    service  = get_authenticated_service()
    video_id = upload_video(service, content, video_path)
    if thumbnail_path and os.path.exists(thumbnail_path):
        upload_thumbnail(service, video_id, thumbnail_path)
    url = f"https://youtu.be/{video_id}"
    return url
