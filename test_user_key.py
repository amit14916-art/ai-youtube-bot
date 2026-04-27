import requests

url = "https://api.elevenlabs.io/v1/user"
headers = {
    "xi-api-key": "OZcJQVMuHqL63ZfWUPqNsSAjq8yDLiJnHJOZ3qSctirWKdL4ls53Co5N"
}

response = requests.get(url, headers=headers)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
