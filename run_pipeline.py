import os
import boto3
import json
from xml.etree.ElementTree import Element, SubElement, tostring
from pydub import AudioSegment
from voice_maker import tts
# … other imports …

BUCKET = "jc-ai-podcast"
s3 = boto3.client("s3")

def publish_episode(episode_mp3: str, metadata: dict):
    # 1. Upload MP3
    key = f"episodes/{metadata['slug']}.mp3"
    s3.upload_file(
        Filename=episode_mp3,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={
            "ACL": "public-read",
            "ContentType": "audio/mpeg"
        }
    )
    url = f"https://{BUCKET}.s3.amazonaws.com/{key}"
    return url

def generate_rss(all_episodes: list):
    rss = Element("rss", version="2.0")
    ch = SubElement(rss, "channel")
    SubElement(ch, "title").text = "My AI Podcast"
    SubElement(ch, "link").text  = f"https://{BUCKET}.s3-website-us-east-1.amazonaws.com/rss.xml"
    SubElement(ch, "description").text = "Automated AI show"

    for ep in all_episodes:
        item = SubElement(ch, "item")
        SubElement(item, "title").text       = ep["title"]
        SubElement(item, "description").text = ep["description"]
        SubElement(item, "pubDate").text     = ep["pubDate"]
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
        ACL="public-read"
    )

if __name__ == "__main__":
    # 1. Create script (GPT, etc.)
    script = make_script(...)  
    # 2. TTS
    tts(script["text"], "episode.mp3", voice_id=os.getenv("ELEVEN_VOICE_ID"))
    # 3. Mastering (ffmpeg via pydub)
    audio = AudioSegment.from_file("episode.mp3", format="mp3")
    audio = audio.apply_gain(-3)  # example
    audio.export("episode_final.mp3", format="mp3", bitrate="128k")
    # 4. Upload
    url = publish_episode("episode_final.mp3", {
        "title": script["title"],
        "description": script["description"],
        "slug": script["slug"],
        "pubDate": script["pubDate"],
        "bytes": os.path.getsize("episode_final.mp3")
    })
    # 5. Maintain a local JSON of episodes (or pull from a sheet)
    if os.path.exists("episodes.json"):
        with open("episodes.json") as f:
            eps = json.load(f)
    else:
        eps = []
    eps.insert(0, {
        "title": script["title"],
        "description": script["description"],
        "slug": script["slug"],
        "pubDate": script["pubDate"],
        "url": url,
        "bytes": os.path.getsize("episode_final.mp3")
    })
    with open("episodes.json", "w") as f:
        json.dump(eps, f, indent=2)

    # 6. Regenerate RSS
    generate_rss(eps)

    print("Published!", url)
