import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set in the environment")

    # 👇 Hit the real API endpoint (note the .json)
    url = f"https://api.buzzsprout.com/v2/podcasts/{buzz_id}/episodes.json"

    headers = {
        "Authorization": f"Token token={buzz_key}",
        "User-Agent":    "ai-show-factory/1.0",
        "Accept":        "application/json",
    }

    with open(mp3_path, "rb") as audio_file:
        response = requests.post(
            url,
            headers=headers,
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    # 201 means “Created” – anything else we’ll print so you can see the real JSON
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
