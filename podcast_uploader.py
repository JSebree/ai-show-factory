import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    """
    Upload an MP3 to Buzzsprout’s v2 API using browser-like headers
    to bypass Cloudflare’s JS challenge.

    Expects these env vars to be set:
      • BUZZ_ID  — your numeric podcast ID (e.g. "2489052")
      • BUZZ_KEY — your Buzzsprout API token
    """

    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("Environment variables BUZZ_ID and BUZZ_KEY must be set")

    # Real v2 endpoint (with .json)  
    url = f"https://api.buzzsprout.com/v2/podcasts/{buzz_id}/episodes.json"

    # Browser-like headers
    headers = {
        "Authorization":   f"Token token={buzz_key}",
        "User-Agent":      (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer":         "https://www.buzzsprout.com/",
        "Origin":          "https://www.buzzsprout.com",
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # POST the MP3 file
    with open(mp3_path, "rb") as audio_file:
        response = requests.post(
            url,
            headers=headers,
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    # Expect 201 Created
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
