# 🔑 API Keys Setup Guide

Your bot is ready but **needs API keys** to run. Here's how to get them:

## ✅ What You Already Have

- ✅ YouTube OAuth: `config/client_secrets.json` (ready)
- ✅ All Python packages installed
- ✅ All code and dependencies

## ❌ What's Missing

### 1. **GROQ API Key** (Primary LLM - FREE)
**Status:** ❌ MISSING - This is why uploads fail

- Go to: https://console.groq.com/keys
- Copy your API key
- **Windows:** Run this in PowerShell:
  ```powershell
  [System.Environment]::SetEnvironmentVariable("GROQ_API_KEY", "your-key-here", "User")
  ```
  Then restart PowerShell.

- **Or create `.env` file** in project root:
  ```
  GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxx
  YOUTUBE_API_KEY=your-key-here
  GEMINI_API_KEY=your-key-here
  ```

### 2. **YOUTUBE API Key** (YouTube Search - Optional but recommended)
**Status:** ❌ MISSING - Search fails with 403 error

- Go to: https://console.cloud.google.com/
- Enable YouTube Data API v3
- Create an API Key (not OAuth)
- Set it: `YOUTUBE_API_KEY=AIza...`

### 3. **GEMINI API Key** (Fallback LLM - FREE)
**Status:** ❌ MISSING - Fallback if Groq fails

- Go to: https://aistudio.google.com/app/apikeys
- Create a free API key
- Set it: `GEMINI_API_KEY=AIza...`

---

## 🚀 Quick Setup (Windows PowerShell)

```powershell
# 1. Set environment variables (persistent across restarts)
[System.Environment]::SetEnvironmentVariable("GROQ_API_KEY", "gsk_your_key_here", "User")
[System.Environment]::SetEnvironmentVariable("YOUTUBE_API_KEY", "AIza_your_key_here", "User")
[System.Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "AIza_your_key_here", "User")

# 2. Restart PowerShell or reload environment
$env:GROQ_API_KEY = "gsk_your_key_here"
$env:YOUTUBE_API_KEY = "AIza_your_key_here"
$env:GEMINI_API_KEY = "AIza_your_key_here"

# 3. Test the bot
cd c:\Users\user\Downloads\ai-youtube-bot-main\ai-youtube-bot-main
python main.py --dry-run
```

---

## ✅ YouTube OAuth (Already Done)

Your `config/client_secrets.json` is already configured. The first upload will:
1. Open a browser window
2. Ask you to log in with your YouTube account
3. Authorize the app
4. Save `config/token.json` (auto-generated)

---

## 📋 Checklist Before Running

- [ ] Set GROQ_API_KEY
- [ ] Set YOUTUBE_API_KEY  
- [ ] Set GEMINI_API_KEY
- [ ] Run: `python main.py --dry-run`
- [ ] Verify video in `output/` folder
- [ ] Run: `python main.py` (will open browser for YouTube auth)
- [ ] Check YouTube channel for uploaded video

---

## 🆘 Troubleshooting

**Q: "All LLM providers failed"**
- A: Set at least GROQ_API_KEY or GEMINI_API_KEY

**Q: "YouTube search error 403"**
- A: Set YOUTUBE_API_KEY

**Q: "Token error" during upload**
- A: Run `python main.py` once (opens browser for auth)

**Q: Environment variable not working**
- A: Restart PowerShell after setting it
