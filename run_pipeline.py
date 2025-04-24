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
BUCKET        = os.getenv("S3_BUCKET", "jc-ai-podcast-bucket")
REGION        = os.getenv("AWS_REGION", "us-east-2")
VOICE_A_ID    = os.getenv("ELEVEN_VOICE_A_ID")  # e.g. cohost 1
VOICE_B_ID    = os.getenv("ELEVEN_VOICE_B_ID")  # e.g. cohost 2
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
        ExtraArgs={"ContentType": "audio/mpeg"}
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list):
    rss = Element("rss", version="2.0")
    ch  = SubElement(rss, "channel")
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


# ─── Pipeline ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # pull out the fields
    title       = script.get("title","").strip()
    description = script.get("description","").strip()
    slug        = script.get("slug") or slugify(title)
    pub_date    = script.get("pubDate") or datetime.now(timezone.utc)\
                                            .strftime("%a, %d %b %Y %H:%M:%S GMT")

    # dialogue may come back as a single string or a list
    raw = script.get("dialogue") or script.get("full_script") or ""
    # if it's a list, join on newlines; if a string, leave it
    if isinstance(raw, list):
        full_text = "\n".join(raw)
    else:
        full_text = raw

    if not all([title, description, full_text]):
        raise RuntimeError(f"Incomplete LLM output: {script.keys()}")

    # split into turns
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    segments = []
    for i, line in enumerate(lines, start=1):
        # Expect lines like: "Host A: Hello…" or "Host B: Great question!"
        if line.startswith("Host B:"):
            voice_id = VOICE_B_ID
        else:
            # default to Host A for anything else (including "Host A:")
            voice_id = VOICE_A_ID

        out_file = f"segment_{i:03d}.mp3"
        tts(
            text=line,
            out_path=out_file,
            voice_id=voice_id
        )
        segments.append(out_file)

    # concatenate
    convo = AudioSegment.empty()
    for seg in segments:
        convo += AudioSegment.from_file(seg, format="mp3")

    # apply a little mastering
    convo = convo.apply_gain(-3.0)
    convo.export("episode_final.mp3", format="mp3", bitrate="128k")

    # upload
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       os.path.getsize("episode_final.mp3")
    })

    # update local episodes.json
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file) as f: episodes = json.load(f)
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
    with open(eps_file,"w") as f:
        json.dump(episodes, f, indent=2)

    # regenerate RSS
    generate_rss(episodes)

    print(f"✅ Published episode “{title}” → {url}")
