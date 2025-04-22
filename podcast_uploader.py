import requests, os, json

BUZZ_URL = "https://api.buzzsprout.com/api/2489052/episodes.json"  # replace feed ID!

def upload(mp3_path, title, description):
    with open(mp3_path, "rb") as audio:
        r = requests.post(
            BUZZ_URL,
            headers={
                # your Buzzsprout API token
                "Authorization": f"Token token={os.getenv('BUZZ_KEY')}",
                # Cloudflare won’t challenge if you present a UA
                "User-Agent":    "ai-show-factory/1.0",
                # explicitly ask for JSON, not HTML
                "Accept":        "application/json",
            },
            files={"audio_file": audio},
            data={"title": title, "description": description},
        )

        # debug print if it still fails
        if r.status_code != 201:
            print("Buzzsprout returned:", r.status_code, r.text[:500])
            r.raise_for_status()
        return r.json()


