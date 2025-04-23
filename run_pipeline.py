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
BUCKET     = os.getenv("S3_BUCKET",     "jc-ai-podcast-bucket")
REGION     = os.getenv("AWS_REGION",     "us-east-2")
VOICE_ID   = os.getenv("ELEVEN_VOICE_ID")  # your TTS voice
s3         = boto3.client("s3")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    """Lowercase + replace non-alphanum with hyphens."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def publish_episode(mp3_path: str, metadata: dict) -> str:
    """
    Uploads the final MP3 to S3 under episodes/{slug}.mp3.
    Returns the public URL (bucket must have a public read policy).
    """
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=mp3_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={  # no ACL here
            "ContentType": "audio/mpeg"
        }
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list):
    """
    Builds an RSS XML from the episodes list and uploads it as rss.xml.
    """
    rss = Element("rss", version="2.0")
    ch = SubElement(rss, "channel")
    SubElement(ch, "title").text = "My AI Podcast"
    SubElement(ch, "link").text  = f"https://{BUCKET}.s3-website-{REGION}.amazonaws.com/rss.xml"
    SubElement(ch, "description").text = "Automated AI show"

    for ep in episodes:
        item = SubElement(ch, "item")
        SubElement(item, "title").text       = ep["title"]
        SubElement(item, "description").text = ep["description"]
        SubElement(item, "pubDate").text     = ep["pubDate"]
        enc = SubElement(item, "enclosure")
        enc.set("url",    ep["url"])
        enc.set("length", str(ep["bytes"]))
        enc.set("type",   "audio/mpeg")

    xml = tostring(rss, encoding="utf-8", xml_declaration=True)
    s3.put_object(
        Bucket=BUCKET,
        Key="rss.xml",
        Body=xml,
        ContentType="application/rss+xml"
    )


# ─── Main Pipeline ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1) Generate with your LLM writer
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # 2) Normalize & fill missing fields
    title       = script.get("title", "").strip()
    description = script.get("description", "").strip()
    text_body   = script.get("full_script") or script.get("text") or ""
    slug        = script.get("slug") or slugify(title)
    pub_date    = script.get("pubDate") or datetime.now(timezone.utc) \
                                         .strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 3) Quick sanity check
    if not all([title, description, text_body]):
        raise RuntimeError(f"LLM returned incomplete data: {script.keys()}")

    # 4) Text-to-Speech
    tts(text_body, "episode.mp3", voice_id=VOICE_ID)

    # 5) Mastering: simple gain and export
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3.0)
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 6) Upload to S3
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       os.path.getsize("episode_final.mp3")
    })

    # 7) Maintain episodes.json locally
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file) as f:
            episodes = json.load(f)
    else:
        episodes = []

    episodes.insert(0, {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "url":         url,
        "bytes":       os.path.getsize("episode_final.mp3")
    })
    with open(eps_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 8) Regenerate RSS
    generate_rss(episodes)

    print(f"✅ Published episode \"{title}\" → {url}")
