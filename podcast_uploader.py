# podcast_uploader.py

import os
import cloudscraper

def upload(mp3_path: str, title: str, description: str) -> dict:
    """
    Upload an MP3 to Buzzsprout’s v2 API, clearing the Cloudflare challenge
    by using cloudscraper under the hood.

    Requires BUZZ_ID (podcast numeric ID) and BUZZ_KEY (API token)
    to be set as environment variables.
    """
    buzz_id  = os.getenv("BUZZ_ID")
    buzz_key = os.getenv("BUZZ_KEY")
    if not buzz_id or not buzz_key:
        raise RuntimeError("BUZZ_ID and BUZZ_KEY must be set in the environment")

    # The documented v2 JSON endpoint
    url = f"https://api.buzzsprout.com/v2/podcasts/{buzz_id}/episodes.json"

    # Create a CF‐bypassing scraper with a real browser UA
    scraper = cloudscraper.create_scraper(
        browser={
            "custom": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
    )

    # Do the POST with the MP3
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

    # 201 Created → success; otherwise print and raise
    if response.status_code != 201:
        print("Buzzsprout returned:", response.status_code, response.text[:500])
        response.raise_for_status()

    return response.json()
