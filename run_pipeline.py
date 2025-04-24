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
BUCKET          = os.getenv("S3_BUCKET", "jc-ai-podcast-bucket")
REGION          = os.getenv("AWS_REGION", "us-east-2")
VOICE_A_ID      = os.getenv("ELEVEN_VOICE_A_ID")  # first co-host voice ID
VOICE_B_ID      = os.getenv("ELEVEN_VOICE_B_ID")  # second co-host voice ID
S3_BASE_URL     = f"https://{BUCKET}.s3.amazonaws.com"
RSS_PAGE_URL    = f"https://{BUCKET}.s3-website-{REGION}.amazonaws.com/rss.xml"
s3_client       = boto3.client("s3")

# ─── Helpers ───────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """Simple slugifier: lowercases and replaces non-alphanum with hyphens."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def publish_episode(file_path: str, slug: str) -> str:
    """
    Upload file to S3 under `episodes/{slug}.mp3` and return its public URL.
    Requires bucket policy allowing public read.
    """
    key = f"episodes/{slug}.mp3"
    s3_client.upload_file(
        Filename=file_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={"ContentType": "audio/mpeg"}
    )
    return f"{S3_BASE_URL}/{key}"


def generate_rss(episodes: list[dict]):
    """
    Build and upload RSS feed to `rss.xml` in the bucket.
    """
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "My AI Podcast"
    SubElement(channel, "link").text = RSS_PAGE_URL
    SubElement(channel, "description").text = "Automated AI co-hosted show"

    for ep in episodes:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "description").text = ep["description"]
        SubElement(item, "pubDate").text = ep["pubDate"]
        enc = SubElement(item, "enclosure")
        enc.set("url",    ep["url"])
        enc.set("length", str(ep["bytes"]))
        enc.set("type",   "audio/mpeg")

    xml_data = tostring(rss, encoding="utf-8", xml_declaration=True)
    s3_client.put_object(
        Bucket=BUCKET,
        Key="rss.xml",
        Body=xml_data,
        ContentType="application/rss+xml"
    )

# ─── Main Pipeline ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) Ask LLM for a script/topic dialogue
    topic = os.getenv("EPISODE_TOPIC", "AI and society")
    script = make_script(topic)

    # validate required keys
    required = {"title", "description", "pubDate", "dialogue"}
    if not required.issubset(script):
        missing = required - set(script)
        raise RuntimeError(f"LLM script missing fields: {missing}")

    title       = script["title"].strip()
    description = script["description"].strip()
    pub_date    = script["pubDate"].strip()
    dialogue    = script["dialogue"]
    slug        = slugify(title)

    # 2) Render each dialogue turn with the correct co-host voice
    # map speaker names to the two voice IDs in encounter order
    speaker_map: dict[str,str] = {}
    segments: list[AudioSegment] = []
    for idx, turn in enumerate(dialogue):
        speaker = turn.get("speaker","").strip()
        text    = turn.get("text","").strip()
        if not (speaker and text):
            continue

        # assign voice IDs dynamically
        if speaker not in speaker_map:
            if len(speaker_map) == 0:
                speaker_map[speaker] = VOICE_A_ID
            elif len(speaker_map) == 1:
                speaker_map[speaker] = VOICE_B_ID
            else:
                raise RuntimeError(f"More than two speakers encountered: {speaker_map.keys()} + {speaker}")
        voice_id = speaker_map[speaker]
        if not voice_id:
            raise RuntimeError(f"No voice ID configured for speaker {speaker}")

        out_file = f"seg_{idx}.mp3"
        tts(text, out_file, voice_id=voice_id)
        segments.append(AudioSegment.from_file(out_file))

    # if no segments, bail
    if not segments:
        raise RuntimeError("No audio segments generated—from empty dialogue?")

    # 3) Concatenate all segments into episode.mp3
    episode = segments[0]
    for seg in segments[1:]:
        episode += seg
    episode.export("episode.mp3", format="mp3", bitrate="128k")

    # 4) Simple mastering: gain adjustment
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    final = audio.apply_gain(-3.0)
    final.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 5) Upload to S3 and record metadata
    url = publish_episode("episode_final.mp3", slug)
    size = os.path.getsize("episode_final.mp3")

    # load or init episodes list
    eps_file = "episodes.json"
    episodes = []
    if os.path.exists(eps_file):
        with open(eps_file) as f:
            episodes = json.load(f)

    episodes.insert(0, {
        "title":       title,
        "description": description,
        "pubDate":     pub_date,
        "url":         url,
        "bytes":       size
    })
    with open(eps_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 6) Regenerate RSS
    generate_rss(episodes)

    print(f"✅ Published: {title} → {url}")
