# llm_writer.py – conversational, slow-paced, self-review version
import os, re, json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# ─── Targets ────────────────────────────────────────────────────────────────
TARGET_MIN   = 8000           # words ≈ 24 min @ ~170 wpm
TARGET_MAX   = 9500           # ≈ 28 min upper bound
MAX_ROUNDS   = 4              # expansion / polish loops
MODEL        = "gpt-4o"

# ─── Helpers ────────────────────────────────────────────────────────────────

def wc(dialogue):
    """Word-count of dialogue list"""
    return sum(len(t["text"].split()) for t in dialogue)

# ─── Main ───────────────────────────────────────────────────────────────────

def make_script(topic: str) -> dict:
    """Return polished podcast JSON for Art & Ingrid (≥8k words, 20–25 min)."""

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

    utc_now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    base_system = (
        "You are head writer for the conversational podcast **Art and Ingrid Discuss A.I.**\n"
        f"Current UTC date: {utc_now}\n\n"
        "**Goal**: deliver a **natural, engaging 20–25 min episode** (≈ 8000–9500 words).\n"
        "· Pull **≥30 reputable emerging technology (specifically AI, quantum computing, and robotics) news items** (≤7 days old).\n"
        "· Include exactly one short listener Q&A, one real-world case study.\n"
        "· Hosts Art & Ingrid speak **slightly slower** (stage directions like (pause) allowed).\n"
        "· Organic flow (no pillar labels): intro / breakthroughs → ethics & policy → human impact → futures → wrap.\n"
        "· Insert timestamps MM:SS at topic changes, and light banter between facts.\n"
        "· Return valid JSON per schema below – NO markdown fences.\n\n"
        "After drafting, **self-review**:\n"
        "  a) Ensure dialogue > 8000 words, < 9500 words.\n"
        "  b) Check flow, trim repetition, add connective banter where stiff.\n"
        "  c) Verify no pillar labels, smooth segues, slower pacing cues.\n"
        "If any criteria fail, revise before returning.\n\n"
        "JSON schema:\n" + json.dumps(schema, indent=2)
    )

    user_msg = {
        "role": "user",
        "content": (
            f"Umbrella topic for today’s episode:\n\n{topic}\n\n"
            "Return ONLY the JSON object."
        )
    }

    draft = None
    for attempt in range(1, MAX_ROUNDS + 1):
        messages = [
            {"role": "system", "content": base_system},
            user_msg
        ]

        if draft:
            words_now = wc(draft["dialogue"])
            messages.append({"role": "assistant", "content": json.dumps(draft)})
            messages.append({
                "role": "user",
                "content": (
                    f"Current length ≈ {words_now} words (target 8 000–9 500). "
                    "Improve flow, add fresh banter, new examples, slower-paced reflections, "
                    "until total words are within target and transitions feel seamless. "
                    "Return the full revised JSON."
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
            draft = json.loads(cleaned)
        except json.JSONDecodeError:
            raise RuntimeError(f"⛔ Bad JSON (round {attempt}):\n{raw[:600]}…")

        if TARGET_MIN <= wc(draft["dialogue"]) <= TARGET_MAX:
            break

    # Defaults
    draft.setdefault("pubDate", utc_now)
    if not draft.get("title", "").strip():
        draft["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d %Y')}"
    return draft
