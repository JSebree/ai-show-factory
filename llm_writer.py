# llm_writer.py

import os
import re
import json
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def make_script(topic: str) -> dict:
    """
    Generates a two-host podcast script on the given topic.
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

    # 2) Fine-tuned system prompt
    system = {
        "role":    "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show.\n"
            "Produce a natural, free-flowing 20–25 minute conversation about the latest AI news "
            "and its social & philosophical impact, drawing exclusively from reputable sources "
            "published in the last 30 days.\n\n"

            "Use these four themes to structure—but never name—the flow:\n"
            "  • Breakthroughs: deep explainer of the day’s biggest AI headline\n"
            "  • Governance & Ethics: policy stakes and emerging moral questions\n"
            "  • Inner Life & Society: how AI is reshaping our psychology & communities\n"
            "  • Speculative Futures: where this all leads economically & philosophically\n\n"

            "Format:\n"
            "- Two hosts (Host A & Host B) in an easy, back-and-forth style with genuine rapport.\n"
            "- No “pillar” call-outs—just smooth segues into each theme for ~5 minutes each.\n"
            "- Include approximate timestamps (MM:SS) at the start of each segment.\n"
            "- Total run time: 20–25 minutes of dialogue.\n\n"

            "Produce exactly valid JSON (no markdown, no commentary) matching this schema."
        )
    }

    # 3) User prompt invoking schema
    user = {
        "role":    "user",
        "content": (
            f"Topic: {topic}\n\n"
            f"Here is the JSON schema to follow:\n\n{json.dumps(json_schema, indent=2)}\n\n"
            "Return only the JSON object."
        )
    }

    # 4) Call the API
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, user],
        temperature=0.7,
        max_tokens=1500
    )

    raw = resp.choices[0].message.content

    # 5) Clean out any fences
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n\n{raw}")

    # 7) Sanity-check required keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"Missing field from LLM output: {key}")

    return data
