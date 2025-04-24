# llm_writer.py  – robust “retry-until-valid” + auto-expansion
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

MODEL        = "gpt-4o-mini"      # or "gpt-4o"
WORD_TARGET  = 3800              # ≈ 20 min
MAX_ROUNDS   = 6                  # expansion passes
RETRY_LIMIT  = 3                  # regenerate if schema incomplete
MAX_TOKENS   = 9000

schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "pubDate": {"type": "string"},
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

# ---------- helpers -----------------------------------------------------------
def _strip(txt: str) -> str:
    return re.sub(r"^```json\s*|\s*```$", "", txt.strip(), flags=re.I)

def _n_words(dialogue) -> int:
    return sum(len(turn["text"].split()) for turn in dialogue)

def _call(messages):
    resp = openai.chat.completions.create(
        model=MODEL, messages=messages, temperature=0.7, max_tokens=MAX_TOKENS
    )
    return _strip(resp.choices[0].message.content)

def _valid(data: dict) -> bool:
    return all(k in data for k in ("title", "description", "pubDate", "dialogue"))

# ---------- main --------------------------------------------------------------
def make_script(topic: str) -> dict:
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    base_system = f"""
You are the senior writer for **Art and Ingrid Talk A.I.**
Current UTC date: {now}

Craft a **20–25-minute** (≥{WORD_TARGET}-word) two-host script (Art & Ingrid) on the single topic provided.
• Use ≥30 reputable sources ≤7 days old (news, X, LinkedIn, YouTube, Reddit).
• Include 1 case study, listener Q&A, sponsor read.
• Smooth flow: breakthroughs → ethics → social impact → speculative futures → wrap (no labels aloud).
• Add timestamps MM:SS at logical transitions (~5-min blocks).
• After drafting, count words; if below {WORD_TARGET}, expand with more depth/banter until ≥ {WORD_TARGET}.
Return exactly one JSON object that matches this schema:
{json.dumps(schema, indent=2)}
""".strip()

    user_prompt = {
        "role": "user",
        "content": f"Today’s topic (all research must support this):\n\n**{topic}**\n\nReturn only the JSON."
    }

    base_msgs = [
        {"role": "system", "content": base_system},
        user_prompt
    ]

    # 1) first draft with retries until schema complete ------------------------
    cleaned = None
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            cleaned = _call(base_msgs)
            draft = json.loads(cleaned)
            if _valid(draft):
                break
        except json.JSONDecodeError:
            pass  # fall through to retry
        # Ask the model to regenerate with explicit reminder
        base_msgs.append({
            "role": "assistant",
            "content": cleaned or "(no valid JSON returned)"
        })
        base_msgs.append({
            "role": "user",
            "content":
                "Your last answer was incomplete or invalid JSON. "
                "Please regenerate **full valid JSON** including all required keys."
        })
    else:
        raise RuntimeError("Model failed to supply valid JSON with all keys after retries.")

    # 2) iterative expansion to hit word target --------------------------------
    for rnd in range(1, MAX_ROUNDS + 1):
        if _n_words(draft["dialogue"]) >= WORD_TARGET:
            break
        deficit = WORD_TARGET - _n_words(draft["dialogue"])
        expand_msgs = [
            {"role": "system", "content": base_system},
            {"role": "assistant", "content": json.dumps(draft)},
            {"role": "user",
             "content": (
                 f"Current length ≈ {_n_words(draft['dialogue'])} words; "
                 f"need ≥ {WORD_TARGET}. Add at least {deficit + 400} words "
                 "with more details, examples, Q&A, and discussion. Return full JSON."
             )}
        ]
        cleaned = _call(expand_msgs)
        try:
            draft = json.loads(cleaned)
            if not _valid(draft):
                raise ValueError
        except Exception:
            raise RuntimeError("Expansion round yielded invalid JSON; aborting.")

    if _n_words(draft["dialogue"]) < WORD_TARGET:
        raise RuntimeError("Model failed to generate sufficient dialogue after expansion attempts")

    # 3) default fillers -------------------------------------------------------
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = now

    return draft
