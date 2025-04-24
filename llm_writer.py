# llm_writer.py
import os, json
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def make_script(topic: str) -> dict:
    """
    Returns a JSON dict with keys:
      - title
      - slug
      - description
      - full_script   (the full dialogue)
      - pubDate       (RFC-822 date string)
    The script is written as a dialogue between two co-hosts:
      Host A and Host B.
    It follows this structure:
      Positioning + the Four Pillars:
        1. Breakthroughs
        2. Governance/Ethics
        3. Inner Life & Society
        4. Speculative Futures
    """
    system = (
        "You are a professional podcast scriptwriter. "
        "You generate a conversational dialogue between two hosts (\"Host A\" and \"Host B\"). "
        "Use a friendly, natural back-and-forth style, but stay on topic."
    )

    user = f"""
Topic: {topic}

Structure your script like this:

Positioning:
  Bridge bleeding-edge advances (AI, quantum, neurotech) with ethics & social impact.

• Four Pillars:
  1. Breakthroughs – concise explainer.
  2. Governance/Ethics – policy stakes.
  3. Inner Life & Society – psychology, community.
  4. Speculative Futures – economy, philosophy.

Write the full dialogue, labeling each turn:

Host A: …
Host B: …

At the top, supply:
  Title: a catchy episode title
  Description: a one-sentence summary
  PubDate: today’s date in RFC-822 (e.g. “Wed, 23 Apr 2025 12:00:00 GMT”)

Return your entire response as a single JSON object. Do NOT wrap it in Markdown or any extra text.
"""

    res = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ],
        temperature=0.7,
    )

    # the assistant message is pure JSON
    return json.loads(res.choices[0].message.content)

