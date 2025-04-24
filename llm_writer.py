# llm_writer.py
import os
import re
import json
import openai
from datetime import datetime, timezone

openai.api_key = os.getenv("OPENAI_API_KEY")


def make_script(topic: str) -> dict:
    """
    Generates a two-host, 20–25 minute podcast script on the given topic.
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

    # 2) Enhanced system prompt
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show titled 'Art and Ingrid talks AI'.\n"
            "Your goal is to craft a natural, free-flowing 20–25 minute, 3000+ word conversation about the latest AI news "
            "and its social & philosophical implications. Current date: " + today + ".\n\n"

            "STEP 1: Research Phase – Gather at least 30 relevant items (articles, thought-leader X posts, "
            "LinkedIn essays, YouTube explainers, Reddit threads) on the topic from reputable sources "
            "published within the last 14 days. Include diverse perspectives, quotes, and case studies to build depth.\n\n"

            "STEP 2: Script Phase – Weave the research into four thematic segments without naming them directly:\n"
            "  • Breakthroughs: deep technical explainers of major AI headlines (~5–6 minutes)\n"
            "  • Governance & Ethics: policy stakes and moral considerations (~5–6 minutes)\n"
            "  • Inner Life & Society: human stories and community impact (~5–6 minutes)\n"
            "  • Speculative Futures: economic and philosophical possibilities (~5–6 minutes)\n\n"

            "Format Guidelines:\n"
            "- Hosts: Art & Ingrid, genuine and engaging, speaking slightly slower for clarity, with personal anecdotes interwoven between facts.\n"
            "- Smooth segues into each theme—never explicitly mention 'pillars'—ensuring transitions feel organic.\n"
            "- Include approximate timestamps (MM:SS) at the start of each new segment.\n"
            "- Dialogue must total at least 3000 words to meet the 20–25 minute runtime.\n\n"
            "Return exactly valid JSON (no markdown, no commentary) matching the provided schema."
        )
    }

    # 3) User prompt with schema
    user = {
        "role": "user",
        "content": (
            f"Topic: {topic}\n\n"
            "Here is the JSON schema to use:\n"
            f"{json.dumps(json_schema, indent=2)}\n\n"
            "Return only the JSON object."
        )
    }

    # 4) Call OpenAI API
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, user],
        temperature=0.7,
        max_tokens=2000
    )

    raw = resp.choices[0].message.content

    # 5) Clean up any JSON fences
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}")

    # 7) Validate output keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"Missing field from LLM output: {key}")

    return data
