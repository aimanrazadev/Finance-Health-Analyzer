import json
import os
from typing import Literal
from urllib import request

from dotenv import load_dotenv


load_dotenv()
Provider = Literal["gemini", "groq", "deterministic"]


class InsightsLLMService:
    """Gemini-first JSON generation with Groq and deterministic fallbacks."""

    def generate(self, prompt: str) -> tuple[str | None, Provider]:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            result = self._gemini(prompt, gemini_key)
            if result:
                return result, "gemini"

        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            result = self._groq(prompt, groq_key)
            if result:
                return result, "groq"

        return None, "deterministic"

    def _gemini(self, prompt: str, api_key: str) -> str | None:
        try:
            configured_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            model = configured_model.removeprefix("models/")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "maxOutputTokens": 1400,
                    "responseMimeType": "application/json",
                },
            }).encode("utf-8")
            req = request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None

    def _groq(self, prompt: str, api_key: str) -> str | None:
        try:
            body = json.dumps({
                "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                "messages": [
                    {"role": "system", "content": "Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1400,
                "response_format": {"type": "json_object"},
            }).encode("utf-8")
            req = request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=body,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"]
        except Exception:
            return None
