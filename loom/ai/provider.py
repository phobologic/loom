"""Anthropic AI provider — the single implementation behind the AI abstraction."""

from __future__ import annotations

from typing import TypeVar

import anthropic
import instructor
from pydantic import BaseModel

from loom.config import settings

T = TypeVar("T", bound=BaseModel)


class AnthropicProvider:
    """Async wrapper around the Anthropic Messages API via instructor.

    A single instance is shared across the process. The underlying client is
    created lazily so tests that never call AI functions don't require a key.
    """

    def __init__(self) -> None:
        self._client: instructor.AsyncInstructor | None = None

    def _get_client(self) -> instructor.AsyncInstructor:
        if self._client is None:
            self._client = instructor.from_anthropic(
                anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
            )
        return self._client

    async def generate_structured(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int = 1024,
        response_model: type[T],
    ) -> T:
        """Send a prompt to the Anthropic API and return a validated Pydantic model.

        Args:
            system: System prompt (behavioral instructions only).
            prompt: User message content.
            model: Model ID (e.g., "claude-haiku-4-5-20251001").
            max_tokens: Maximum tokens to generate.
            response_model: Pydantic model class defining the expected output shape.

        Returns:
            A validated instance of response_model.
        """
        return await self._get_client().messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            response_model=response_model,
        )


_provider = AnthropicProvider()


def get_provider() -> AnthropicProvider:
    """Return the singleton AI provider."""
    return _provider
