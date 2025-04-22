import os
import sys
import requests

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def tts(text: str, out_path: str, voice_id = os.getenv("ELEVEN_VOICE_ID")):
    # Build headers and body
    headers = {
        "xi-api-key": os.getenv("ELEVEN_KEY"),
        "Content-Type": "application/json",
    }
    payload = {
        "model_id": "eleven_turbo_v2",
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 1},
        "voice_format": "wav"
    }

    # Call the API
    r = requests.post(
        ELEVEN_URL.format(voice_id=voice_id),
        json=payload,
        stream=True,
        headers=headers,
    )
    # Fail fast on HTTP errors
    r.raise_for_status()

    # Verify it's audio, not an error HTML/JSON blob
    content_type = r.headers.get("Content-Type", "")
    if "audio" not in content_type:
        raise RuntimeError(f"TTS failed, server said: {r.text[:200]}")

    # Write out the binary audio
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)
