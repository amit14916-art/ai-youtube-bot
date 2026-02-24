import requests
import logging
import os

log = logging.getLogger(__name__)

def send_whatsapp_notification(url: str, title: str):
    """
    Sends a WhatsApp message with the video link using CallmeBot API.
    """
    phone = os.getenv("WHATSAPP_PHONE")
    api_key = os.getenv("WHATSAPP_API_KEY")

    if not phone or not api_key:
        log.warning("WhatsApp credentials missing. Skipping notification.")
        return

    message = f"🚀 *AI YouTube Bot Update*\n\n✅ *New Video Uploaded!*\n\n*Title:* {title}\n*Link:* {url}\n\n_Bot is working autonomously!_ 🤖"
    
    # CallmeBot API Endpoint
    # format: https://api.callmebot.com/whatsapp.php?phone=[phone]&text=[text]&apikey=[apikey]
    endpoint = "https://api.callmebot.com/whatsapp.php"
    params = {
        "phone": phone,
        "text": message,
        "apikey": api_key
    }

    try:
        response = requests.get(endpoint, params=params)
        if response.status_code == 200:
            log.info("WhatsApp notification sent successfully! ✓")
        else:
            log.warning(f"WhatsApp notification failed: {response.text}")
    except Exception as e:
        log.error(f"Error sending WhatsApp notification: {e}")
