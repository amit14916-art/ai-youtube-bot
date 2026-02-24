import requests
from config.settings import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
headers = {
    "xi-api-key": ELEVENLABS_API_KEY,
    "Content-Type": "application/json",
}
payload = {
    "text": "This is a test of the ElevenLabs API.",
    "model_id": "eleven_turbo_v2",
}

response = requests.post(url, headers=headers, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response snippet: {response.text[:200]}")
