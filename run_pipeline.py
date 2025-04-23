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
BUCKET = os.getenv("S3_BUCKET", "jc-ai-podcast-bucket")
REGION = os.getenv("AWS_REGION", "us-east-2")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID")
s3 = boto3.client("s3")


# ─── Helpers ───────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """Simple slug generator: lower-case, non-alphanum ➔ hyphens, strip."""
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def publish_episode(mp3_path: str, metadata: dict) -> str:
    """Upload MP3 to S3 and return its public URL."""
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=mp3_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": "audio/mpeg",
        },
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list) -> None:
    """Turn a list of episode dicts into RSS XML and push to S3."""
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
        ContentType="application/rss+xml",
        ACL="public-read",
    )


# ─── Main Pipeline ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1) Generate script + metadata from your LLM
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # 2) Normalize field names / fill missing values
    title       = script.get("title", "").strip()
    description = script.get("description", "").strip()
    full_text   = script.get("full_script") or script.get("text", "")
    slug        = script.get("slug") or slugify(title)
    pub_date    = script.get("pubDate") or datetime.now(timezone.utc) \
                                         .strftime("%a, %d %b %Y %H:%M:%S GMT")

    # 3) Sanity check
    if not all([title, description, full_text]):
        raise RuntimeError(f"Missing required output from make_script(): {script.keys()}")

    # 4) Text-to-Speech
    tts(full_text, "episode.mp3", voice_id=ELEVEN_VOICE_ID)

    # 5) Mastering: simple gain tweak + export final MP3
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3.0)
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 6) Upload MP3 to S3
    url = publish_episode("episode_final.mp3", {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "bytes":       os.path.getsize("episode_final.mp3"),
    })

    # 7) Maintain local episodes.json
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file) as f:
            eps = json.load(f)
    else:
        eps = []

    eps.insert(0, {
        "title":       title,
        "description": description,
        "slug":        slug,
        "pubDate":     pub_date,
        "url":         url,
        "bytes":       os.path.getsize("episode_final.mp3"),
    })
    with open(eps_file, "w") as f:
        json.dump(eps, f, indent=2)

    # 8) Regenerate & upload RSS feed
    generate_rss(eps)

    print(f"✅ Published \"{title}\" → {url}")
