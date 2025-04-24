# llm_writer.py
import os
import re
import json
import openai
from datetime import datetime, timezone

openai.api_key = os.getenv("OPENAI_API_KEY")


def make_script(topic: str) -> dict:
    """
    Generates a two-host, 20–25 minute podcast script on the given topic.
    Returns a dict with:
      - title       (str)
      - description (str)
      - pubDate     (RFC-2822 str)
      - dialogue    (list of {speaker: str, time: "MM:SS", text: str})
    """
    # 1) JSON schema for final output
    json_schema = {
        "type": "object",
        "properties": {
            "title":       {"type": "string"},
            "description": {"type": "string"},
            "pubDate":     {"type": "string"},
            "dialogue": {
                "type":  "array",
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

    # 2) System prompt guiding outline and expansion
    today = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    system_prompt = f"""
You are a podcast scriptwriter for 'Art and Ingrid talks AI'. Current date: {today}.
Your goal: craft a 20–25 minute, 3800+ word back-and-forth conversation
about the latest AI news and its social & philosophical impact.

STEP 1: Create a detailed outline in JSON with at least 10 bullet points for each of these themes,
plus bullets for Listener Q&A, Case Study Deep Dive, Sponsor Read, and Recap:
  1. Breakthroughs
  2. Governance & Ethics
  3. Inner Life & Society
  4. Speculative Futures
Example outline format:
{{
  "Breakthroughs": ["First bullet", "Second bullet", ...],
  "Governance & Ethics": [...],
  ...
}}

STEP 2: Expand each bullet into a 3–5 sentence dialogue exchange between Art & Ingrid,
including approximate timestamps (MM:SS) at the start of each section.

STEP 3: After drafting, count total words. If under 3800 words, automatically add more
examples, anecdotes, Q&A, sponsor reads, or deeper dives until word count >= 3800.

Return ONLY the final script as valid JSON matching this schema (no markdown, no commentary):
""" + json.dumps(json_schema)

    # 3) User prompt with topic
    user_prompt = f"Topic: {topic}"

    # 4) Call the OpenAI API with high token limit
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=6000
    )

    raw = resp.choices[0].message.content

    # 5) Strip any JSON fences
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}")

    # 7) Validate output keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"Missing field from LLM output: {key}")

    return data
