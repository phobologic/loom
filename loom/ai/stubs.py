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


def generate_world_document(session0_data: dict) -> str:
    """Stub: returns a minimal structured world document."""
    return "# World Document\n\nThis world is shaped by the choices made at its founding..."
