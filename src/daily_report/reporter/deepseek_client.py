from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from openai import OpenAI


@dataclass(frozen=True)
class ChatMessage:
    role: Literal['system', 'user', 'assistant']
    content: str


class DeepSeekClient:
    """Tiny OpenAI-compatible client wrapper for DeepSeek chat models."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = 'deepseek-chat',
        base_url: str = 'https://api.deepseek.com',
        temperature: float = 0.2,
        timeout_seconds: int = 60,
    ) -> None:
        if not api_key:
            raise ValueError(
                'DeepSeek API key is empty. Set DEEPSEEK_API_KEY, '
                'or pass --api-key, or save it in local_settings.json.'
            )
        self.model_name = model_name
        self.temperature = temperature
        self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)

    def chat(self, messages: Iterable[ChatMessage]) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{'role': m.role, 'content': m.content} for m in messages],
            temperature=self.temperature,
        )
        content = response.choices[0].message.content
        return content or ''

    def test(self) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {'role': 'system', 'content': 'You are a connection test endpoint.'},
                {'role': 'user', 'content': 'Reply with OK.'},
            ],
            temperature=0,
            max_tokens=8,
        )
        content = response.choices[0].message.content or 'OK'
        return f'模型连接正常：{self.model_name}，返回：{content.strip()}'
