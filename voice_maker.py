import os, requests

ELEVEN_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

def tts(text: str, out_path: str, voice_id="YourVoiceIDHere"):
    headers = {
        "xi-api-key": os.getenv("ELEVEN_KEY"),
        "Content-Type": "application/json"
    }
    payload = {
        "model_id": "eleven_turbo_v2",
        "text": text,
        "voice_settings": {"stability": 0.4, "similarity_boost": 1}
    }
    r = requests.post(ELEVEN_URL.format(voice_id=voice_id), json=payload, stream=True, headers=headers)
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            f.write(chunk)
