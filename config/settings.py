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
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "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")

# ─── YOUTUBE DATA API v3 ─────────────────────────────────
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyAe36ZHNKd6vV-vGeI4Qk3m-obdCN4mP7s")
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "config/client_secrets.json")

# ─── GOOGLE CUSTOM SEARCH API ────────────────────────────
GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY", "AIzaSyAe36ZHNKd6vV-vGeI4Qk3m-obdCN4mP7s")
GOOGLE_SEARCH_ENGINE_ID = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "56147179e87e648f7")

# ─── ELEVENLABS (Premium TTS) ────────────────────────────
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_b00fac47a3960642fbd00a014066d0a78b10cc681dcf4f74")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "NFG5qt843uXKj4pFvR7C") # Host A (Adam)
ELEVENLABS_VOICE_ID_2 = os.getenv("ELEVENLABS_VOICE_ID_2", "G0yjIg3xY8gEJZkHpjVm") # Host B

# ─── TTS SETTINGS ──────────────────────────────────────────
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "playht") # options: playht, elevenlabs, openai, edge
EDGE_VOICE_A = "en-US-AndrewNeural"
EDGE_VOICE_B = "en-US-EmmaNeural"
OPENAI_VOICE_A = "onyx" # Deep
OPENAI_VOICE_B = "nova" # Engaging

# ─── PLAYHT (Ultra-realistic TTS) ────────────────────────
PLAYHT_USER_ID = os.getenv("PLAYHT_USER_ID", "")
PLAYHT_API_KEY = os.getenv("PLAYHT_API_KEY", "")
PLAYHT_VOICE_ID = os.getenv("PLAYHT_VOICE_ID", "s3://voice-cloning-zero-shot/d9ff78ba-d016-47f6-b0ef-dd630f59414e/female-cs/manifest.json") # Default Host A (Female)
PLAYHT_VOICE_ID_2 = os.getenv("PLAYHT_VOICE_ID_2", "s3://voice-cloning-zero-shot/775ae416-49bb-4fb6-bd45-740f205d20a1/jason/manifest.json") # Default Host B (Male)

# ─── IMAGE/VIDEO GENERATION (FAL.AI) ─────────────────────
FAL_API_KEY = os.getenv("FAL_API_KEY", "80820a4b-404e-4571-821a-b44efebfebb6:e1cc228267b3a2b2275b04e932ad6319")
USE_AI_VIDEO_BROLL = True # Set to True to generate actual AI Video clips instead of static images

# ─── STOCK FOOTAGE (Pexels) ─────────────────────────────
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "OZcJQVMuHqL63ZfWUPqNsSAjq8yDLiJnHJOZ3qSctirWKdL4ls53Co5N")

# ─── NOTIFICATIONS (WhatsApp via CallmeBot) ──────────────
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY", "")

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
SCRIPT_WORDS    = 1300       # ~8-9 minute video to ensure at least 6-7 mins minimum

# Google Trends geo (US, IN, GB, etc.)
TRENDS_GEO = "US"

# ─── YOUTUBE UPLOAD SETTINGS ─────────────────────────────
CATEGORY_ID    = "28"        # 28 = Science & Technology
PRIVACY_STATUS = "public"    # public | private | unlisted
TAGS_EXTRA     = ["AI", "artificial intelligence", "tech", "2025", "ChatGPT",
                   "machine learning", "deep learning", "future of AI"]
DEFAULT_LANGUAGE = "en"

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
