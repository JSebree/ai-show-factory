# podcast_uploader.py

import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    """
    Upload an MP3 file to Buzzsprout via their dedicated uploads subdomain.

    Requires:
      • BUZZ_ID   (your numeric podcast ID, e.g. "2489052")
      • BUZZ_KEY  (your Buzzsprout API token)

    Returns the JSON response on success (HTTP 201).
    Raises an exception with details on failure.
    """
    # 1) Read and validate env vars
    BUZZ_ID = os.getenv("BUZZ_ID")
    BUZZ_KEY = os.getenv("BUZZ_KEY")
    if not BUZZ_ID:
        raise RuntimeError("Environment variable BUZZ_ID is not set")
    if not BUZZ_KEY:
        raise RuntimeError("Environment variable BUZZ_KEY is not set")

    # 2) Build the upload URL
    url = f"https://api.buzzsprout.com/v2/{BUZZ_ID}/episodes"

    # 3) Prepare headers
    headers = {
        "Authorization": f"Token token={BUZZ_KEY}",
        "User-Agent":    "ai-show-factory/1.0",
        "Accept":        "application/json",
    }

    # 4) Perform the POST with the MP3 file
    with open(mp3_path, "rb") as audio_file:
        response = requests.post(
            url,
            headers=headers,
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    # 5) Check for success (201 Created) and debug if not
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    # 6) Return the parsed JSON response
    return response.json()
