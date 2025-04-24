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
VOICE_A_ID = os.getenv("ELEVEN_VOICE_A_ID")  # Host A voice
VOICE_B_ID = os.getenv("ELEVEN_VOICE_B_ID")  # Host B voice
s3         = boto3.client("s3")


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
        enc.set("url", ep["url"])
        enc.set("length", str(ep["bytes"]))
        enc.set("type", "audio/mpeg")

    xml = tostring(rss, encoding="utf-8", xml_declaration=True)
    s3.put_object(
        Bucket=BUCKET,
        Key="rss.xml",
        Body=xml,
        ContentType="application/rss+xml"
    )


if __name__ == "__main__":
    # 1) Generate script via LLM
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # 2) Extract required fields
    title = script.get("title", "").strip()
    description = script.get("description", "").strip()
    slug = script.get("slug") or slugify(title)
    pub_date = script.get("pubDate") or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 3) Flatten dialogue or full script
    raw_dialogue = script.get("dialogue") or script.get("full_script") or script.get("text") or ""
    if isinstance(raw_dialogue, list):
        pieces = []
        for elem in raw_dialogue:
            if isinstance(elem, str):
                pieces.append(elem.strip())
            elif isinstance(elem, dict):
                text = elem.get("text") or elem.get("line")
                if isinstance(text, str):
                    pieces.append(text.strip())
                else:
                    raise RuntimeError(f"Dialogue element missing text: {elem}")
            else:
                raise RuntimeError(f"Unexpected dialogue element type {type(elem)}: {elem}")
        full_text = "\n".join(pieces)
    else:
        full_text = str(raw_dialogue).strip()
    if not full_text:
        raise RuntimeError("LLM returned empty dialogue or script.")

    # 4) Split into lines & TTS per speaker
    lines = [ln for ln in full_text.splitlines() if ln.strip()]
    segments = []
    for idx, line in enumerate(lines, 1):
        voice_id = VOICE_B_ID if line.startswith("Host B:") else VOICE_A_ID
        seg_file = f"segment_{idx:03d}.mp3"
        tts(text=line, out_path=seg_file, voice_id=voice_id)
        segments.append(seg_file)

    # 5) Concatenate, gain & export
    convo = AudioSegment.empty()
    for seg in segments:
        convo += AudioSegment.from_file(seg, format="mp3")
    convo = convo.apply_gain(-3.0)
    convo.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 6) Upload final MP3
    url = publish_episode("episode_final.mp3", {
        "title": title,
        "description": description,
        "slug": slug,
        "pubDate": pub_date,
        "bytes": os.path.getsize("episode_final.mp3")
    })

    # 7) Update local episodes.json
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file) as f:
            episodes = json.load(f)
    else:
        episodes = []
    episodes.insert(0, {"title": title, "description": description, "slug": slug,
                         "pubDate": pub_date, "url": url,
                         "bytes": os.path.getsize("episode_final.mp3")})
    with open(eps_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 8) Regenerate RSS feed
    generate_rss(episodes)
    print(f"✅ Published episode '{title}' → {url}")
