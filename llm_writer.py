# llm_writer.py
import os, re, json, math
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 3800          # ≈ 20 min @ ~190 wpm TTS
TARGET_MAX   = 4400          # soft upper guard-rail
MAX_ROUNDS   = 3             # extra “expansion” passes if short
MODEL        = "gpt-4o-mini" # swap to gpt-4o for even richer output

# ──────────────────────────────────────────────────────────────────────────── #
def words(obj) -> int:
    """Count words in dialogue list or plain string."""
    if isinstance(obj, list):
        return sum(len(d["text"].split()) for d in obj)
    return len(obj.split())

# ──────────────────────────────────────────────────────────────────────────── #
def make_script(topic: str) -> dict:
    """Return podcast JSON {title, description, pubDate, dialogue[]}"""
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
    common_system = (
        "You are the senior scriptwriter for **Art and Ingrid Talk A.I.**\n"
        f"Current UTC date: {utc_now}\n\n"
        "❑ **Runtime target:** 20–25 min (≈ 3 800–4 400 words, ~135 wpm pace).\n"
        "❑ **Hosts:** Art & Ingrid – warm chemistry, light banter, then fact-rich discussion.\n"
        "❑ **Sources:** Pull at least **30** reputable AI items (news, peer tweets, LinkedIn posts, "
        "YouTube clips, Reddit threads) published **≤ 14 days** ago.\n"
        "❑ **Mandatory elements:** 1 case-study deep dive • 1 listener Q&A.\n\n"
        "❑ **Flow (no section labels in dialogue):**\n"
        "   • Intro & big breakthroughs\n"
        "   • Policy / ethics angles\n"
        "   • Societal & psychological impacts\n"
        "   • Speculative futures\n"
        "   • Wrap-up + next steps\n\n"
        "❑ Insert **timestamps (MM:SS)** at each natural transition; aim ~5 min per core block.\n"
        "❑ After drafting, if word-count < 3 800, **expand** by adding extra anecdotes, deeper analysis, "
        "or more Q&A until ≥ 3 800 words.\n\n"
        "Return **only** a JSON object matching this schema:\n"
        + json.dumps(schema, indent=2)
    )

    user_msg = {
        "role": "user",
        "content": f"Today’s umbrella topic:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [{"role": "system", "content": common_system}, user_msg]

        if draft:
            deficit = TARGET_MIN - words(draft["dialogue"])
            messages.extend([
                {"role": "assistant", "content": json.dumps(draft)},
                {
                    "role": "user",
                    "content": (
                        f"The previous script is about {words(draft['dialogue'])} words "
                        f"({deficit} short of target). Enrich it – add more news items, "
                        "longer reflections, extra banter, extended listener Q&A – until "
                        "total words fall between 3 800 and 4 400. Return the full revised JSON."
                    )
                }
            ])

        resp = openai.chat.completions.create(
            model       = MODEL,
            messages    = messages,
            temperature = 0.65,
            max_tokens  = 9000
        )

        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)

        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Could not parse JSON (attempt {attempt}):\n{raw}")

        wc = words(draft["dialogue"])
        if TARGET_MIN <= wc <= TARGET_MAX:
            break  # success

    # Final hygiene
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = utc_now

    return draft
