import os
import json
from typing import Optional
from urllib import request

from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self):
        self.provider = os.getenv("AI_PROVIDER", "fallback").lower()
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("AI_MODEL", "gpt-4o-mini")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key) and self.provider in {"openai", "groq", "gemini"}

    def generate_text(self, prompt: str) -> Optional[str]:
        if not self.is_configured:
            return None

        if self.provider == "gemini":
            return self._generate_gemini_text(prompt)

        try:
            from openai import OpenAI

            base_url = None
            if self.provider == "groq":
                base_url = "https://api.groq.com/openai/v1"

            client = OpenAI(api_key=self.api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a practical personal finance advisor. Give concise, safe spending and savings insights.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=450,
            )
            return response.choices[0].message.content
        except Exception:
            return None

    def _generate_gemini_text(self, prompt: str) -> Optional[str]:
        try:
            model = self.model if self.model.startswith("gemini") else "gemini-1.5-flash"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            payload = json.dumps({
                "contents": [
                    {
                        "parts": [
                            {"text": prompt}
                        ]
                    }
                ]
            }).encode("utf-8")
            req = request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
            return body["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return None
