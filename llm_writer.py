# llm_writer.py – ensures 20–25 min (~7 500‑9 000 words)
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 7_500   # words ≈ 20 min @ 160‑170 wpm
TARGET_MAX   = 9_000   # stay within token budget
MAX_ROUNDS   = 4       # expansion attempts
MODEL        = "gpt-4o-mini"  # upgrade if quota permits

# ────────────────────────────────────────────────────────────

def _count_words(dialogue):
    return sum(len(turn["text"].split()) for turn in dialogue)

# ────────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Generate a single‑topic episode script for *Art and Ingrid Talk A.I.*"""

    # JSON schema
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

    # Base system prompt (triple‑quoted f‑string for safety)
    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    base_system = f"""
You are the senior writer for **Art and Ingrid Talk A.I.**
Current UTC date: {utc_now}
Create a **20–25‑minute** (7 500–9 000 word) two‑host conversation between Art & Ingrid.
• Focus exclusively on this single topic (ignore unrelated news).
• Pull **≥30** reputable sources from the last **14 days** (news, X/tweets, LinkedIn, YouTube, Reddit) that directly support the topic.
• Weave in: 1 case study, 1 listener Q&A, 1 brief sponsor read. Flow naturally—no rigid labels.
• Organic progression: breakthroughs → governance & ethics → inner life & society → speculative futures → wrap‑up.
• Hosts banter, think aloud, speak slightly slower (~160 wpm). No pillar names spoken.
• Insert approximate timestamps (MM:SS) when shifting focus (~5‑minute blocks).
After drafting, count words; if <7 500, expand with deeper analysis, anecdotes, or extra Q&A until ≥7 500. If >9 000, trim.
Return exactly one JSON object conforming to this schema (no markdown fences):
{json.dumps(schema, indent=2)}
"""

    user_msg = {
        "role": "user",
        "content": (
            "Today’s topic (limit all research to this):\n\n"
            f"**{topic}**\n\n"
            "Return only the JSON object."
        )
    }

    draft = None
    for round_no in range(1, MAX_ROUNDS + 1):
        msgs = [
            {"role": "system", "content": base_system},
            user_msg
        ]
        if draft:
            wc = _count_words(draft["dialogue"])
            msgs.extend([
                {"role": "assistant", "content": json.dumps(draft)},
                {"role": "user", "content": f"Current length ≈{wc} words; need at least {TARGET_MIN}. Please expand."}
            ])

        resp = openai.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=0.6,
            max_tokens=9_000
        )
        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse JSON (round {round_no})")

        words = _count_words(draft["dialogue"])
        if TARGET_MIN <= words <= TARGET_MAX:
            break  # good length

    # Final hygiene
    if not draft.get("title", "").strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft.get("pubDate", "").strip():
        draft["pubDate"] = utc_now

    return draft
