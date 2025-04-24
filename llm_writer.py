# llm_writer.py – iterative expansion to hit 20‑25 min (≈ 7 500–9 000 words)
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 7500   # ≈ 20 min @ 160‑170 wpm
TARGET_MAX   = 9000   # stay within model limit
MAX_ROUNDS   = 6       # expansion / fix‑up attempts
MODEL        = "gpt-4o-mini"  # adjust if you have quota for gpt‑4o

# ─── helpers ────────────────────────────────────────────────────────────────

def _count_words(dialogue):
    """Return total words in a dialogue list (0 if missing/empty)."""
    if not isinstance(dialogue, list):
        return 0
    return sum(len(turn.get("text", "").split()) for turn in dialogue)

# ─── main entry ─────────────────────────────────────────────────────────────

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

    # System prompt
    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    base_system = f"""
You are the senior writer for **Art and Ingrid Talk A.I.**  
Current UTC date: {utc_now}

**Goal**: craft a **20–25 minute** (7500–9000‑word) two‑host conversation focused **exclusively** on the topic provided.  
• Use ≥30 reputable sources from the last **14 days** (news, X, LinkedIn, YouTube, Reddit) that directly support the topic.  
• Include: 1 case study, 1 listener Q&A, 1 brief sponsor read.  
• Flow naturally—no pillar labels spoken.  
• Hosts (Art & Ingrid) speak slightly slower (~160 wpm) with natural pauses and chemistry.  
• Insert approximate timestamps (MM:SS) at logical shifts (~5‑minute blocks).  

After drafting, **count words**.  
If **< {TARGET_MIN} words** OR dialogue list is empty, expand with deeper dives, extra examples, anecdotes, or audience Q&A until ≥{TARGET_MIN}.  
If **> {TARGET_MAX} words**, trim fat.  
Return exactly one JSON object matching this schema (no markdown fences or commentary):
{json.dumps(schema, indent=2)}
"""

    user_msg = {
        "role": "user",
        "content": (
            "Today’s single topic (limit all research to this):\n\n"
            f"**{topic}**\n\n"
            "Return only the JSON object."
        )
    }

    draft = {}  # will hold latest attempt

    for round_no in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": base_system},
            user_msg
        ]

        # If we already have a draft but it’s too short or empty, feed it back for expansion
        if draft:
            words = _count_words(draft.get("dialogue"))
            if words < TARGET_MIN:
                messages.extend([
                    {"role": "assistant", "content": json.dumps(draft)},
                    {"role": "user", "content": f"Current length ≈{words} words (round {round_no}). Expand to ≥{TARGET_MIN} words and ensure dialogue is populated."}
                ])
            else:
                # Length is OK; stop iterating
                break

        resp = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.6,
            max_tokens=9000
        )
        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            # Force another round requesting valid JSON
            draft = {}
            continue

        # Loop back if dialogue empty – treat like <TARGET_MIN
        if not draft.get("dialogue"):
            draft["dialogue"] = []

    # Final sanity
    if _count_words(draft.get("dialogue")) < TARGET_MIN:
        raise RuntimeError("Model failed to generate sufficient dialogue after expansion attempts")

    if not draft.get("title"):
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft.get("pubDate"):
        draft["pubDate"] = utc_now

    return draft
