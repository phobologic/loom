"""Anthropic AI provider — the single implementation behind the AI abstraction."""

from __future__ import annotations

import anthropic

from loom.config import settings


class AnthropicProvider:
    """Async wrapper around the Anthropic Messages API.

    A single instance is shared across the process. The underlying client is
    created lazily so tests that never call AI functions don't require a key.
    """

    def __init__(self) -> None:
        self._client: anthropic.AsyncAnthropic | None = None

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        model: str,
        max_tokens: int = 1024,
    ) -> str:
        """Send a prompt to the Anthropic API and return the text response.

        Args:
            system: System prompt.
            prompt: User message content.
            model: Model ID (e.g., "claude-haiku-4-5-20251001").
            max_tokens: Maximum tokens to generate.

        Returns:
            The model's text response.
        """
        client = self._get_client()
        message = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        block = message.content[0]
        return block.text  # type: ignore[union-attr]


_provider = AnthropicProvider()


def get_provider() -> AnthropicProvider:
    """Return the singleton AI provider."""
    return _provider
