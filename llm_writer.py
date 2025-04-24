# llm_writer.py
import os
import re
import json
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def make_script(topic: str) -> dict:
    """
    Returns a dict with keys:
      - title (str)
      - description (str)
      - pubDate (RFC2822 str)
      - dialogue (list of {speaker,text})
    """
    # 1) Define the JSON schema we want
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
                        "text":    {"type": "string"}
                    },
                    "required": ["speaker", "text"]
                }
            }
        },
        "required": ["title", "description", "pubDate", "dialogue"]
    }

    # 2) Build our system + user prompt
    messages = [
        {"role": "system", "content":
            "You are a podcast co-host writer.  Produce a JSON object (no extra keys) as defined by the following schema:"},
        {"role": "system", "content": json.dumps(json_schema)},
        {"role": "user", "content":
            f"""Please write a conversational, two-voice podcast script on this topic:
**{topic}**

Use this structure:
- Positioning: Bridge bleeding-edge advances (AI, quantum, neurotech) with ethics & social impact.
- Four Pillars:
  1. Breakthroughs – concise explainer.
  2. Governance/Ethics – policy stakes.
  3. Inner Life & Society – psychology, community.
  4. Speculative Futures – economy, philosophy.

Return **only** valid JSON (no markdown or commentary)."""}
    ]

    # 3) Call the new API
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=1000
    )

    raw = resp.choices[0].message.content

    # 4) Strip any code fences or leading/trailing junk
    #    e.g. ```json { … } ```
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}") from e

    # 5) Final sanity check
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    return data
