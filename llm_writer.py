import openai, os, json

openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT = """You are a podcast script writer..."""

def make_script(topic: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": PROMPT},
            {"role": "user", "content": f"Topic: {topic}"}
        ]
    )
    return json.loads(response.choices[0].message.content)
