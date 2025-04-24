#!/usr/bin/env python3
import os
import re
import json
import boto3
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from pydub import AudioSegment
from voice_maker import tts
from llm_writer import make_script

# ─── Configuration ─────────────────────────────────────────────────────────────
BUCKET      = os.getenv("S3_BUCKET",     "jc-ai-podcast-bucket")
REGION      = os.getenv("AWS_REGION",     "us-east-2")
VOICE_A_ID  = os.getenv("ELEVEN_VOICE_A")  # e.g. your first host
VOICE_B_ID  = os.getenv("ELEVEN_VOICE_B")  # e.g. your second host
s3          = boto3.client("s3")


# ─── publish & RSS helpers (unchanged) ─────────────────────────────────────────
def slugify(text): …
def publish_episode(mp3_path, metadata): …
def generate_rss(episodes): …

# ─── Main Pipeline ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    title       = script["title"].strip()
    description = script["description"].strip()
    pub_date    = script["pubDate"]
    slug        = script.get("slug") or re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    dialogue    = script["dialogue"]

    # sanity check
    if not (title and description and dialogue):
        raise RuntimeError("Missing title/description/dialogue from LLM output")

    # 4) Two-voice TTS: render each turn separately
    parts = []
    for i, turn in enumerate(dialogue):
        speaker = turn["speaker"]
        text    = turn["text"]

        # pick the correct voice ID
        voice_id = VOICE_A_ID if speaker.lower().startswith("host a") else VOICE_B_ID
        if not voice_id:
            raise RuntimeError(f"Missing voice ID for {speaker}")

        out_file = f"seg_{i}.wav"
        tts(text, out_file, voice_id=voice_id)
        parts.append(AudioSegment.from_file(out_file, format="wav"))

    # 5) Concatenate all segments into one episode
    episode = parts[0]
    for seg in parts[1:]:
        episode += seg
    episode.export("episode.mp3", format="mp3", bitrate="128k")

    # 6) (Optional) Mastering boost/normalize
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3.0)
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 7) Upload and metadata bookkeeping (unchanged)
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       os.path.getsize("episode_final.mp3")
    })

    # [...] episodes.json + generate_rss as before [...]

    print(f"✅ Published \"{title}\" → {url}")
