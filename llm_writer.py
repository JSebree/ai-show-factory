# llm_writer.py  – auto-expand until dialogue ≥ 3 800 words (~20 min)
import os
import re
import json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# --------------------------- configuration ------------------------------------
MODEL          = "gpt-4o-mini"   # swap to "gpt-4o" if you have quota
WORD_TARGET    = 3800
SAFETY_CAP     = 6               # max expansion rounds
MAX_TOKENS     = 9000           # plenty of runway

# --------------------------- helpers ------------------------------------------
def _words(dialogue):
    """Count total words in the dialogue list."""
    return sum(len(turn["text"].split()) for turn in dialogue)

def _strip_fences(txt: str) -> str:
    return re.sub(r"^```json\\s*|\\s*```$", "", txt.strip(), flags=re.I)

# --------------------------- main entry ---------------------------------------
def make_script(topic: str) -> dict:
    """Return a JSON script for one episode of *Art and Ingrid Talk A.I.*"""

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
    base_system = f"""
You are the senior writer for **Art and Ingrid Talk A.I.**
Current UTC date: {utc_now}

Craft a **20–25-minute** (≥ {WORD_TARGET:,}-word) two-host conversation focused **only** on the topic supplied.
• Pull ≥30 reputable sources <=7 days old (news, X posts, LinkedIn, YouTube, Reddit) supporting the topic.
• Weave in 1 case study, 1 listener Q&A, 1 sponsor read. Speak slightly slower (~160 wpm).
• Flow naturally: breakthroughs → governance/ethics → social/psych impact → speculative futures → wrap.
• Never announce “Section” or “Pillar” out loud. Add timestamps (MM:SS) at logical shifts (~5-min blocks).

After drafting, *count words*. If under {WORD_TARGET:,}, expand with deeper detail, extra anecdotes, longer banter
and more Q&A until ≥ {WORD_TARGET:,}. Return exactly one JSON object matching this schema:
{json.dumps(schema, indent=2)}
""".strip()

    user_prompt = (
        f"Today’s single topic (restrict all research to this):\n\n**{topic}**\n\n"
        "Return only the JSON object."
    )

    def call_llm(msgs):
        resp = openai.chat.completions.create(
            model=MODEL,
            messages=msgs,
            temperature=0.7,
            max_tokens=MAX_TOKENS
        )
        return _strip_fences(resp.choices[0].message.content)

    # -------------------- first draft ----------------------------------------
    base_msgs = [
        {"role": "system", "content": base_system},
        {"role": "user",   "content": user_prompt}
    ]
    cleaned = call_llm(base_msgs)
    draft = json.loads(cleaned)          # will raise if malformed

    # -------------------- iterative expansion --------------------------------
    for round_no in range(1, SAFETY_CAP + 1):
        if _words(draft["dialogue"]) >= WORD_TARGET:
            break  # long enough

        deficit = WORD_TARGET - _words(draft["dialogue"])
        expand_msgs = base_msgs + [
            {"role": "assistant", "content": json.dumps(draft)},
            {"role": "user",
             "content": (
                 f"Current length ≈ {_words(draft['dialogue'])} words "
                 f"({deficit} short of target). Expand by at least {deficit + 400} words "
                 "using more detailed examples, additional news references, richer banter, "
                 "and extended listener Q&A. Return the full updated JSON."
             )}
        ]
        cleaned = call_llm(expand_msgs)
        draft = json.loads(cleaned)

    # Final guard
    if _words(draft["dialogue"]) < WORD_TARGET:
        raise RuntimeError("Script still below word target after expansion rounds.")

    # -------------------- defaults -------------------------------------------
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = utc_now

    return draft
