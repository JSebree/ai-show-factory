import os, requests

def upload(mp3_path, title, description):
    """
    Upload an MP3 to Buzzsprout v2 API.
    Expects BUZZ_ID and BUZZ_KEY in the environment.
    """
    buzz_id = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID or BUZZ_KEY not set")

    url = f"https://api.buzzsprout.com/v2/{buzz_id}/episodes"
    headers = {
        "Authorization": f"Token token={buzz_key}",
        "User-Agent":    "ai-show-factory/1.0",
        "Accept":        "application/json",
    }

    with open(mp3_path, "rb") as audio:
        r = requests.post(
            url,
            headers=headers,
            files={"audio_file": audio},
            data={"title": title, "description": description},
        )

    # debug on failure
    if r.status_code != 201:
        print("Buzzsprout returned:", r.status_code, r.text[:500])
        r.raise_for_status()

    return r.json()
