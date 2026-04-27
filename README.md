# 🤖 AI Faceless YouTube Channel Automation Bot

Fully automated pipeline that **researches trending AI topics → writes scripts → generates voiceover → builds faceless videos → uploads to YouTube daily.**

---

## 🗂️ Project Structure

```
ai_youtube_bot/
├── main.py                    # Entry point & scheduler
├── requirements.txt           # Python dependencies
├── config/
│   ├── settings.py            # ⚙️  ALL your API keys & settings go here
│   ├── client_secrets.json    # YouTube OAuth (you download this)
│   └── token.json             # Auto-generated after first auth
├── modules/
│   ├── researcher.py          # Google Trends + YouTube research + Claude AI
│   ├── audio_generator.py     # Text-to-Speech (ElevenLabs or gTTS)
│   └── video_creator.py       # Animated slides video builder
│   └── uploader.py            # YouTube upload & thumbnail
├── assets/
│   └── bgm.mp3                # (Optional) background music file
└── output/                    # Generated files saved here
```

---

## 🚀 Quick Setup (Step-by-Step)

### Step 1 — Install Python & Dependencies

```bash
# Requires Python 3.11+
pip install -r requirements.txt

# Also install ffmpeg (required by moviepy)
# Ubuntu/Debian:
sudo apt install ffmpeg
# macOS:
brew install ffmpeg
# Windows: download from https://ffmpeg.org/download.html
```

### Step 2 — Get Your API Keys

#### A. Anthropic (Claude AI) — REQUIRED
1. Go to https://console.anthropic.com/
2. Create an API key
3. Paste into `config/settings.py` → `ANTHROPIC_API_KEY`

#### B. YouTube Data API v3 — REQUIRED for upload
1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "YouTubeBot")
3. Enable **YouTube Data API v3**
4. Go to **Credentials** → Create **OAuth 2.0 Client ID**
   - Application type: **Desktop app**
5. Download the JSON → save as `config/client_secrets.json`
6. Also create an **API Key** and paste into `config/settings.py` → `YOUTUBE_API_KEY`

#### C. Google Custom Search — REQUIRED for research
1. Go to https://programmablesearchengine.google.com/
2. Create a search engine (search the whole web)
3. Get the **Search Engine ID**
4. Go to https://console.cloud.google.com/ → enable **Custom Search API**
5. Create an API key
6. Paste both into `config/settings.py`

#### D. ElevenLabs (Optional — better voice quality)
1. Go to https://elevenlabs.io/ and create a free account
2. Copy your API key from the profile page
3. Paste into `config/settings.py` → `ELEVENLABS_API_KEY`
> If left blank, the bot uses **gTTS** (Google TTS, free, decent quality)

### Step 3 — Configure Settings

Edit `config/settings.py`:
```python
NICHE = "Artificial Intelligence"   # Your channel niche
PRIVACY_STATUS = "private"          # Start with "private" to test!
UPLOAD_HOUR = 9                     # Daily upload time (9 AM)
SCRIPT_WORDS = 600                  # ~3-4 minute video
```

### Step 4 — Add Background Music (Optional)

Place any royalty-free MP3 file at `assets/bgm.mp3`.  
Good sources: **Pixabay Music**, **YouTube Audio Library**, **Free Music Archive**

### Step 5 — First Run (Test Mode)

```bash
# Dry run — generates everything but does NOT upload
python main.py --dry-run
```

Check the `output/` folder for:
- `*_content.json` — topic, SEO title, description, script
- `*_voice.mp3` — voiceover audio
- `*_video.mp4` — final video
- `*_thumbnail.jpg` — thumbnail image

### Step 6 — Authorize YouTube (First Upload Only)

```bash
python main.py
```

A browser window will open → log in with your YouTube channel account → click Allow.  
Token is saved to `config/token.json` — subsequent runs are fully automatic.

### Step 7 — Start Daily Schedule

```bash
# Runs immediately, then daily at the configured time
python main.py --schedule
```

To keep it running permanently on a server:
```bash
# Using nohup (Linux/Mac)
nohup python main.py --schedule > output/nohup.log 2>&1 &

# Or with PM2 (recommended)
npm install -g pm2
pm2 start "python main.py --schedule" --name youtube-bot
pm2 save && pm2 startup
```

---

## ⚙️ How It Works

```
DAILY PIPELINE
══════════════
① RESEARCH
   ├── Google Trends → top AI keywords (last 7 days)
   └── YouTube API  → most-viewed AI videos (last 7 days)

② AI CONTENT GENERATION (Claude Sonnet)
   ├── Picks the single best viral topic
   ├── Writes SEO-optimized title (70 chars)
   ├── Writes YouTube description (800-1000 chars + hashtags)
   ├── Writes full voiceover script (~600 words)
   └── Suggests thumbnail text

③ TEXT-TO-SPEECH
   ├── ElevenLabs (premium, natural) — if API key set
   └── gTTS (free fallback)

④ VIDEO CREATION
   ├── Animated gradient background
   ├── Text slides auto-synced to audio duration
   ├── Subtle zoom effects per slide
   ├── Optional background music (mixed under voiceover)
   └── Channel branding overlay

⑤ THUMBNAIL
   └── Auto-generated 1280×720 branded image

⑥ YOUTUBE UPLOAD
   ├── Video file (MP4, 1080p)
   ├── Custom thumbnail
   └── Title, description, tags, category — all set automatically
```

---

## 📊 Output Files (per run)

| File | Description |
|------|-------------|
| `YYYYMMDD_HHMMSS_content.json` | Full research + AI-generated content |
| `YYYYMMDD_HHMMSS_voice.mp3`    | Voiceover audio |
| `YYYYMMDD_HHMMSS_video.mp4`    | Final 1080p video |
| `YYYYMMDD_HHMMSS_thumbnail.jpg`| YouTube thumbnail |
| `YYYYMMDD_HHMMSS_result.json`  | Upload result + YouTube URL |
| `bot.log`                       | Full activity log |

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| ffmpeg not found | Install ffmpeg (see Step 1) |
| YouTube quota exceeded | YouTube API has 10,000 units/day free. Uploads use ~1600 units each. You get ~6 free uploads/day. |
| Font not found | Edit `FONT_PATH` in settings.py to a font file on your system |
| Audio too slow | Increase `playback_speed` in `audio_generator.py` line with `speedup()` |
| Video render slow | Reduce `VIDEO_WIDTH`/`VIDEO_HEIGHT` to 1280×720 in settings |

---

## 🎯 Tips for Channel Growth

- Set `PRIVACY_STATUS = "private"` during testing, switch to `"public"` when happy
- Add proper background music (calm lo-fi or cinematic) — big difference in watch time
- Run the bot for 2-4 weeks consistently before judging results
- Check `output/*_content.json` daily to see what topics Claude picks — tweak `NICHE` if needed
- Upgrade to ElevenLabs for noticeably better audio quality

---

## ⚠️ Important Notes

- **YouTube ToS**: Automated uploads are allowed under YouTube's API Terms of Service as long as content is original and valuable. Spam/low-quality content can result in channel termination.
- **API Costs**: Claude Sonnet ~$0.01/video script. ElevenLabs free tier = 10,000 chars/month (~3-4 videos). Google APIs have generous free tiers.
- **Content Quality**: The bot generates real educational content, not spam. Claude writes 600-word scripts with research-backed information.
