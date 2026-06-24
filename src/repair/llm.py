from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class OpenRouterClient:
    model: str
    timeout_s: int = 60
    max_retries: int = 2
    temperature: float = 0.1
    base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    api_key_env: str = "OPENROUTER_API_KEY"

    def _headers(self) -> dict[str, str]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"{self.api_key_env} is not set.")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def complete_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        error = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    self.base_url,
                    headers=self._headers(),
                    json=payload,
                    timeout=self.timeout_s,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as exc:
                error = exc
                if attempt == self.max_retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError("OpenRouter request failed.") from error

