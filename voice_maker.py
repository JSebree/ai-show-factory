import os
import sys
import requests

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def tts(text: str, out_path: str, voice_id: str = None):
    """
    Generate TTS audio from ElevenLabs and save it to `out_path`.
    Requires ELEVEN_KEY and ELEVEN_VOICE_ID in the environment.
    """
    # Load credentials
    api_key = os.getenv("ELEVEN_KEY")
    if not api_key:
        raise RuntimeError("ELEVEN_KEY not set in environment")

    if voice_id is None:
        voice_id = os.getenv("ELEVEN_VOICE_ID")
    if not voice_id:
        raise RuntimeError("ELEVEN_VOICE_ID not set in environment")

    # Build request
    url = ELEVEN_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",              # ask explicitly for MP3
        "User-Agent": "ai-show-factory/1.0"   # plain ASCII
    }
    payload = {
        "model_id": "eleven_turbo_v2",
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 1},
        "voice_format": "mp3"                # ensure MP3 output
    }

    # Call the API
    response = requests.post(url, json=payload, headers=headers, stream=True)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        # Dump the first bit of the error body for debugging
        body = response.text[:500]
        raise RuntimeError(f"TTS API returned {response.status_code}: {body}") from e

    # Verify content type
    ct = response.headers.get("Content-Type", "")
    if "audio" not in ct:
        raise RuntimeError(f"Expected audio, got {ct!r}: {response.text[:200]}")

    # Write the MP3 file
    with open(out_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            f.write(chunk)
