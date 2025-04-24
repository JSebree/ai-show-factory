# llm_writer.py
import os
import re
import json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def make_script(topic: str) -> dict:
    """
    Returns a dict with keys:
      - title       (str)
      - description (str)
      - pubDate     (RFC-2822 str)
      - dialogue    (list of {speaker, time, text})
    """
    # 1) JSON schema for validation
    schema = {
        "type": "object",
        "properties": {
            "title":       {"type": "string"},
            "description": {"type": "string"},
            "pubDate":     {"type": "string"},
            "dialogue": {
                "type": "array",
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

    # 2) Build the system prompt with all your requirements
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system_prompt = (
        "You are a podcast scriptwriter for **Art and Ingrid Talk A.I.**\n"
        f"Current date (UTC): {today}\n\n"
        "Your mission is to craft a **20–25 minute** (~3,800+ word) two-host episode—friendly, engaging, "
        "fact-rich but with genuine chemistry—about the latest AI news from **only reputable sources** "
        "published in the last **14 days** (including news sites, thought-leader tweets, LinkedIn posts, "
        "YouTube snippets, Reddit conversations).\n\n"

        "**Structure (smooth, unlabeled transitions; no robotic pillar call-outs):**\n"
        "  • Breakthroughs (latest top stories, ~5 min)  \n"
        "  • Governance & Ethics (policy, moral stakes, ~5 min)  \n"
        "  • Inner Life & Society (psych/community impact, ~5 min)  \n"
        "  • Speculative Futures (economy, philosophy, what’s next, ~5 min)  \n"
        "  • Intros, wrap, Q&A, sponsor reads sprinkled to hit 20–25 min (total ~5 min)\n\n"

        "**Style & Pacing:**\n"
        "- Hosts: **Art** & **Ingrid**, back-and-forth banter—slightly slower delivery, "
        "pauses to reflect, real-time reactions.  \n"
        "- Emphasize facts and context; weave in anecdotes, listener questions, and 1 brief case study.  \n"
        "- Include **approximate timestamps** (MM:SS) at each section start.\n\n"

        "**Output:**\n"
        "Return **only** valid JSON (no markdown, no commentary), exactly matching this top-level schema:\n"
        + json.dumps(schema, indent=2)
    )

    # 3) The user prompt
    user_prompt = (
        f"Here’s today’s topic:\n\n**{topic}**\n\n"
        "Return only the JSON object."
    )

    # 4) Call the new OpenAI API
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=6000
    )

    raw = resp.choices[0].message.content

    # 5) Strip any code fences
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}") from e

    # 7) Validate required fields
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    # 8) Fill defaults if blank
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    if not data["title"].strip():
        data["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    if not data["pubDate"].strip():
        data["pubDate"] = now

    return data
