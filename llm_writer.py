# llm_writer.py
import os
import re
import json
from datetime import datetime, timezone
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def make_script(topic: str) -> dict:
    """
    Returns a dict with keys:
      - title       (str)
      - description (str)
      - pubDate     (RFC-2822 str)
      - dialogue    (list of {speaker, time, text})
    """
    # 1) JSON schema for validation
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

        STEP 2: Expand each bullet into a 3–5 sentence friendly and engaging dialogue exchange between Art & Ingrid, with genuine chemistry,
        including approximate timestamps (MM:SS) at the start of each section. Smooth, un-labeled transitions between topics

        STEP 3: After drafting, count total words. If under 3800 words, automatically add more
        examples, anecdotes, Q&A, sponsor reads, or deeper dives until word count >= 3800.

        Return ONLY the final script as valid JSON matching this schema (no markdown, no commentary):
        """ + json.dumps(json_schema)
    
    # 3) User prompt: the specific topic
    user = {
        "role": "user",
        "content": f"Here’s today’s topic:\n\n**{topic}**\n\nReturn only the JSON object."
    }

    # 4) Invoke the API
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            system,
            {"role": "system", "content": json.dumps(schema)},
            user
        ],
        temperature=0.7,
        max_tokens=6000
    )
    raw = resp.choices[0].message.content

    # 5) Strip code-fences if any
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}")

    # 7) Validate keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    # 8) Fill defaults if blank
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    if not data["title"].strip():
        data["title"] = f"{topic} — {datetime.now(timezone.utc).strftime('%b %d, %Y')}"
    if not data["pubDate"].strip():
        data["pubDate"] = now

    return data
