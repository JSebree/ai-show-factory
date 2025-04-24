# llm_writer.py
import os
import json
from openai import OpenAI

# Instantiate the v1 client
client = OpenAI()

def make_script(topic: str) -> dict:
    """
    Returns a dict with:
      - title
      - slug
      - description
      - full_script
      - pubDate
    as JSON output from the model.
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
  PubDate: today’s date in RFC-822 (e.g. “Wed, 24 Apr 2025 12:00:00 GMT”)

Return **only** a single JSON object—no extra prose or Markdown.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        temperature=0.7,
    )

    # The assistant’s content is guaranteed to be pure JSON
    return json.loads(response.choices[0].message.content)
