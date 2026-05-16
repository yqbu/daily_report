from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from openai import OpenAI


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class DeepSeekClientError(RuntimeError):
    pass


class DeepSeekClient:
    """DeepSeek OpenAI-compatible Chat Completions client."""

    def __init__(
            self,
            *,
            api_key: str | None,
            model_name: str = "deepseek-chat",
            base_url: str = "https://api.deepseek.com",
            temperature: float = 0.2,
            timeout: float = 60.0,
    ) -> None:
        key = (api_key or "").strip() or os.getenv("DEEPSEEK_API_KEY", "").strip()
        if not key:
            raise DeepSeekClientError("缺少 DeepSeek API Key。请在设置页填写，或设置 DEEPSEEK_API_KEY 环境变量。")

        self.model_name = model_name.strip() or "deepseek-chat"
        self.temperature = float(temperature)
        self.client = OpenAI(
            api_key=key,
            base_url=(base_url or "https://api.deepseek.com").rstrip("/"),
            timeout=timeout,
        )

    def chat(self, messages: Iterable[ChatMessage]) -> str:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=payload,
                temperature=self.temperature,
                stream=False,
            )
            content = response.choices[0].message.content
        except Exception as exc:  # openai SDK exception hierarchy changes across versions; keep GUI error readable.
            raise DeepSeekClientError(f"DeepSeek API 调用失败：{exc}") from exc

        if not content:
            raise DeepSeekClientError("DeepSeek API 返回为空。")
        return content

    def test(self) -> str:
        return self.chat(
            [
                ChatMessage(role="system", content="你是一个用于测试 API 连通性的助手。"),
                ChatMessage(role="user", content="请回复：Daily Report API 测试成功。并用一句话说明当前模型可用。"),
            ]
        )
