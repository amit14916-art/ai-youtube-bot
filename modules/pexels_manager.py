"""
modules/pexels_manager.py
Handles fetching free stock footage from Pexels API.
Each scene gets a UNIQUE clip that matches what is being spoken.
"""

import os
import requests
import random
import hashlib
import logging
from config.settings import OUTPUT_DIR, PEXELS_API_KEY

log = logging.getLogger(__name__)

# Track which video IDs we've already used this run so every scene gets a DIFFERENT clip
_used_video_ids: set = set()

GENERIC_TERMS = {
    "technology", "artificial", "intelligence", "future", "innovation",
    "tech", "digital", "modern", "abstract", "generic"
}


def _clean_query(query: str) -> str:
    """Keep stock searches concrete enough to avoid unrelated generic footage."""
    words = [
        w for w in "".join(c if c.isalnum() or c.isspace() else " " for c in (query or "").lower()).split()
        if w not in GENERIC_TERMS
    ]
    return " ".join(words[:2]).strip()


def _search_pexels(query: str, headers: dict, per_page: int = 30,
                   orientation: str = "") -> list:
    """Raw Pexels search returning list of video dicts."""
    url = "https://api.pexels.com/videos/search"
    # Randomise page so every run doesn't pull the exact same top clips
    page = random.randint(1, 3)
    params = {"query": query, "per_page": per_page, "page": page}
    if orientation in ("landscape", "portrait", "square"):
        params["orientation"] = orientation
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        log.info(f"  Pexels '{query}' (page={page}, orient={orientation or 'any'}): HTTP {resp.status_code}")
        if resp.status_code != 200:
            # page > 1 might be empty — retry page 1
            if page > 1:
                params["page"] = 1
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                if resp.status_code != 200:
                    return []
            else:
                return []
        return resp.json().get("videos", [])
    except Exception as e:
        log.warning(f"  Pexels search error for '{query}': {e}")
        return []


def get_stock_video(
    query: str,
    alt_query: str = "",
    orientation: str = "landscape",
    min_duration: int = 4,
    scene_index: int = -1,
    job_id: str = "",
) -> str:
    """
    Search Pexels for a stock video clip and return its local path.
    - Tries primary query first, then alt_query, then simplified fallbacks.
    - Ensures each scene gets a UNIQUE clip (avoids repeating the same footage).
    - Downloads the best-resolution file within a safe size limit.
    """
    if not PEXELS_API_KEY:
        log.warning("Pexels API key missing.")
        return ""

    headers = {"Authorization": PEXELS_API_KEY}
    query = _clean_query(query) or "data center"
    alt_query = _clean_query(alt_query)
    videos = []

    # ── 1. Primary query (with correct orientation) ─────────────────
    videos = _search_pexels(query, headers, orientation=orientation)

    # ── 2. Alt keyword (from Director Agent's backup suggestion) ────
    if not videos and alt_query and alt_query != query:
        log.info(f"  No results for '{query}', trying alt: '{alt_query}'")
        videos = _search_pexels(alt_query, headers, orientation=orientation)

    # ── 3. First word of primary query (relax orientation) ──────────
    if not videos and len(query.split()) > 1:
        first_word = query.split()[0]
        if first_word not in GENERIC_TERMS and len(first_word) > 3:
            log.info(f"  Still empty, trying first word: '{first_word}'")
            videos = _search_pexels(first_word, headers, orientation=orientation)

    # ── 4. Smart topic-based generic fallbacks ───────────────────────
    SMART_FALLBACKS = [
        "data center",
        "coding screen",
        "server room",
        "computer chip",
        "robot arm",
        "office desk",
        "business meeting",
        "stock market",
        "medical scan",
        "factory robot",
        "city night",
        "typing laptop",
        "video editing",
        "camera setup",
        "creator desk",
        "phone screen",
        "mobile app",
        "calendar app",
        "hacker screen",
        "security camera",
        "developer laptop",
    ]
    if not videos:
        seed = int(hashlib.sha256(f"{job_id}:{scene_index}:{query}".encode("utf-8")).hexdigest()[:8], 16)
        fallback = SMART_FALLBACKS[seed % len(SMART_FALLBACKS)]
        log.info(f"  All specific searches failed, using smart fallback: '{fallback}'")
        videos = _search_pexels(fallback, headers, orientation=orientation)

    # ── 5. Last resort ───────────────────────────────────────────────
    if not videos:
        log.error(f"  PEXELS TOTAL FAILURE for query '{query}'")
        return ""

    # ── Filter: prefer minimum duration ─────────────────────────────
    valid = [v for v in videos if v.get("duration", 0) >= min_duration]
    if not valid:
        valid = videos

    # ── De-duplicate: remove clips used in previous scenes ──────────
    fresh = [v for v in valid if v.get("id") not in _used_video_ids]
    if not fresh:
        # All clips used — reset for this query only
        fresh = valid

    # Pick deterministically per job/scene from top clips: varied across jobs, stable within one render.
    seed = int(hashlib.sha256(f"{job_id}:{scene_index}:{query}:{alt_query}".encode("utf-8")).hexdigest()[:8], 16)
    pick_pool = fresh[:8]
    chosen = pick_pool[seed % len(pick_pool)]
    _used_video_ids.add(chosen.get("id"))

    # ── Pick best resolution file ────────────────────────────────────
    video_files = chosen.get("video_files", [])
    # Try HD (1080p) first, then anything ≤ 10MP
    hd_files = [
        f for f in video_files
        if f.get("quality") in ("hd", "uhd") and
        ((f.get("width") or 0) * (f.get("height") or 0)) <= 8_294_400  # ≤4K
    ]
    if not hd_files:
        hd_files = [f for f in video_files if ((f.get("width") or 0) * (f.get("height") or 0)) <= 10_000_000]
    if not hd_files:
        hd_files = video_files

    # Sort by resolution descending, prefer 1920x1080 sweet spot
    hd_files.sort(
        key=lambda x: abs((x.get("width") or 0) * (x.get("height") or 0) - 1920 * 1080)
    )
    best = hd_files[0] if hd_files else None
    if not best:
        return ""

    download_url = best.get("link", "")
    if not download_url:
        return ""

    # ── Unique filename: based on video ID + scene_index ─────────────
    vid_id = chosen.get("id", "unknown")
    suffix = f"_{scene_index}" if scene_index >= 0 else ""
    filename = f"pexels_{vid_id}{suffix}_{orientation}.mp4"
    save_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(save_path):
        log.info(f"  ✅ Pexels cache hit: {filename}")
        return save_path

    # ── Download ─────────────────────────────────────────────────────
    log.info(f"  ⬇️  Downloading Pexels clip [{vid_id}] for '{query}' → {filename}")
    try:
        r = requests.get(download_url, stream=True, timeout=60)
        r.raise_for_status()
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
        log.info(f"  ✅ Saved: {filename} ({os.path.getsize(save_path) // 1024}KB)")
        return save_path
    except Exception as e:
        log.error(f"  Pexels download failed for '{query}': {e}")
        return ""


def reset_used_ids():
    """Call at start of each video job to allow clips to be reused across jobs."""
    global _used_video_ids
    _used_video_ids = set()
