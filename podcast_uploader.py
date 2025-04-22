import requests, os, json

BUZZ_URL = "https://www.buzzsprout.com/api/1234567/episodes.json"  # replace feed ID!

def upload(mp3_path, title, description):
    with open(mp3_path, "rb") as audio:
        r = requests.post(
            BUZZ_URL,
            headers={"Authorization": f"Token token={os.getenv('BUZZ_KEY')}"},
            files={"audio_file": audio},
            data={"title": title, "description": description}
        )
    r.raise_for_status()
    return r.json()
