# podcast_uploader.py

import os
import cloudscraper

def upload(mp3_path: str, title: str, description: str) -> dict:
    """
    Upload an MP3 to Buzzsprout by using cloudscraper to bypass
    the Cloudflare JS challenge.
    Requires BUZZ_ID and BUZZ_KEY in the environment.
    """

    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set in the environment")

    # The documented v2 endpoint with .json suffix
    url = f"https://api.buzzsprout.com/v2/podcasts/{buzz_id}/episodes.json"

    # Create a scraper that can solve CF’s JS challenge
    scraper = cloudscraper.create_scraper(
        browser={
            "custom": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
    )

    with open(mp3_path, "rb") as audio_file:
        response = scraper.post(
            url,
            headers={
                "Authorization": f"Token token={buzz_key}",
                "Accept":        "application/json",
            },
            files={"audio_file": audio_file},
            data={"title": title, "description": description},
        )

    # Buzzsprout returns 201 on success
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
