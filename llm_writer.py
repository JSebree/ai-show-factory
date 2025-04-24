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

    # 2) Build a deeply detailed system prompt
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system_prompt = (
        "You are the showrunner and scriptwriter for **Art and Ingrid Talk A.I.**\n"
        f"Date (UTC): {now}\n\n"
        "Your assignment: craft a **20–25 minute** (~3,800+ word) two-host conversation between Art & Ingrid. "
        "It should be friendly, deeply informative, and paced **slightly slower** with natural pauses. "
        "After drafting the script, count total words. If under 3800 words, automatically add more examples, "
        "anecdotes, Q&A, sponsor reads, or deeper dives until word count >= 3800.\n\n"

        "Content requirements:\n"
        "- Cover the **latest AI news** published **within the last 14 days**, drawing from at least **30** distinct, reputable sources:\n"
        "  news outlets, expert tweets, LinkedIn posts, YouTube explainers, Reddit discussions.\n"
        "- Weave in at least one case study, at least one listener Q&A snippet, and a brief sponsor read—all integrated naturally.\n\n"

        "Structural guidance (do NOT call these out aloud):\n"
        "  1. Intro + big breakthroughs  \n"
        "  2. Policy/ethics angles  \n"
        "  3. Societal & psychological impacts  \n"
        "  4. Speculative futures  \n"
        "  5. Wrap-up & next steps\n\n"

        "Style & pacing:\n"
        "- Hosts should banter, share personal takes, then dive into facts, and offer reflection on the implications.  \n"
        "- Transitions must flow organically (no “Section 1” labels).  \n"
        "- Include **timestamps (MM:SS)** at each major transition, roughly:\n"
        "    • First segment ~05:00  • Second ~05:00  • Third ~05:00  • Fourth ~05:00  • Wrap & extras ~05–07:00\n\n"

        "**Output**: Return exactly one JSON object matching this schema (no markdown or comments):\n"
        + json.dumps(schema, indent=2)
    )

    # 3) User prompt: the specific topic
    user_prompt = {
        "role": "user",
        "content": f"Here’s today’s topic:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    # 4) Invoke the v1.x chat completions API
    resp = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            user_prompt
        ],
        temperature=0.7,
        max_tokens=10000
    )

    raw = resp.choices[0].message.content

    # 5) Strip any code fences
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

    # 8) Fill blanks
    if not data["title"].strip():
        data["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    if not data["pubDate"].strip():
        data["pubDate"] = now

    return data
