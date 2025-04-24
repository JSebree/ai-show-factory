# llm_writer.py
import os
import re
import json
import openai

# make sure you have openai>=1.0.0 installed
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

    # 2) Full system prompt with all requirements
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
            "- Make transitions smooth and natural.  \n"
            "- Include approximate timestamps (mm:ss) for each Pillar segment, "
            "allocating roughly:  \n"
            "    * Breakthroughs: 05:00  \n"
            "    * Governance/Ethics: 05:00  \n"
            "    * Inner Life & Society: 05:00  \n"
            "    * Speculative Futures: 05:00  \n"
            "    * Intros, transitions & wrap: 05–07 minutes total.  \n\n"

            "Produce exactly valid JSON (no markdown or commentary) matching this schema:"
        )
    }

    # 3) Build user prompt
    user = {
        "role": "user",
        "content": (
            f"Topic: **{topic}**\n\n"
            "Return only a JSON object with these top-level keys:\n"
            "  • title (string)\n"
            "  • description (string)\n"
            "  • pubDate (RFC-2822)\n"
            "  • dialogue (array of {speaker: str, time: \"mm:ss\", text: str})\n\n"
            "Ensure you follow the schema exactly."
        )
    }

    # 4) Call the new 1.x API endpoint
    resp = openai.chat.completions.create(
        model="gpt-4o",
        messages=[system, {"role":"system","content": json.dumps(json_schema)}, user],
        temperature=0.7,
        max_tokens=2000
    )

    raw = resp.choices[0].message.content

    # 5) Strip fences & whitespace
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    # 6) Parse JSON
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}") from e

    # 7) Sanity‐check all required keys
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    return data
