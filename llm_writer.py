import os
import re
import json
import openai
from datetime import datetime, timezone

# Initialize OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")


def make_script(topic: str) -> dict:
    """
    Generates a two-host, 20–25 min podcast script on the given topic.
    Returns a dict with:
      - title       (str)
      - description (str)
      - pubDate     (RFC-2822 str)
      - dialogue    (list of {speaker: str, time: "MM:SS", text: str})
    """

    # 1) JSON schema
    json_schema = {
        "type": "object",
        "properties": {
            "title":       {"type": "string"},
            "description": {"type": "string"},
            "pubDate":     {"type": "string"},
            "dialogue": {
                "type":  "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {"type": "string"},
                        "time":    {"type": "string"},
                        "text":    {"type": "string"}
                    },
                    "required": ["speaker", "time", "text"]
                }
            }
        },
        "required": ["title", "description", "pubDate", "dialogue"]
    }

    # 2) System prompt with full requirements
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show titled 'Art and Ingrid talks AI'.\n"
            "Your job is to craft a 20–25 minute back-and-forth conversation about the latest AI news, "
            "with social and philosophical implications. The current date is " + today + ". "
            "Only reference reputable sources published within the last 30 days.\n\n"

            "Structure by four themes—without directly naming them as 'pillars':\n"
            "  • Breakthroughs: deep explainer of today’s biggest AI headline.\n"
            "  • Governance & Ethics: policy stakes and moral dimensions.\n"
            "  • Inner Life & Society: psychological & community impact.\n"
            "  • Speculative Futures: economic & philosophical possibilities.\n\n"
            "Allow Art and Ingrid to riff and banter with personal perspectives 'in-between' facts, "
            "to help stretch dialogue to a full 20–25 minutes (not under 4 minutes).\n\n"
            "Use these guidelines:\n"
            "- Hosts: Art & Ingrid, friendly and engaging with natural chemistry.\n"
            "- Approximate timestamps (MM:SS) at the start of each segment.\n"
            "- Rough time allocation: 5 min each theme + 5–7 min intro/transitions/conclusion.\n"
            "- Gather details from news outlets, thought-leader X posts, LinkedIn essays, YouTube explainers, Reddit threads.\n\n"
            "Return exactly valid JSON matching this schema—no markdown or commentary."
        )
    }

    # 3) User prompt with schema
    user = {
        "role": "user",
        "content": (
            f"Topic: {topic}\n\n"
            "Here is the JSON schema to use:\n"
            f"{json.dumps(json_schema)}\n\n"
            "Return only the JSON object."
        )
    }

    # 4) Send request
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, user],
        temperature=0.7,
        max_tokens=1600
    )

    raw = resp.choices[0].message.content

    # 5) Clean up
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n\n{raw}")

    # 7) Sanity-check
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"Missing field from LLM output: {key}")

    return data
