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
BUCKET     = os.getenv("S3_BUCKET", "jc-ai-podcast-bucket")
REGION     = os.getenv("AWS_REGION", "us-east-2")
VOICE_A_ID = os.getenv("ELEVEN_VOICE_A_ID")   # e.g. first host
VOICE_B_ID = os.getenv("ELEVEN_VOICE_B_ID")   # e.g. second host
s3         = boto3.client("s3", region_name=REGION)


# ─── Helpers ───────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """Lowercase + replace non-alphanum with hyphens."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def publish_episode(mp3_path: str, metadata: dict) -> str:
    """
    Uploads the final MP3 to S3 under episodes/{slug}.mp3.
    Returns the public URL.
    """
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=mp3_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={"ContentType": "audio/mpeg"}
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list):
    """
    Builds an RSS XML from the episodes list and uploads it as rss.xml.
    """
    rss = Element("rss", version="2.0")
    ch = SubElement(rss, "channel")
    SubElement(ch, "title").text = "My AI Podcast"
    SubElement(ch, "link").text = f"https://{BUCKET}.s3-website-{REGION}.amazonaws.com/rss.xml"
    SubElement(ch, "description").text = "Automated AI show"

    for ep in episodes:
        item = SubElement(ch, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "description").text = ep["description"]
        SubElement(item, "pubDate").text = ep["pubDate"]
        enc = SubElement(item, "enclosure")
        enc.set("url",    ep["url"])
        enc.set("length", str(ep["bytes"]))
        enc.set("type",   "audio/mpeg")

    xml_data = tostring(rss, encoding="utf-8", xml_declaration=True)
    s3.put_object(
        Bucket=BUCKET,
        Key="rss.xml",
        Body=xml_data,
        ContentType="application/rss+xml"
    )


# ─── Main Pipeline ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) Generate script with two-host dialogue
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    title       = script.get("title", "").strip()
    description = script.get("description", "").strip()
    pub_date    = script.get("pubDate") or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    slug        = script.get("slug") or slugify(title)
    dialogue    = script.get("dialogue", [])

    # sanity check
    if not (title and description and dialogue):
        raise RuntimeError(f"Incomplete LLM output: {script.keys()}")

    # 2) Render each turn with the proper voice, ElevenLabs comes back as MP3
    segments = []
    for idx, turn in enumerate(dialogue):
        speaker = turn.get("speaker", "").strip()
        text    = turn.get("text",    "").strip()
        if not text:
            continue

        # pick the correct ElevenLabs voice
        if speaker.lower().startswith("host a"):
            vid = VOICE_A_ID
        elif speaker.lower().startswith("host b"):
            vid = VOICE_B_ID
        else:
            raise RuntimeError(f"Unknown speaker “{speaker}”")

        # write out as MP3, then let pydub auto-detect format
        mp3_path = f"seg_{idx}.mp3"
        tts(text, mp3_path, voice_id=vid)
        segments.append(AudioSegment.from_file(mp3_path))

    # 3) Concatenate into one MP3
    if not segments:
        raise RuntimeError("No audio segments generated")

    episode_audio = segments[0]
    for seg in segments[1:]:
        episode_audio += seg
    episode_audio.export("episode.mp3", format="mp3", bitrate="128k")

    # 4) Optional mastering
    mastered = AudioSegment.from_file("episode.mp3", format="mp3")
    mastered = mastered.apply_gain(-3.0)
    mastered.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 5) Upload & metadata
    size_bytes = os.path.getsize("episode_final.mp3")
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       size_bytes
    })

    # 6) Update local episodes.json
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file, "r") as f:
            episodes = json.load(f)
    else:
        episodes = []

    episodes.insert(0, {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "url":         url,
        "bytes":       size_bytes
    })
    with open(eps_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 7) Regenerate RSS
    generate_rss(episodes)

    print(f"✅ Published episode “{title}” → {url}")
