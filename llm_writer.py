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

    # 2) System prompt with full requirements
    system = {
        "role": "system",
        "content": (
            "You are a professional podcast scriptwriter for a two-host show.\n"
            "Your job is to craft a 20–25 minute conversational episode about the latest AI news, "
            "with social and philosophical implications, drawing only from reputable sources "
            "published in the last 30 days.\n\n"

            "Positioning: Bridge bleeding-edge advances (AI, quantum, neurotech) with ethics & social impact.\n"
            "Four Pillars:\n"
            "  1. Breakthroughs — concise explainers of top news items.\n"
            "  2. Governance & Ethics — policy stakes and moral dimensions.\n"
            "  3. Inner Life & Society — psychological/community impact.\n"
            "  4. Speculative Futures — economy, philosophy, and what’s next.\n\n"
            "Format:\n"
            "- Two hosts (Host A & Host B), friendly and engaging, with real chemistry.\n"
            "- Dialogue style: back-and-forth, with brief banter but clear emphasis on facts.\n"
            "- Make transitions from section to section smooth and natural.\n"
            "- Include approximate timestamps (mm:ss) for each Pillar segment, allocating roughly:\n"
            "    * Breakthroughs: 05:00\n"
            "    * Governance/Ethics: 05:00\n"
            "    * Inner Life & Society: 05:00\n"
            "    * Speculative Futures: 05:00\n"
            "    * Intros, transitions & wrap: 05:00–07:00.\n\n"
            "Produce exactly valid JSON with these top-level keys:\n"
            "  • title\n"
            "  • description\n"
            "  • pubDate (RFC-2822)\n"
            "  • dialogue (array of objects: {speaker: str, time: \"mm:ss\", text: str})\n"
        )
    }

    # 3) User message with the topic
    user = {
        "role": "user",
        "content": f"Topic: {topic}"  
    }

    # 4) Assemble messages
    messages = [
        system,
        {"role": "system", "content": json.dumps(json_schema)},
        user
    ]

    # 5) Call the OpenAI chat API (new style)
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=1500
    )

    raw = resp.choices[0].message.content

    # 6) Clean up any fences
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON from LLM:\n{raw}") from e

    # 7) Final sanity check
    for key in ("title", "description", "pubDate", "dialogue"):
        if key not in data:
            raise RuntimeError(f"LLM returned missing field: {key}")

    return data
