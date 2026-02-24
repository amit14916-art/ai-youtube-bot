import requests
from config.settings import ELEVENLABS_API_KEY

url = "https://api.elevenlabs.io/v1/user"
headers = {
    "xi-api-key": ELEVENLABS_API_KEY
}

response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
