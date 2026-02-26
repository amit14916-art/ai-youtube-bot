"""
Script to send the latest generated video via Gmail.
Uses Gmail SMTP with App Password.
"""
import os
import smtplib
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ─── CONFIG ────────────────────────────────────────────────
TO_EMAIL = "amit14916@gmail.com"
FROM_EMAIL = os.getenv("GMAIL_SENDER", "")      # Your Gmail address
APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")  # Gmail App Password (16 chars)

# ─── FIND LATEST VIDEO ─────────────────────────────────────
output_dir = os.path.join(os.path.dirname(__file__), "output")
shorts_files = sorted(glob.glob(os.path.join(output_dir, "*_shorts.mp4")), reverse=True)
long_files = sorted(glob.glob(os.path.join(output_dir, "*_video.mp4")), reverse=True)

video_path = shorts_files[0] if shorts_files else (long_files[0] if long_files else None)

if not video_path:
    print("❌ No video found in output/ folder!")
    exit(1)

print(f"📹 Sending: {os.path.basename(video_path)}")
file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
print(f"📦 File size: {file_size_mb:.1f} MB")

if not FROM_EMAIL or not APP_PASSWORD:
    print()
    print("❌ Gmail credentials not set!")
    print("Set these environment variables first:")
    print("  $env:GMAIL_SENDER='youremail@gmail.com'")
    print("  $env:GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
    print()
    print("To create a Gmail App Password:")
    print("  1. Go to Google Account -> Security -> 2-Step Verification")
    print("  2. Scroll down to 'App passwords'")
    print("  3. Create an app password for 'Mail'")
    exit(1)

# ─── BUILD EMAIL ───────────────────────────────────────────
msg = MIMEMultipart()
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL
msg["Subject"] = f"🎬 AI YouTube Bot - New Video Ready: {os.path.basename(video_path)}"

body = f"""Hi!

Your AI YouTube Bot has successfully generated a new video!

📁 File: {os.path.basename(video_path)}
📦 Size: {file_size_mb:.1f} MB

The video has been generated using:
✅ Groq LLM - Script & Topic Research
✅ Groq Whisper - Word-by-Word Timestamps 
✅ Director Agent - Context-Aware B-Roll Selection
✅ Edge-TTS - High Quality Voiceover
✅ Remotion - Professional Video Rendering

Check your YouTube channel for uploads when the scheduler runs!

— AI YouTube Bot 🤖
"""

msg.attach(MIMEText(body, "plain"))

# Attach the video (only if under 25MB Gmail limit)
if file_size_mb < 24:
    with open(video_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(video_path)}"
        )
        msg.attach(part)
    print("✅ Video attached to email!")
else:
    msg.attach(MIMEText(f"\n⚠️ Video is {file_size_mb:.1f}MB (too large for Gmail). Please find it locally at:\n{video_path}", "plain"))
    print(f"⚠️ Video too large ({file_size_mb:.1f}MB) — sending path info instead.")

# ─── SEND ──────────────────────────────────────────────────
try:
    print("📬 Connecting to Gmail SMTP...")
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM_EMAIL, APP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    print(f"✅ Email sent successfully to {TO_EMAIL}!")
except Exception as e:
    print(f"❌ Failed to send email: {e}")
