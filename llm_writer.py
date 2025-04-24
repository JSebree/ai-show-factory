import os
import re
import json
import openai

# Load your OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OPENAI_API_KEY environment variable is not set.")


def make_script(topic: str) -> dict:
    """
    Fetch the latest AI news on `topic` from reputable sources (last 30 days),
    and format as a co-host dialogue JSON using the four-pillar structure.

    Returns:
        {
          "title": "<episode title>",
          "description": "<one-sentence summary>",
          "pubDate": "<RFC-822 date>",
          "dialogue": [
             {"timestamp": "00:00", "speaker": "Host A", "text": "..."},
             ...
          ]
        }
    """
    # System prompt for voice/personality
    system_prompt = (
        "You are NewsCaster, an expert at summarizing the latest AI developments in a friendly, engaging "
        "co-host podcast format with impeccable host chemistry. Always ground your conversation in facts from "
        "only reputable news outlets."
    )

    # User prompt with detailed instructions
    user_prompt = f"""
1. Read the current episode topic: {topic}
2. Search for and gather the 5–7 most important news items about this topic published in the last 30 days, only from reputable sources (Reuters, AP, BBC, MIT Technology Review, Wired, The Guardian, NYT, Bloomberg).
3. For each item, capture the headline, source name, date, and one-sentence fact summary.
4. Write a 20–25 minute episode script as a dialogue between Host A and Host B, with timestamps and this structure:
   • 00:00–02:00  Intro & Topic Setup
   • 02:00–06:00  Pillar 1 (Breakthroughs)
   • 06:00–11:00  Pillar 2 (Governance & Ethics)
   • 11:00–17:00  Pillar 3 (Inner Life & Society)
   • 17:00–21:00  Pillar 4 (Speculative Futures)
   • 21:00–22:00  Wrap & Tease
5. Dialogue should be lively, personable, teasing, but fact-focused.
6. Cite each fact with (Source, YYYY‑MM‑DD).
7. Output ONLY valid JSON exactly matching this schema (no markdown):
```json
{{
  "title": "...",
  "description": "...",
  "pubDate": "...",
  "dialogue": [
    {{"timestamp":"00:00","speaker":"Host A","text":"..."}},
    ...
  ]
}}
```
"""

    # Call the Chat API
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=1500
    )

    raw = response.choices[0].message.content.strip()
    # Remove markdown fences if present
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}")

    # Validate schema keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"Missing key in LLM output: {key}")

    return data
