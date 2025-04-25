# llm_writer.py – iterative script generator (30‑news, per‑item 4‑lens, 8–9.5 k words)
import os, json, re
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# ─── Tunables ─────────────────────────────────────────────────────────────
TARGET_MIN   = 8000        # ≈ 24 min at ~170 wpm
TARGET_MAX   = 9500        # ≈ 28 min upper cap
MAX_ROUNDS   = 6            # self‑expansion / polish loops
MODEL        = "gpt-4o"  # upgrade to gpt‑4o if quota allows

# ─── Helpers ──────────────────────────────────────────────────────────────

def word_count(dialogue):
    """Return total words in the dialogue list (safe if key missing)."""
    if not isinstance(dialogue, list):
        return 0
    return sum(len(turn.get("text", "").split()) for turn in dialogue)

# ─── Main entry ───────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Generate ≥8 000‑word two‑host script following 4‑lens cycle per article."""

    schema = {
        "type": "object",
        "properties": {
            "title":       {"type": "string"},
            "description": {"type": "string"},
            "pubDate":     {"type": "string"},
            "dialogue":    {
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

    base_sys = f"""
You are the senior writer for **Art and Ingrid Talk A.I.**
UTC date: {utc_now}

Goal: craft a **natural, engaging 20–25 min** (≈ 8–9.5 k‑word) two‑host episode.
• Harvest **≥30** reputable emerging tech (specifically AI, quantum computing, and robotics) news items from the last **7 days**.
• For **each** story, have Art & Ingrid discuss it through four lenses in order: breakthrough → ethics/policy → human impact → futures (do **not** say the headings aloud).
• Add light banter / pauses so delivery feels slightly slower.
• Include at least one listener Q&A, one 60‑second real case study (≈15 s).
• Insert timestamps MM:SS at the first line of every new news item.
• After writing, **self‑review**: if word‑count < {TARGET_MIN} or > {TARGET_MAX}, information is repeated, hosts begin wrapping before the end of podcast, or any required keys missing, expand / trim until compliant.

Return a single JSON object matching this schema with **NO** markdown fences:
{json.dumps(schema)}
"""

    user_msg = {
        "role": "user",
        "content": (
            f"Today’s umbrella topic:\n\n{topic}\n\n"
            "Return ONLY the JSON object."
        )
    }

    draft = None
    for _ in range(MAX_ROUNDS):
        messages = [
            {"role": "system", "content": base_sys},
            user_msg
        ]

        # If a draft exists, feed it back for expansion/refinement
        if draft is not None:
            words = word_count(draft.get("dialogue", []))
            messages.append({"role": "assistant", "content": json.dumps(draft)})
            messages.append({
                "role": "user",
                "content": (
                    f"Current length ≈ {words} words. Target {TARGET_MIN}–{TARGET_MAX}. "
                    "Polish flow, add more stories, banter & reflections, and ensure all schema keys exist."
                )
            })

        resp = openai.chat.completions.create(
            model = MODEL,
            messages = messages,
            temperature = 0.55,
            max_tokens = 9500,
            response_format = {"type": "json_object"}
        )

        try:
            content = resp.choices[0].message.model_dump()["content"]
            draft = json.loads(content) if isinstance(content, str) else content
        except Exception:
            draft = {}

        # Basic validation -------------------------------------------------
        if not all(k in draft for k in ("title", "description", "pubDate", "dialogue")):
            continue  # missing keys → another round
        if not isinstance(draft["dialogue"], list) or not draft["dialogue"]:
            continue  # empty dialogue → retry
        words = word_count(draft["dialogue"])
        if TARGET_MIN <= words <= TARGET_MAX:
            break  # success

    # Fallback defaults ----------------------------------------------------
    draft.setdefault("pubDate", utc_now)
    if not draft.get("title", "").strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    draft.setdefault("description", f"Conversation on {topic} and its implications.")

    return draft
