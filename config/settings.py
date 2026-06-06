"""
=============================================================
  AI Faceless YouTube Channel Automation Bot - Settings
=============================================================
Fill in your API keys and preferences below before running.
"""
import os


# ─── LLM SETTINGS ────────────────────────────────────────
# Primary: Groq (FREE, fast, no quota issues)
# Fallback: Gemini (FREE, set GEMINI_API_KEY in GitHub Secrets)
LLM_PROVIDER      = os.getenv("LLM_PROVIDER") or "groq"
GROQ_API_KEY      = os.getenv("GROQ_API_KEY") or ""   # ✅ Set GROQ_API_KEY in GitHub Secrets!
GROQ_MODEL        = os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile"

# Fallback providers
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY") or ""
GEMINI_MODEL      = os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY") or ""
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY") or ""

# ─── YOUTUBE DATA API v3 ─────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY") or ""
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE") or "config/client_secrets.json"

# ─── GOOGLE CUSTOM SEARCH API ────────────────────────────
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY") or ""
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID") or ""

# ─── ELEVENLABS (Premium TTS) ────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or ""
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") or "NFG5qt843uXKj4pFvR7C" # Host A (Adam)
ELEVENLABS_VOICE_ID_2 = os.getenv("ELEVENLABS_VOICE_ID_2") or "G0yjIg3xY8gEJZkHpjVm" # Host B

# ─── TTS SETTINGS ──────────────────────────────────────────
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge") # options: playht, elevenlabs, openai, edge
EDGE_VOICE_A = "en-US-AndrewNeural"
EDGE_VOICE_B = "en-US-EmmaNeural"
OPENAI_VOICE_A = "onyx" # Deep
OPENAI_VOICE_B = "nova" # Engaging

# ─── PLAYHT (Ultra-realistic TTS) ────────────────────────
PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID") or ""
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY") or ""
PLAYHT_VOICE_ID = os.getenv("PLAYHT_VOICE_ID") or "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json" # Default Host A (Female)
PLAYHT_VOICE_ID_2 = os.getenv("PLAYHT_VOICE_ID_2") or "s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jason/manifest.json" # Default Host B (Male)

# ─── IMAGE/VIDEO GENERATION (FAL.AI) ─────────────────────
FAL_API_KEY = os.getenv("FAL_API_KEY") or ""  # Fal.ai removed — using Pexels + Pollinations only
USE_AI_VIDEO_BROLL = False

# ─── STOCK FOOTAGE ───────────────────────────────────────
# Pexels (primary) — free, high quality
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY") or ""

# Pixabay (secondary) — free, 3M+ videos, great variety
# Get your free key at: https://pixabay.com/api/docs/
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY") or ""

# ─── NOTIFICATIONS (WhatsApp via CallmeBot) ──────────────
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE") or ""
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY") or ""

# ─── VIDEO SETTINGS ──────────────────────────────────────
VIDEO_WIDTH  = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS    = 24
VIDEO_DURATION_PER_SLIDE = 6
BACKGROUND_MUSIC_VOLUME  = 0.08

# Font path — dynamic for Windows/Linux
FONT_PATH = os.getenv("FONT_PATH")
if not FONT_PATH:
    if os.name == 'nt': # Windows
        FONT_PATH = "C:\\Windows\\Fonts\\arialbd.ttf"
    else: # Linux/Docker
        FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# ─── RESEARCH SETTINGS ───────────────────────────────────
NICHE           = "artificial intelligence"   # YouTube search query (not channel name)
RESEARCH_TOPICS = 8          # Number of trending topics to research
SCRIPT_WORDS    = 1400       # ~8-10 min video — sweet spot for YouTube watch time

# Google Trends geo (US, IN, GB, etc.)
TRENDS_GEO = "US"

# ─── YOUTUBE UPLOAD SETTINGS ─────────────────────────────
CATEGORY_ID    = "28"        # 28 = Science & Technology
PRIVACY_STATUS = "public"    # public | private | unlisted
TAGS_EXTRA     = [
    "AI", "artificial intelligence", "AI tools 2025", "AI tutorial",
    "AI explained", "machine learning", "deep learning", "ChatGPT",
    "AI news", "future of AI", "AI automation", "AI for beginners",
    "OpenAI", "Google AI", "AI technology", "AI trends",
    "tech news", "AI productivity", "AI content creation", "AI agents",
]
DEFAULT_LANGUAGE = "en"

# ─── FACEBOOK UPLOAD SETTINGS ────────────────────────────
ENABLE_FACEBOOK_UPLOAD  = (os.getenv("ENABLE_FACEBOOK_UPLOAD", "False").lower() == "true")
FB_PAGE_ACCESS_TOKEN    = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
FB_PAGE_ID              = os.getenv("FB_PAGE_ID", "")

# ─── INSTAGRAM UPLOAD SETTINGS ───────────────────────────
ENABLE_INSTAGRAM_UPLOAD = (os.getenv("ENABLE_INSTAGRAM_UPLOAD", "False").lower() == "true")
IG_USER_ID              = os.getenv("IG_USER_ID", "")

# ─── LINKEDIN UPLOAD SETTINGS ────────────────────────────
ENABLE_LINKEDIN_UPLOAD  = (os.getenv("ENABLE_LINKEDIN_UPLOAD", "False").lower() == "true")
LINKEDIN_ACCESS_TOKEN   = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_OWNER_URN      = os.getenv("LINKEDIN_OWNER_URN", "") # e.g. urn:li:person:XXXX or urn:li:organization:XXXX

# ─── SCHEDULE ────────────────────────────────────────────
# Upload time daily (24-hr format, system local time)
# 1st Video: 9:00 AM
UPLOAD_HOUR   = 9
UPLOAD_MINUTE = 0

# 2 times for Long
LONG_ONLY_TIMES = ["09:00", "19:00"]

# 1 more Short only (Total 1 more Short = 3 Shorts total daily)
SHORTS_ONLY_TIMES = ["14:00"]

# ─── OUTPUT PATHS ────────────────────────────────────────
OUTPUT_DIR      = "output"
ASSETS_DIR      = "assets"
LOG_FILE        = "output/bot.log"

# ─── FFMPEG DETECTION ────────────────────────────────────
import os, subprocess
FFMPEG_PATH = "ffmpeg"  # default

try:
    import imageio_ffmpeg
    path = imageio_ffmpeg.get_ffmpeg_exe()
    if path and os.path.exists(path):
        FFMPEG_PATH = path
except ImportError:
    pass
