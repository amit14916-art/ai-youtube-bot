# AI YouTube Automation Bot — Dockerfile
# Optimized for high-speed cloud rendering (FFmpeg + Python 3.11)

FROM python:3.11-slim

# 1. Install system dependencies (FFmpeg and Fonts are critical)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    fonts-noto-cjk \
    fonts-liberation \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# 2. Set working directory
WORKDIR /app

# 3. Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of the code
COPY . .

# 5. Environment variables (can be overridden at runtime)
# We prioritize ENV vars, but keep defaults from settings.py
ENV PYTHONUNBUFFERED=1
ENV FONT_PATH="/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# 6. Create output directory if it doesn't exist
RUN mkdir -p output assets

# 7. Start the bot on schedule
CMD ["python", "main.py", "--schedule"]
