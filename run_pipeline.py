import os
import json
import boto3
from xml.etree.ElementTree import Element, SubElement, tostring
from pydub import AudioSegment
from voice_maker import tts
from llm_writer import make_script

# === Configuration ===
BUCKET = os.getenv("S3_BUCKET", "jc-ai-podcast-bucket")
REGION = os.getenv("AWS_REGION", "us-east-1")
s3 = boto3.client("s3")

# === Helpers ===
def publish_episode(mp3_path: str, metadata: dict) -> str:
    """
    Uploads the MP3 to S3 and returns its public URL.
    """
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=mp3_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": "audio/mpeg",
        }
    )
    return f"https://{BUCKET}.s3.amazonaws.com/{key}"


def generate_rss(episodes: list) -> None:
    """
    Generates an RSS XML string from episode list and uploads it to S3 as rss.xml.
    """
    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")
    SubElement(channel, "title").text = "My AI Podcast"
    SubElement(channel, "link").text = f"https://{BUCKET}.s3-website-{REGION}.amazonaws.com/rss.xml"
    SubElement(channel, "description").text = "Automated AI show powered by GitHub Actions & AWS S3"

    for ep in episodes:
        item = SubElement(channel, "item")
        SubElement(item, "title").text = ep["title"]
        SubElement(item, "description").text = ep["description"]
        SubElement(item, "pubDate").text = ep["pubDate"]
        enc = SubElement(item, "enclosure")
        enc.set("url", ep["url"])
        enc.set("length", str(ep["bytes"]))
        enc.set("type", "audio/mpeg")

    xml_bytes = tostring(rss, encoding="utf-8", xml_declaration=True)
    s3.put_object(
        Bucket=BUCKET,
        Key="rss.xml",
        Body=xml_bytes,
        ContentType="application/rss+xml",
        ACL="public-read"
    )

# === Main pipeline ===
if __name__ == "__main__":
    # 1) Generate script via LLM
    topic = os.getenv("EPISODE_TOPIC", "Default AI Topic")
    script = make_script(topic)

    # Expecting keys: title, slug, full_script, description, pubDate
    title       = script.get("title")
    slug        = script.get("slug")
    full_script = script.get("full_script")
    description = script.get("description")
    pub_date    = script.get("pubDate")

    if not all([title, slug, full_script, description, pub_date]):
        raise ValueError("make_script did not return all required fields")

    # 2) Text-to-speech
    tts(full_script, "episode.mp3", voice_id=os.getenv("ELEVEN_VOICE_ID"))

    # 3) Mastering: apply normalization or gain
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3.0)
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")

    # 4) Publish to S3 and get URL
    url = publish_episode("episode_final.mp3", {
        "title": title,
        "description": description,
        "slug": slug,
        "pubDate": pub_date,
        "bytes": os.path.getsize("episode_final.mp3")
    })

    # 5) Load or initialize local episodes JSON
    eps_file = "episodes.json"
    if os.path.exists(eps_file):
        with open(eps_file) as f:
            episodes = json.load(f)
    else:
        episodes = []

    # Prepend new episode
    episodes.insert(0, {
        "title": title,
        "description": description,
        "slug": slug,
        "pubDate": pub_date,
        "url": url,
        "bytes": os.path.getsize("episode_final.mp3")
    })
    with open(eps_file, "w") as f:
        json.dump(episodes, f, indent=2)

    # 6) Regenerate and upload RSS feed
    generate_rss(episodes)

    print("Published episode:", title)
