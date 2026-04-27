#!/bin/bash

# start.sh — Start script for Railway deployment
# This script runs both the API server and the Bot scheduler.

echo "🚀 Starting AI YouTube Bot Automation Suite..."

# 1. Start the FastAPI backend on port 8000 (matched to Railway settings)
echo "🌐 Starting Dashboard API on port 8000..."
uvicorn webapp.api:app --host 0.0.0.0 --port 8000 &

# 2. Start the Bot Scheduler in the foreground
echo "📅 Starting Daily Video Scheduler..."
python main.py --schedule
