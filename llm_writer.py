# llm_writer.py  – auto‑stretch to 7 500–9 000 words (≈ 20‑25 min)
import os
import re
import json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 7_500          # words ≈ 20‑22 min @ ~180 wpm
TARGET_MAX   = 9_000          # soft ceiling so we do not exceed token limits
MAX_ROUNDS   = 4              # expansion attempts if the first draft is short
MODEL        = "gpt-4o-mini" # upgrade to gpt-4o if you have the quota

# ─────────────────────────────────────────────────────────────

def _count_words(dialogue_or_str):
    """Utility to count words either in a whole string or a dialogue array."""
    if isinstance(dialogue_or_str, list):
        return sum(len(turn["text"].split()) for turn in dialogue_or_str)
    return len(str(dialogue_or_str).split())

# ─────────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Return a fully‑formed JSON script for one episode of *Art and Ingrid Talk A.I.*"""

    # 1. JSON schema the model must respect
    schema = {
        "type": "object",
        "properties": {
            "title":       {"type": "string"},
            "description": {"type": "string"},
            "pubDate":     {"type": "string"},  # RFC‑2822
            "dialogue": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {"type": "string"},
                        "time":    {"type": "string"},  # MM:SS
                        "text":    {"type": "string"}
                    },
                    "required": ["speaker", "time", "text"]
                }
            }
        },
        "required": ["title", "description", "pubDate", "dialogue"]
    }

    # 2. System prompt with exhaustive instructions
    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    base_system = (
        "You are the senior writer for **Art and Ingrid Talk A.I.**\n"
        f"Current UTC date: {utc_now}\n\n"
        "Craft a **20–25 minute** (~7 500–9 000 word) two‑host conversation between *Art* and *Ingrid*.\n"
        "● *All* content must revolve around the single topic provided – ignore news that does not clearly relate.\n"
        "● Pull **at least 30** reputable AI items from the last **14 days** (news outlets, expert tweets/X posts, LinkedIn insights, YouTube explainers, Reddit discussions) that **support this topic**.\n"
        "● Weave in 1 case study, 1 listener Q&A, and 1 brief sponsor read – naturally, not as rigid segments.\n"
        "● Pacing: slightly slower – imagine ~160–170 wpm with natural pauses.\n"
        "● Flow organically: breakthroughs → governance & ethics → inner life & society → speculative futures → wrap‑up. **Do NOT** say the section names out loud.\n"
        "● Insert approximate timestamps (MM:SS) whenever the topic shifts (roughly every 5 minutes).\n"
        "After drafting, count total words; if under 7 500, automatically expand with deeper analysis, additional anecdotes, or richer banter until ≥7 500 words. If over 9 000, tighten slightly.\n\n"
        "Return exactly one JSON object matching this schema (no markdown fences):\n" + json.dumps(schema, indent=2)
    )

    # 3. User message containing today’s topic
    user_msg = {
        "role": "user",
        "content": (
            "Today’s topic (focus all research on this):\n\n"
            f"**{topic}**\n\n"
            "Return only the JSON object."
        )
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": base_system},
            user_msg
        ]

        # If we already have a draft that is too short, send it back for expansion
        if draft:
            wc = _count_words(draft["dialogue"])
            messages.extend([
                {"role": "assistant", "content": json.dumps(draft)},
                {"role": "user", "content": (
                    f"Current length ≈ {wc} words (target 7 500–9 000). Please expand: add more source‑backed details, deeper discussion, richer banter, additional anecdotes/Q&A until length is in range. Return full revised JSON." )}
            ])

        resp = openai.chat.completions.create(
            model        = MODEL,
            messages     = messages,
            temperature  = 0.6,
            max_tokens   = 9_000
        )

        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse JSON from LLM (round {attempt}):\n{raw[:400]}…")

        words = _count_words(draft["dialogue"])
        if TARGET_MIN <= words <= TARGET_MAX:
            break  # reached acceptable length – stop iterating

    # 4. Final field hygiene
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = utc_now

    return draft
