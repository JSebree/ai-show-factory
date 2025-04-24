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
      - title (str)
      - description (str)
      - pubDate (RFC-2822 str)
      - dialogue (list of {speaker, time, text})
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
                        "time":    {"type": "string"},
                        "text":    {"type": "string"}
                    },
                    "required": ["speaker", "time", "text"]
                }
            }
        },
        "required": ["title", "description", "pubDate", "dialogue"]
    }

    # 2) Build our system + user prompts
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show.  \n"
            "Your job is to craft a 20–25 minute conversational episode about the latest AI news, "
            "with social and philosophical implications, drawing only from reputable sources "
            "published in the last 14 days.  \n\n"

            "Positioning: Bridge bleeding-edge advances (AI, quantum, neurotech) with ethics & social impact.  \n"
            "Four Pillars:  \n"
            "  1. Breakthroughs — concise explainers of top news items.  \n"
            "  2. Governance & Ethics — policy stakes and moral dimensions.  \n"
            "  3. Inner Life & Society — psychological and community impact.  \n"
            "  4. Speculative Futures — economy, philosophy, and what’s next.  \n\n"

            "Format:  \n"
            "- Two hosts: Art & Ingrid, friendly and engaging, with real chemistry.  \n"
            "- Dialogue style: back-and-forth, with brief banter but clear emphasis on facts.  \n"
            "- Smooth, natural transitions between sections.  \n"
            "- Include approximate timestamps (mm:ss) for each Pillar segment, allocating roughly:  \n"
            "    * Breakthroughs: 05:00  \n"
            "    * Governance & Ethics: 05:00  \n"
            "    * Inner Life & Society: 05:00  \n"
            "    * Speculative Futures: 05:00  \n"
            "    * Intros, transitions & wrap: 05–07 minutes total.  \n\n"

            "Explicitly generate a catchy `title` for this episode.  \n"
            "Produce exactly valid JSON (no markdown or commentary) conforming to this schema:"
        )
    }

    user = {
        "role": "user",
        "content": f"""Here’s the topic to cover in today’s show:
**{topic}**

Return ONLY the JSON object—do not add any extra keys or text."""
    }

    # 3) Call the new Chat Completions endpoint
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            system,
            {"role": "system", "content": json.dumps(json_schema)},
            user
        ],
        temperature=0.7,
        max_tokens=1500
    )

    raw = resp.choices[0].message.content

    # 4) Strip fences and whitespace
    cleaned = re.sub(r"^```json\s*|\s
