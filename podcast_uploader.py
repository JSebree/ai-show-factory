# podcast_uploader.py

import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set in the environment")

    # ← version-1 API endpoint (token in querystring)
    url = f"https://www.buzzsprout.com/api/{buzz_id}/episodes.json?api_token={buzz_key}"

    with open(mp3_path, "rb") as audio_file:
        response = requests.post(
            url,
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    # Buzzsprout responds 201 on success
    if response.status_code != 201:
        # print the first bit of their JSON error payload
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
