#!/bin/bash
# ============================================================
# AI YouTube Bot - RunPod One-Shot Setup Script
# Just run this once and bot will start automatically
# ============================================================
set -e

echo "🚀 Starting AI YouTube Bot Setup on RunPod..."

# ── 1. System Dependencies ────────────────────────────────
echo "📦 Installing system packages..."
apt-get update -qq
apt-get install -y ffmpeg fonts-liberation fonts-open-sans git curl wget tmux > /dev/null 2>&1
echo "✅ System packages installed"

# ── 2. Node.js 20 ─────────────────────────────────────────
echo "📦 Installing Node.js 20..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
apt-get install -y nodejs > /dev/null 2>&1
echo "✅ Node.js $(node --version) installed"

# ── 3. Clone / Pull latest bot code ───────────────────────
echo "📥 Pulling latest bot code from GitHub..."
cd /workspace
if [ -d "ai-youtube-bot" ]; then
    cd ai-youtube-bot
    git pull origin main
else
    git clone https://github.com/amit14916-art/ai-youtube-bot.git
    cd ai-youtube-bot
fi
echo "✅ Code ready"

# ── 4. Python dependencies ────────────────────────────────
echo "📦 Installing Python packages..."
pip install -r requirements.txt -q
echo "✅ Python packages installed"

# ── 5. Remotion / Node dependencies ───────────────────────
echo "📦 Installing Remotion dependencies..."
cd remotion_app
npm install --prefer-offline > /dev/null 2>&1
cd ..
echo "✅ Remotion ready"

# ── 6. Write YouTube token from env var ───────────────────
echo "🔑 Writing YouTube token..."
mkdir -p config
if [ -n "$YOUTUBE_TOKEN_JSON" ]; then
    printf '%s' "$YOUTUBE_TOKEN_JSON" > config/token.json
    echo "✅ token.json written"
else
    echo "⚠️  YOUTUBE_TOKEN_JSON not set - Upload will fail!"
fi

# ── 7. Environment check ──────────────────────────────────
echo ""
echo "🔍 API Key Status:"
[ -n "$GROQ_API_KEY" ]             && echo "  ✅ GROQ_API_KEY set"        || echo "  ❌ GROQ_API_KEY missing"
[ -n "$OPENAI_API_KEY" ]           && echo "  ✅ OPENAI_API_KEY set"      || echo "  ⚠️  OPENAI_API_KEY missing (optional)"
[ -n "$PEXELS_API_KEY" ]           && echo "  ✅ PEXELS_API_KEY set"      || echo "  ❌ PEXELS_API_KEY missing"
[ -n "$YOUTUBE_API_KEY" ]          && echo "  ✅ YOUTUBE_API_KEY set"     || echo "  ❌ YOUTUBE_API_KEY missing"
[ -n "$ELEVENLABS_API_KEY" ]       && echo "  ✅ ELEVENLABS_API_KEY set"  || echo "  ⚠️  ELEVENLABS_API_KEY missing (optional)"
echo ""

# ── 8. Run one video immediately ─────────────────────────
echo "🎬 Starting bot to generate ONE video now..."
tmux new-session -d -s bot "cd /workspace/ai-youtube-bot && python main.py --long-only 2>&1 | tee /workspace/bot_run.log"
echo ""
echo "✅ Bot is running in tmux session 'bot'"
echo ""
echo "📺 To watch live logs:  tmux attach -t bot"
echo "📄 To read log file:    tail -f /workspace/bot_run.log"
echo ""
echo "⏳ Estimated time on RunPod: 10-15 minutes for full video"
echo "🔗 Video will auto-upload to YouTube when done"
