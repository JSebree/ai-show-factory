import openai, os, json

openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT = """
You are a podcast‑script generator.
Return your answer **as valid JSON** with keys:
title, description, full_script. Do NOT add extra keys.
"""

def make_script(topic: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user",
             "content": f"Topic: {topic}\n\nRemember: respond in JSON only."}
        ]
    )
    return json.loads(response.choices[0].message.content)

