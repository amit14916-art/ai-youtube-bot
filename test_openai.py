from openai import OpenAI
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
from config.settings import OPENAI_API_KEY

def test_openai_tts():
    print(f"Testing OpenAI API Key: {OPENAI_API_KEY[:10]}...")
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input="This is a test of the OpenAI text to speech system for our YouTube bot."
        )
        response.stream_to_file("test_voice_openai.mp3")
        print("Success! Audio saved to test_voice_openai.mp3")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_openai_tts()
