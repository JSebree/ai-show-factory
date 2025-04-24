# llm_writer.py

import os
import re
import json
import openai

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

    # 2) Fine-tuned system prompt
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show.\n"
            "Your goal is to craft a **20–25 minute** back-and-forth conversation about the latest AI news "
            "and its social & philosophical impact.\n\n"

            "Gather from *multiple* reputable sources—top news outlets plus thought-leader "
            "tweets/X posts, LinkedIn essays, YouTube explainers, Reddit threads—*all* published "
            "within the last 30 days, and weave them naturally into the dialogue.\n\n"

            "Structure by these four themes—but never mention the labels directly:\n"
            "  • Breakthroughs: deep explainer of today’s biggest AI headline\n"
            "  • Governance & Ethics: policy stakes and moral dimensions\n"
            "  • Inner Life & Society: psychological & community impact\n"
            "  • Speculative Futures: economic & philosophical possibilities\n\n"

            "Format:\n"
            "- Two hosts (Host A & Host B) in a friendly, engaging back-and-forth.\n"
            "- Smooth segues—no “pillar” call-outs—~5 min per theme, plus ~5–7 min intro/transitions/wrap.\n"
            "- Include approximate timestamps (MM:SS) at the start of each new segment.\n"
            "- Total dialogue needs to fill **20–25 minutes**.\n\n"

            "Return *only* exact, valid JSON matching this schema—no markdown or commentary."
        )
    }

    # 3) User prompt with schema
    user = {
        "role": "user",
        "content": (
            f"Topic: {topic}\n\n"
            "Here is the JSON schema to use:\n\n"
            f"{json.dumps(json_schema, indent=2)}\n\n"
            "Return only the JSON object."
        )
    }

    # 4) Call the new (1.0+) chat endpoint
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, user],
        temperature=0.7,
        max_tokens=1600
    )

    raw = resp.choices[0].message.content

    # 5) Strip any ```json fences
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
