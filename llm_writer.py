# llm_writer.py – conversational iterative version with per‑news 4‑lens flow and robust key checks
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# ─── Runtime targets ─────────────────────────────────────────────────────
TARGET_MIN   = 8000   # words  (≈ 24 min at ~170 wpm)
TARGET_MAX   = 9500   #        (≈ 28 min safety ceiling)
MAX_ROUNDS   = 4       # self‑expansion / polish loops
MODEL        = "gpt-4o"  # swap for "gpt-4o" if quota allows

# ─── Helper ──────────────────────────────────────────────────────────────

def wc(dialogue):
    """Return total word‑count of the dialogue list (safe if missing)."""
    if not isinstance(dialogue, list):
        return 0
    return sum(len(t.get("text", "").split()) for t in dialogue)

# ─── Main ────────────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Generate ≥8 000‑word two‑host script following 4‑lens cycle per article."""

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

    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    system_prompt = (
        "You are head writer for the friendly conversational podcast **Art and Ingrid Talk A.I.**\n"
        f"UTC date: {utc_now}\n\n"
        "**Runtime goal**: 20–25 min (≈ 8000–9500 words) at a relaxed, slower pace.\n"
        "• Pull **≥30** reputable emerging tech (specifically AI, quantum computing, and robotics) news items from the last **7 days**.\n"
        "• For **each** item have the hosts walk sequentially through: breakthrough, ethics/policy, human impact, futures.\n"
        "• Do **not** state those headings aloud – just converse.\n"
        "• Natural segues + light banter (~10 s) between items.\n"
        "• Include exactly one listener Q&A, one 60‑s case study, one brief sponsor read.\n"
        "• Insert timestamps (MM:SS) at the first line for each new news item.\n"
        "• After drafting, self‑review length & flow; expand/trim until word‑count within target, no repetition, all required keys present.\n\n"
        "Return a single JSON object matching this schema exactly (no markdown):\n"
        + json.dumps(schema, indent=2)
    )

    user_prompt = {
        "role": "user",
        "content": (
            f"Today’s umbrella topic:\n\n{topic}\n\n"
            "Return ONLY the JSON object."
        )
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": system_prompt},
            user_prompt
        ]

        # If we already have a draft, ask for expansion / fixes
        if draft is not None:
            words_now = wc(draft.get("dialogue", []))
            messages.append({"role": "assistant", "content": json.dumps(draft)})
            messages.append({
                "role": "user",
                "content": (
                    f"Current draft ≈ {words_now} words. Target {TARGET_MIN}–{TARGET_MAX}.\n"
                    "Expand with additional news items, slower banter, deeper analysis, and ensure the JSON contains the keys:"
                    " title, description, pubDate, dialogue (non‑empty). Return the full revised JSON."
                )
            })

        resp = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.55,
            max_tokens=9500
        )
        raw = resp.choices[0].message.content.strip()
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            draft = {}

        # --- validation ----------------------------------------------------
        missing_keys = [k for k in ("title", "description", "pubDate", "dialogue") if k not in draft]
        if missing_keys:
            continue  # request another round
        if not isinstance(draft["dialogue"], list) or not draft["dialogue"]:
            continue  # invalid dialogue, regenerate
        words = wc(draft["dialogue"])
        if TARGET_MIN <= words <= TARGET_MAX:
            break  # success

    # Final sanity defaults ---------------------------------------------------
    draft.setdefault("pubDate", utc_now)
    if not draft.get("title", "").strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    draft.setdefault("description", f"Conversation on {topic} and its implications.")

    return draft
