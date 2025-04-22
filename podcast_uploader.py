import requests, os, json

BUZZ_URL = "https://www.buzzsprout.com/api/2489052/episodes.json"  # replace feed ID!

def upload(mp3_path, title, description):
    with open(mp3_path, "rb") as audio:
        r = requests.post(
            BUZZ_URL,
            headers={
                "Authorization": f"Token token={os.getenv('BUZZ_KEY')}",
                "User-Agent":    "ai-show-factory/1.0"       # <- important
            },
            files={"audio_file": audio},
            data={"title": title, "description": description}
        )

        # DEBUG: dump Buzzsprout’s error response if it’s not a 201 CREATED
        if r.status_code != 201:
            print("Buzzsprout returned:", r.status_code, r.text)
            r.raise_for_status()

        return r.json()

