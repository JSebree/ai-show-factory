# llm_writer.py

import os
import json
from openai import OpenAI
from openai_function_calling import fetch_news_from_sheet  # your existing helper

# Instantiate the new 1.0.0+ client
client = OpenAI()

def make_script(topic: str) -> dict:
    """
    Returns a dict with keys:
      - title
      - description
      - pubDate
      - dialogue: List of {speaker, text} turns covering the Four Pillars
    """

    # 1) Gather the most up-to-date news
    news_items = fetch_news_from_sheet(
        sheet_id=os.getenv("GSHEET_ID"),
        days_back=30,
        sources=[
            "The New York Times",
            "Wired",
            "MIT Technology Review",
            "BBC News",
            "Reuters",
            "Financial Times"
        ]
    )

    # 2) System prompt with full requirements
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show.  \n"
            "Your job is to craft a 20–25 minute conversational episode about the latest AI news, "
            "with social and philosophical implications, drawing only from reputable sources "
            "published in the last 30 days.  \n\n"

            "Positioning: Bridge bleeding-edge advances (AI, quantum, neurotech) with ethics & social impact.  \n"
            "Four Pillars:  \n"
            "  1. Breakthroughs — concise explainers of top news items.  \n"
            "  2. Governance & Ethics — policy stakes and moral dimensions.  \n"
            "  3. Inner Life & Society — psychological/community impact.  \n"
            "  4. Speculative Futures — economy, philosophy, and what’s next.  \n\n"

            "Format:  \n"
            "- Two hosts (Host A & Host B), friendly and engaging, with real chemistry.  \n"
            "- Dialogue style: back-and-forth, with brief banter but clear emphasis on facts.  \n"
            "- Make tranisitions from section to section smooth and natural.  \n"
            "- Include approximate timestamps (mm:ss) for each Pillar segment, "
            "allocating roughly:  \n"
            "    * Breakthroughs: 5 mins  \n"
            "    * Governance/Ethics: 5 mins  \n"
            "    * Inner Life & Society: 5 mins  \n"
            "    * Speculative Futures: 5 mins  \n"
            "    * Intros, transitions & wrap: 5–7 mins total.  \n\n"

            "Produce exactly valid JSON with these top-level keys:  \n"
            "  • title  \n"
            "  • description  \n"
            "  • pubDate (RFC-2822)  \n"
            "  • dialogue (array of objects: {speaker: str, time: \"mm:ss\", text: str})  \n"
        )
    }

    # 3) User prompt payload
    user = {
        "role": "user",
        "content": json.dumps({
            "topic": topic,
            "news_items": news_items,
            "hosts": ["Host A", "Host B"]
        })
    }

    # 4) Fire the new-chat API
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[system, user],
        temperature=0.7,
        max_tokens=2200
    )

    raw = resp.choices[0].message.content
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}")

    # 5) Ensure we got everything
    required = {"title", "description", "pubDate", "dialogue"}
    if not required.issubset(data.keys()):
        raise RuntimeError(f"Incomplete LLM output: {data.keys()}")

    return data
