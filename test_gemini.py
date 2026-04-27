from google import genai as google_genai
from config.settings import GEMINI_API_KEY

client = google_genai.Client(api_key=GEMINI_API_KEY)

# Try different models
models_to_try = ["gemini-2.0-flash-lite", "gemini-flash-latest", "gemini-2.0-flash-001"]

for model in models_to_try:
    try:
        response = client.models.generate_content(
            model=model,
            contents='Reply OK',
        )
        print(f'SUCCESS with model: {model}')
        print('Response:', response.text[:100])
        break
    except Exception as e:
        print(f'FAILED {model}: {str(e)[:120]}')
