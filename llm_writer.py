# llm_writer.py  – auto‑stretch to 7 500–9 000 words (≈ 20‑25 min)
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 7500          # words  → ≈20‑22 min @ 180‑190 wpm
TARGET_MAX   = 9000          # soft ceiling
MAX_ROUNDS   = 4             # expansion attempts if script short
MODEL        = "gpt-4o-mini" # upgrade to gpt-4o if needed

# ──────────────────────────────────────────────────────────────────────────────
def _count_words(dialogue_or_str):
    if isinstance(dialogue_or_str, list):
        return sum(len(turn["text"].split()) for turn in dialogue_or_str)
    return len(str(dialogue_or_str).split())

# ──────────────────────────────────────────────────────────────────────────────
def make_script(topic: str) -> dict:
    """Generate a 20–25 min script JSON for Art and Ingrid Talk A.I."""

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

    base_system = (
        "You are the senior writer for **Art and Ingrid Talk A.I.**
"
        f"Current UTC date: {utc_now}

"
        "Craft a **20–25 min** (~7 500–9 000 words) two‑host conversation (Art & Ingrid).
"
        "● **All content must revolve around the single topic provided** – ignore AI stories that do not clearly relate.
"
        "● Pull at least 30 reputable sources from the last 14 days (news, expert tweets, LinkedIn, YouTube, Reddit) **that support this topic**.
"
        "● Weave in 1 case‑study, 1 listener Q&A, 1 sponsor read.
"
        "● Pacing: slightly slower, natural pauses.
"
        "● Flow organically through breakthroughs → ethics → social impact → futures → wrap; do **not** name sections.
"
        "● Add timestamps MM:SS whenever the topic changes (~5 min blocks).
"
        "After drafting, if <7 500 words, expand with deeper analysis, more anecdotes/Q&A until ≥7 500 words.

"
        "Return exactly one JSON object matching this schema (no markdown fences):
" + json.dumps(schema, indent=2)
    )
        "You are the senior writer for **Art and Ingrid Talk A.I.**\n"
        f"Current UTC date: {utc_now}\n\n"
        "Craft a **20–25 min** (~7 500–9 000 words) two‑host conversation (Art & Ingrid).\n"
        "● Pull at least 30 reputable AI items from the last 14 days (news, X posts, LinkedIn, YouTube, Reddit).\n"
        "● Include 1 case‑study, 1 listener Q&A, 1 sponsor read.\n"
        "● Pacing: slightly slower, natural pauses.\n"
        "● Flow organically through breakthroughs → ethics → social impact → futures → wrap; do **not** name sections.\n"
        "● Add timestamps MM:SS whenever the topic changes (~5 min blocks).\n"
        "After drafting, if <7 500 words, expand with deeper analysis, more anecdotes/Q&A until ≥7 500 words.\n\n"
        "Return exactly one JSON object matching this schema (no markdown fences):\n" + json.dumps(schema, indent=2)
    )

    user_msg = {
        "role": "user",
        "content": f"Topic for today:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        msgs = [{"role": "system", "content": base_system}, user_msg]

        if draft:
            wc = _count_words(draft["dialogue"])
            msgs.extend([
                {"role": "assistant", "content": json.dumps(draft)},
                {"role": "user", "content": (
                    f"Current length ≈ {wc} words (target 7 500–9 000). "
                    "Please expand—add deeper insights, extra news items, richer banter, "
                    "longer reflections—until total word‑count is within the range. "
                    "Return full revised JSON." )}
            ])

        resp = openai.chat.completions.create(
            model       = MODEL,
            messages    = msgs,
            temperature = 0.6,
            max_tokens  = 9000
        )

        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Failed to parse JSON (round {attempt}):\n{raw[:400]}…")

        if TARGET_MIN <= _count_words(draft["dialogue"]) <= TARGET_MAX:
            break  # good length

    # Final field hygiene
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = utc_now

    return draft
