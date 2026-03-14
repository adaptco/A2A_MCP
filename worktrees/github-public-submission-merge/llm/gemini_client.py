import json
import os
import time
import urllib.request
from typing import Any, Dict, Optional

class GeminiError(RuntimeError):
    pass

class GeminiClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gemini-1.5-pro",
        timeout_s: int = 60,
        max_retries: int = 3,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise GeminiError("Missing GEMINI_API_KEY")
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries

    def generate_json(self, system: str, user: str, schema_hint: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns parsed JSON object. Uses a strict 'respond with JSON only' instruction.
        schema_hint is used as a soft constraint (and for logging).
        """
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        prompt = (
            f"{system}\n\n"
            "You MUST respond with valid JSON only (no markdown, no code fences, no commentary).\n"
            f"Target JSON schema (hint): {json.dumps(schema_hint, sort_keys=True)}\n\n"
            f"USER:\n{user}\n"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.9,
                "maxOutputTokens": 2048,
            },
        }

        last_err = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                    body = resp.read().decode("utf-8")

                data = json.loads(body)
                text = (
                    data["candidates"][0]["content"]["parts"][0].get("text", "").strip()
                )

                # Strip markdown fences if still present
                if text.startswith("```"):
                    lines = text.splitlines()
                    text = "\n".join(
                        line for line in lines
                        if not line.startswith("```")
                    ).strip()

                # Hard parse JSON only
                return json.loads(text)

            except Exception as e:
                last_err = e
                time.sleep(min(2 ** attempt, 8))

        raise GeminiError(f"Gemini generate failed after retries: {last_err}")
