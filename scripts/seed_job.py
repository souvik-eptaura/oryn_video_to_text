import os
import requests

API_URL = os.getenv("API_URL", "http://localhost")
TOKEN = os.getenv("TOKEN", "")

payload = {
    "orgId": "ORG123",
    "source": "instagram",
    "reelUrl": "https://www.instagram.com/reel/XXXX/",
    "postedAt": None,
    "metadata": {"handle": "@somehandle"},
}

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

resp = requests.post(f"{API_URL}/v1/transcribe", json=payload, headers=headers, timeout=30)
print(resp.status_code, resp.text)
