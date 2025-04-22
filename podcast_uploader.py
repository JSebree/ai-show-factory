import os
import requests

def upload(mp3_path: str, title: str, description: str) -> dict:
    """
    Upload an MP3 file to Buzzsprout via their uploads subdomain.
    
    Expects the following environment variables to be set:
      - BUZZ_ID   : your numeric podcast ID (e.g. "2489052")
      - BUZZ_KEY  : your Buzzsprout API token

    Returns the JSON response from Buzzsprout on success.
    Raises an HTTPError with details on failure.
    """
    buzz_id = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set in the environment")

    url = f"https://uploads.buzzsprout.com/v2/{BUZZ_ID}/episodes"
    headers = {
        "Authorization": f"Token token={BUZZ_KEY}",
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

    # If it’s not 201 Created, print and raise
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
