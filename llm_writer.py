# llm_writer.py
import os, re, json, math
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

TARGET_MIN   = 3800            # words  (≈ 20 min @ 190-wpm TTS, or 25 min @ 150-wpm)
TARGET_MAX   = 4400            # give the model some head-room
MAX_ROUNDS   = 3               # attempts to enlarge the script
MODEL        = "gpt-4o-mini"   # you can swap to full gpt-4o if desired

# --------------------------------------------------------------------------- #
# Helper ­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­­ #
def word_count(instr: str | list) -> int:
    if isinstance(instr, list):
        return sum(len(d["text"].split()) for d in instr)
    return len(instr.split())

# --------------------------------------------------------------------------- #
# Main generator
def make_script(topic: str) -> dict:
    """Return a JSON script {title, description, pubDate, dialogue[]}"""
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

    def system_prompt():
        utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        return (
            "You are the senior writer for the two-host podcast **Art and Ingrid Talk A.I.**\n"
            f"Current UTC date/time: {utc_now}\n\n"
            "Goal → deliver a **friendly, engaging, 20-25 min (~3 800-4 400 words)** conversation between Art & Ingrid.\n"
            "· Cover only reputable AI news from the **last 14 days**, citing at least **30 distinct items**\n"
            "· Fold in 1 listener Q&A and 1 short real-world case study\n"
            "· Hosts banter naturally, transitions flow (never name sections)\n"
            "· Target speaking pace ≈ 135 wpm (slightly slower than normal)\n"
            "· Insert timestamps MM:SS whenever the topic clearly changes\n\n"
            "OUTPUT exactly one JSON object that matches this schema (no markdown fences):\n"
            + json.dumps(schema, indent=2)
        )

    user_msg = {
        "role": "user",
        "content": f"Today’s umbrella topic:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    # -------------- round-robin enlargement loop ---------------------------- #
    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": system_prompt()},
            user_msg
        ]
        # On iterations 2+, feed back previous script & ask for expansion
        if draft:
            deficit = TARGET_MIN - word_count(draft["dialogue"])
            messages.append({
                "role": "assistant",
                "content": json.dumps(draft)
            })
            messages.append({
                "role": "user",
                "content": (
                    f"The previous JSON is ≈{word_count(draft['dialogue'])} words "
                    f"({deficit} short of target). Expand it to ~{TARGET_MIN+400} words "
                    "by adding deeper examples, extra banter, additional news items, "
                    "and longer reflective passages—keep timestamps consistent. "
                    "Return the complete *re-written* JSON object."
                )
            })

        resp = openai.chat.completions.create(
            model       = MODEL,
            messages    = messages,
            temperature = 0.7,
            max_tokens  = 9000   # plenty of runway
        )
        raw = resp.choices[0].message.content
        cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.I)

        try:
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"Could not parse JSON (attempt {attempt}):\n{raw}")

        w = word_count(draft["dialogue"])
        if TARGET_MIN <= w <= TARGET_MAX:
            break  # good length
    else:
        print(f"⚠️  Still under target after {MAX_ROUNDS} rounds (≈{w} words) – continuing anyway.")

    # Fill defaults
    if not draft["title"].strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    if not draft["pubDate"].strip():
        draft["pubDate"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    return draft
