from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from meridian_expert.llm.profiles import load_profiles


class OpenAIClient:
    def __init__(self) -> None:
        self.client = OpenAI()
        self.profiles = load_profiles()

    def call(self, alias: str, prompt: str, stream: bool = False, response_format: dict[str, Any] | None = None) -> str:
        profile = self.profiles[alias]
        model = profile["model"]
        effort = profile.get("reasoning_effort", "medium")
        attempts = 3
        for i in range(attempts):
            try:
                resp = self.client.responses.create(model=model, reasoning={"effort": effort}, input=prompt, stream=stream)
                if stream:
                    chunks = []
                    for event in resp:
                        text = getattr(event, "delta", None)
                        if text:
                            chunks.append(text)
                    return "".join(chunks)
                return getattr(resp, "output_text", "")
            except Exception:
                if i == attempts - 1:
                    raise
                time.sleep(2 ** i)
        return ""
