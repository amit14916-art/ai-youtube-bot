"""
=============================================================
  AI Faceless YouTube Channel Automation Bot - Settings
=============================================================
Fill in your API keys and preferences below before running.
"""
import os


# ─── LLM SETTINGS (Open Source / Claude) ─────────────────
LLM_PROVIDER      = os.getenv("LLM_PROVIDER", "groq") 
GROQ_API_KEY      = os.getenv("GROQ_API_KEY", "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")
GROQ_MODEL        = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY")

# ─── YOUTUBE DATA API v3 ─────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyAe36ZHNKd6vV-vGeI4Qk3m-obdCN4mP7s")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "config/client_secrets.json")

# ─── GOOGLE CUSTOM SEARCH API ────────────────────────────
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "AIzaSyAe36ZHNKd6vV-vGeI4Qk3m-obdCN4mP7s")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "56147179e87e648f7")

# ─── ELEVENLABS (Premium TTS) ────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_b00fac47a3960642fbd00a014066d0a78b10cc681dcf4f74")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # Host A (Rachel)
ELEVENLABS_VOICE_ID_2 = os.getenv("ELEVENLABS_VOICE_ID_2", "G0yjIg3xY8gEJZkHpjVm") # Host B

# ─── VIDEO SETTINGS ──────────────────────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
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
NICHE           = "AGENTIC AI WORLD"
RESEARCH_TOPICS = 5          # Number of trending topics to research
SCRIPT_WORDS    = 1100       # ~6-7 minute video (avg 150-160 words per min)

# Google Trends geo (US, IN, GB, etc.)
TRENDS_GEO = "US"

# ─── YOUTUBE UPLOAD SETTINGS ─────────────────────────────
CATEGORY_ID    = "28"        # 28 = Science & Technology
PRIVACY_STATUS = "private"    # public | private | unlisted
TAGS_EXTRA     = ["AI", "artificial intelligence", "tech", "2025", "ChatGPT",
                   "machine learning", "deep learning", "future of AI"]
DEFAULT_LANGUAGE = "en"

# ─── SCHEDULE ────────────────────────────────────────────
# Upload time daily (24-hr format, system local time)
# 1st Video: 9:00 AM
UPLOAD_HOUR   = 9
UPLOAD_MINUTE = 0

# (We will modify main.py to handle 3 uploads per day)
DAILY_UPLOADS = 3
UPLOAD_TIMES  = ["09:00", "15:00", "21:00"]

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
