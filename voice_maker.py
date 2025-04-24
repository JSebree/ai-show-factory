import os
import sys
import requests

# Load your ElevenLabs API key from the environment
ELEVEN_API_KEY = os.getenv("ELEVEN_KEY")
if not ELEVEN_API_KEY:
    raise RuntimeError("Environment variable ELEVEN_KEY is not set.")


def tts(text: str, out_path: str, voice_id: str) -> None:
    """
    Synthesize `text` to speech using ElevenLabs and write the output to `out_path`.

    :param text: The text to synthesize.
    :param out_path: Path to write the MP3 file.
    :param voice_id: ElevenLabs voice ID to use.
    :raises RuntimeError: On HTTP errors or invalid responses.
    """
    if not voice_id:
        raise RuntimeError("voice_id must be provided to TTS function.")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_API_KEY,
    }
    payload = {"text": text}

    # Stream the response so we can write it incrementally
    response = requests.post(url, json=payload, headers=headers, stream=True)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        # Capture the body for debugging
        body = response.text[:500]
        raise RuntimeError(
            f"TTS API error {response.status_code}: {body}"
        ) from exc

    # Write binary audio data to file
    with open(out_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
