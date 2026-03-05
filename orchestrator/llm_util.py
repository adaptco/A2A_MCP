import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from schemas.prompt_inputs import PromptIntent

load_dotenv()


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("LLM_API_KEY")
        self.endpoint = os.getenv("LLM_ENDPOINT")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        fallback = os.getenv("LLM_FALLBACK_MODELS", "")
        self.fallback_models = [m.strip() for m in fallback.split(",") if m.strip()]
        self.timeout_s = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    @staticmethod
    def _is_unsupported_model_error(response) -> bool:
        if getattr(response, "status_code", None) != 400:
            return False
        try:
            payload = response.json()
            message = str(payload.get("error", {}).get("message", "")).lower()
        except Exception:
            message = str(getattr(response, "text", "")).lower()
        return "model is not supported" in message or "requested model is not supported" in message

    def _candidate_models(self):
        models = [self.model] + self.fallback_models
        return list(dict.fromkeys([m for m in models if m]))

    def call_llm(
        self,
        prompt: str | None = None,
        system_prompt: str = "You are a helpful coding assistant.",
        prompt_intent: "PromptIntent" | None = None,
    ):
        if prompt_intent:
            # Simple conversion from intent to prompt string
            prompt = f"{prompt_intent.task_context}\n\n{prompt_intent.user_input}"
            if prompt_intent.workflow_constraints:
                prompt += f"\n\nConstraints:\n- " + "\n- ".join(prompt_intent.workflow_constraints)
        if not self.api_key or not self.endpoint:
            raise ValueError("API Key or Endpoint missing from your local .env file!")

        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        errors = []

        for model in self._candidate_models():
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            }

            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout_s,
            )

            if response.ok:
                body = response.json()
                return body["choices"][0]["message"]["content"]

            if self._is_unsupported_model_error(response):
                errors.append(f"{model}: unsupported")
                continue

            try:
                response.raise_for_status()
            except Exception as exc:
                errors.append(f"{model}: {exc}")
                raise RuntimeError(
                    f"LLM request failed using model '{model}': {exc}"
                ) from exc

        tried = ", ".join(self._candidate_models())
        detail = "; ".join(errors) if errors else "no additional error details"
        raise RuntimeError(
            f"No supported model found for endpoint '{self.endpoint}'. "
            f"Tried: {tried}. Details: {detail}"
        )

    async def acall_llm(self, *args: Any, **kwargs: Any) -> str:
        """Async wrapper around call_llm to prevent blocking the event loop."""
        return await asyncio.to_thread(self.call_llm, *args, **kwargs)
