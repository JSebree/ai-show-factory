# llm_writer.py – full replacement
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# ─── Runtime targets ─────────────────────────────────────────────────────────
TARGET_MIN   = 7500          # words ≈ 22 min @ ~170–180 wpm
TARGET_MAX   = 9000          # soft ceiling (~26 min)
MAX_ROUNDS   = 4             # up‑to four passes of self‑expansion
MODEL        = "gpt-4o-mini" # or "gpt-4o" if you have quota

# ─── Helper ──────────────────────────────────────────────────────────────────

def dialogue_wordcount(dlg):
    """Total words across all dialogue text."""
    return sum(len(turn["text"].split()) for turn in dlg)

# ─── Main function ───────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Generate a ≥7500‑word, 20–25 min podcast script for Art & Ingrid."""

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

    def base_system_prompt():
        utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        return (
            "You are the senior scriptwriter of the show **Art and Ingrid Discuss A.I.**\n"
            f"UTC date: {utc_now}\n\n"
            "Write a **20–25 minute** (≈ 7500–9000‑word) two‑host conversation.\n"
            "Requirements: • 30+ reputable emerging tech (specfically AI, quantum computing, and robotics) news "
            "items (≤7 days old) • 1 listener Q&A • 1 sponsor read • 1 short case study.\n"
            "Hosts Art & Ingrid banter, speak a little slower, keep transitions natural (never name pillars).\n"
            "Implicit flow: intro/breakthroughs → ethics/policy → societal impact → speculative futures → wrap.\n"
            "Insert timestamps (MM:SS) at major topic changes.\n\n"
            "Return exactly one JSON object that matches this schema:\n" + json.dumps(schema, indent=2)
        )

    user_msg = {
        "role": "user",
        "content": f"Today’s umbrella topic:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        msgs = [
            {"role": "system", "content": base_system_prompt()},
            user_msg
        ]

        if draft:
            wc = dialogue_wordcount(draft["dialogue"])
            msgs.append({"role": "assistant", "content": json.dumps(draft)})
            msgs.append({
                "role": "user",
                "content": (
                    f"Current script ≈{wc} words (target ≥{TARGET_MIN}). "
                    "Expand it—add deeper analysis, extra anecdotes, more listener Q&A, "
                    "and additional credible news references—until total words lie between "
                    f"{TARGET_MIN} and {TARGET_MAX}. Return the full updated JSON."
                )
            })

        resp = openai.chat.completions.create(
            model       = MODEL,
            messages    = msgs,
            temperature = 0.6,
            max_tokens  = 9500
        )

        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Bad JSON (round {attempt}):\n{raw[:500]}…")

        if TARGET_MIN <= dialogue_wordcount(draft["dialogue"]) <= TARGET_MAX:
            break  # good length

    # Fallbacks
    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    draft.setdefault("pubDate", utc_now)
    if not draft.get("title", "").strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"

    return draft
