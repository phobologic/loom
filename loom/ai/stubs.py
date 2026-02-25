# AI stub contract: all functions here return realistic hardcoded responses.
# Steps 1–22 use these stubs exclusively.
# Replace with real Anthropic API calls in Step 23.


def classify_beat_significance(beat_text: str) -> str:
    """Stub: always returns 'minor'. Real implementation uses Anthropic API."""
    return "minor"


def oracle_interpretations(question: str, word_pair: tuple[str, str]) -> list[str]:
    """Stub: returns 3 hardcoded plausible interpretations."""
    return [
        "The threads of fate suggest an unexpected alliance forms in shadow.",
        "Ancient obligations resurface, demanding a choice between duty and desire.",
        "What was lost cannot be reclaimed unchanged — but transformation awaits.",
    ]


def session0_synthesis(inputs: list[str]) -> str:
    """Stub: returns genre-appropriate placeholder prose."""
    return (
        "A world of flickering gaslight and forgotten gods, where the streets whisper "
        "secrets and every alliance carries a hidden price. The players have gathered "
        "at the crossroads of ambition and survival."
    )


def format_safety_tools_context(tools: list) -> str:
    """Format lines and veils as a context block for AI prompts.

    Args:
        tools: List of GameSafetyTool instances (objects with .kind.value and .description).

    Returns:
        A formatted string for inclusion in an AI system prompt.
        Returns an empty string if no tools are defined.
    """
    lines = [t for t in tools if t.kind.value == "line"]
    veils = [t for t in tools if t.kind.value == "veil"]

    if not lines and not veils:
        return ""

    parts = ["SAFETY TOOLS — content boundaries established by the players:"]
    if lines:
        parts.append("Lines (must NOT appear in any content or suggestions):")
        for t in lines:
            parts.append(f"  - {t.description}")
    if veils:
        parts.append("Veils (may be referenced but not depicted in detail — fade to black):")
        for t in veils:
            parts.append(f"  - {t.description}")

    return "\n".join(parts)


def generate_world_document(session0_data: dict) -> str:
    """Stub: returns a minimal structured world document."""
    return "# World Document\n\nThis world is shaped by the choices made at its founding..."
