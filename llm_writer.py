# llm_writer.py
import os
import re
import json
from datetime import datetime, timezone
import openai

# ─── Setup ──────────────────────────────────────────────────────────────────────
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

    # 2) Build the full system prompt
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system_prompt = (
        "You are a professional podcast scriptwriter for **Art and Ingrid Talk A.I.**\n"
        f"Current date (UTC): {today}\n\n"
        "Your mission: craft a **20–25 minute** (~3,800+ word) two-host episode—friendly, engaging, fact-rich "
        "but with genuine chemistry—about the latest AI news from **only reputable sources** published in the last **14 days** "
        "(including news sites, thought-leader tweets, LinkedIn posts, YouTube snippets, and Reddit threads).\n\n"

        "**Structure (smooth unlabeled transitions):**\n"
        "  • Breakthroughs (~5 min)  \n"
        "  • Governance & Ethics (~5 min)  \n"
        "  • Inner Life & Society (~5 min)  \n"
        "  • Speculative Futures (~5 min)  \n"
        "  • Intros, listener Q&A, sponsor reads, wrap-up (~5–7 min)\n\n"

        "**Style & Pacing:**\n"
        "- Hosts: **Art** & **Ingrid**, back-and-forth banter—**slightly slower** delivery with natural pauses.  \n"
        "- Emphasize facts: weave in anecdotes, listener questions, and 1 brief case study.  \n"
        "- Include **approximate timestamps** (MM:SS) at each new section start.\n\n"

        "**Output:** Return **only** valid JSON (no markdown, no commentary), exactly matching this schema:\n"
        + json.dumps(schema, indent=2)
    )

    # 3) User prompt with today’s topic
    user_prompt = (
        f"Here’s today’s topic:\n\n**{topic}**\n\n"
        "Return only the JSON object."
    )

    # 4) Call the new chat completions API
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=6000
    )

    raw = resp.choices[0].message.content

    # 5) Strip any ```json fences```
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}") from e

    # 7) Validate required keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    # 8) Fill in any blank defaults
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    if not data["title"].strip():
        data["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    if not data["pubDate"].strip():
        data["pubDate"] = now

    return data
