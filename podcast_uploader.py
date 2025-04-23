import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set")

    # ← corrected here:
    url = f"https://api.buzzsprout.com/v2/podcasts/{buzz_id}/episodes"

    headers = {
        "Authorization": f"Token token={buzz_key}",
        "User-Agent":    "ai-show-factory/1.0",
        "Accept":        "application/json",
    }

    with open(mp3_path, "rb") as audio_file:
        r = requests.post(
            url,
            headers=headers,
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    if r.status_code != 201:
        print("Buzzsprout returned:", r.status_code, r.text[:500])
        r.raise_for_status()

    return r.json()
