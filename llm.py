import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(".env la GEMINI_API_KEY illa")
        _client = genai.Client(api_key=key)
    return _client


def ask(system_prompt: str, user_message: str) -> str:
    resp = _get_client().models.generate_content(
        model=MODEL,
        contents=user_message,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )
    return (resp.text or "").strip()
