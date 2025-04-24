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
BUCKET        = os.getenv("S3_BUCKET",     "jc-ai-podcast-bucket")
REGION        = os.getenv("AWS_REGION",     "us-east-2")
VOICE_A_ID    = os.getenv("ELEVEN_VOICE_A_ID")  # Host A
VOICE_B_ID    = os.getenv("ELEVEN_VOICE_B_ID")  # Host B
s3            = boto3.client("s3")


# ─── Helpers ───────────────────────────────────────────────────────────────────
def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def publish_episode(mp3_path: str, metadata: dict) -> str:
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=mp3_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={ "ContentType": "audio/mpeg" }
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list):
    rss = Element("rss", version="2.0")
    ch = SubElement(rss, "channel")
    SubElement(ch, "title").text       = "My AI Podcast"
    SubElement(ch, "link").text        = f"https://{BUCKET}.s3-website-{REGION}.amazonaws.com/rss.xml"
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
    # 1) Generate script
    topic  = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # 2) Extract & fill defaults
    title       = script.get("title", "").strip()
    description = script.get("description", "").strip()

    # now accept either "full_script" or "dialogue"
    full = (
        script.get("full_script")
        or script.get("dialogue")
        or script.get("text")
        or ""
    )

    slug     = script.get("slug") or slugify(title)
    pub_date = script.get("pubDate") or datetime.now(timezone.utc) \
                                          .strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 3) Sanity check
    if not all([title, description, full]):
        raise RuntimeError(f"Incomplete LLM output: {script.keys()}")


    # 4) Parse into Host A/B segments
    segments = []
    speaker, buffer = None, ""
    for line in full.splitlines():
        line = line.strip()
        if line.startswith("Host A:"):
            if speaker:
                segments.append((speaker, buffer))
            speaker = "A"
            buffer  = line.split("Host A:", 1)[1].strip()
        elif line.startswith("Host B:"):
            if speaker:
                segments.append((speaker, buffer))
            speaker = "B"
            buffer  = line.split("Host B:", 1)[1].strip()
        else:
            buffer += " " + line
    if speaker and buffer:
        segments.append((speaker, buffer))

    # 5) TTS each segment & collect AudioSegments
    audio_parts = []
    for i, (sp, txt) in enumerate(segments):
        vid    = VOICE_A_ID if sp == "A" else VOICE_B_ID
        fname  = f"seg_{i}.mp3"
        tts(txt, fname, voice_id=vid)
        audio_parts.append(AudioSegment.from_file(fname, format="mp3"))

    # 6) Concatenate into one episode.mp3
    episode = audio_parts[0]
    for part in audio_parts[1:]:
        episode += part
    episode.export("episode.mp3", format="mp3")

    # 7) Mastering: simple gain tweak + export final
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3.0)
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 8) Upload
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       os.path.getsize("episode_final.mp3")
    })

    # 9) Update episodes.json
    eps_file = "episodes.json"
    episodes = json.load(open(eps_file)) if os.path.exists(eps_file) else []
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

    # 10) Regenerate RSS
    generate_rss(episodes)

    print(f"✅ Published \"{title}\" → {url}")
