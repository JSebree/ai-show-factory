# llm_writer.py – conversational, iterative‑lens, slow‑paced, self‑review
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 8000   # words ≈ 24–26 min @ ~170 wpm
TARGET_MAX   = 9500   # upper safety limit
MAX_ROUNDS   = 4      # expansion / polish loops
MODEL        = "gpt-4o"

# ─── Helper ────────────────────────────────────────────────────────────────

def wordcount(dlg):
    return sum(len(turn["text"].split()) for turn in dlg)

# ─── Main ──────────────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Return podcast JSON hitting 20–25 min with per‑article 4‑lens flow."""

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

    system_base = (
        "You are head writer for the conversational podcast **Art and Ingrid Discuss A.I.**\n"
        f"UTC date: {utc_now}\n\n"
        "**Runtime goal:** 20–25 min (≈ 8000–9500 words) at a relaxed, slower pace.\n"
        "• Pull at least **30** reputable emreging tech (specifically AI, quantum computing, and robotics) news items from the last **7 days**.\n"
        "• For **each** news item follow this conversational micro‑structure (NEVER say the headings aloud):\n"
        "   1⃣  \*Breakthrough angle\*: Art introduces headline & core technical takeaway.\n"
        "   2⃣  \*Ethics / Policy\*: Ingrid reacts with governance or legal perspective.\n"
        "   3⃣  \*Human impact\*: hosts discuss real‑world or psychological implications.\n"
        "   4⃣  \*Futures\*: both speculate on long‑term possibilities.\n"
        "   ▸ Move on to next item with a natural segue + short banter (≈10‑15 s).\n"
        "• Sprinkle exactly one listener Q&A, one sponsor read, one 60‑sec case study in context.\n"
        "• Insert timestamps (MM:SS) at the first line of *each new news item*.\n"
        "• Stage directions like (pause) / (laughs softly) allowed to slow rhythm.\n\n"
        "After drafting, **self‑review**: ensure 8000‑9500 words, no repetitive phrasing, smooth flow, wrap‑up only at end."
    )

    user_msg = {
        "role": "user",
        "content": (
            f"Umbrella topic for today’s episode:\n\n{topic}\n\n"
            "Return ONLY the JSON object."
        )
    }

    script = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": system_base},
            user_msg
        ]
        if script:
            w = wordcount(script["dialogue"])
            messages.append({"role": "assistant", "content": json.dumps(script)})
            messages.append({
                "role": "user",
                "content": (
                    f"Current draft = {w} words. Expand with extra anecdotes, reflections, slower banter, "
                    f"until total falls between {TARGET_MIN} and {TARGET_MAX}. Polish any stiffness. "
                    "Return full revised JSON."
                )
            })

        resp = openai.chat.completions.create(
            model       = MODEL,
            messages    = messages,
            temperature = 0.55,
            max_tokens  = 9500
        )
        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            script = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"JSON parse error (round {attempt})")

        if TARGET_MIN <= wordcount(script["dialogue"]) <= TARGET_MAX:
            break

    script.setdefault("pubDate", utc_now)
    if not script.get("title", "").strip():
        script["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    return script
