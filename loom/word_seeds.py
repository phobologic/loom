"""Word seed table management: built-in data, lazy seeding, and random pair generation."""

from __future__ import annotations

import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loom.models import WordSeedEntry, WordSeedTable, WordSeedWordType

# ---------------------------------------------------------------------------
# Built-in word seed data
# ---------------------------------------------------------------------------

DEFAULT_WORD_SEEDS: dict[str, dict[str, list[str]]] = {
    "general": {
        "action": [
            "abandon",
            "betray",
            "claim",
            "deceive",
            "destroy",
            "empower",
            "expose",
            "flee",
            "forge",
            "hide",
            "protect",
            "reclaim",
            "reveal",
            "sacrifice",
            "surrender",
            "transform",
            "unite",
            "unravel",
        ],
        "descriptor": [
            "ancient",
            "authority",
            "desire",
            "dreams",
            "forgotten",
            "identity",
            "justice",
            "legacy",
            "light",
            "loyalty",
            "memory",
            "power",
            "shadow",
            "silence",
            "truth",
            "trust",
            "weakness",
        ],
    },
    "fantasy": {
        "action": [
            "banish",
            "commune",
            "conjure",
            "curse",
            "enchant",
            "invoke",
            "quest",
            "shatter",
            "summon",
            "traverse",
        ],
        "descriptor": [
            "arcane",
            "ancient",
            "blessed",
            "cursed",
            "fey",
            "mystical",
            "omen",
            "prophecy",
            "ritual",
            "sacred",
        ],
    },
    "sci-fi": {
        "action": [
            "calculate",
            "escape",
            "hack",
            "override",
            "replicate",
            "scan",
            "transmit",
            "upload",
        ],
        "descriptor": [
            "alien",
            "digital",
            "encrypted",
            "neural",
            "protocol",
            "quantum",
            "synthetic",
            "void",
        ],
    },
    "horror": {
        "action": [
            "consume",
            "corrupt",
            "escape",
            "haunt",
            "hunt",
            "unbury",
            "witness",
        ],
        "descriptor": [
            "abyssal",
            "creeping",
            "profane",
            "rotten",
            "twisted",
            "visceral",
            "wretched",
        ],
    },
    "noir": {
        "action": [
            "blackmail",
            "double-cross",
            "investigate",
            "obsess",
            "pursue",
            "seduce",
            "silence",
        ],
        "descriptor": [
            "corrupt",
            "desperate",
            "gritty",
            "obsessed",
            "shadowed",
            "smoky",
            "tarnished",
        ],
    },
}

# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


async def ensure_game_seeds(game_id: int, db: AsyncSession) -> None:
    """Seed default word tables for a game if none exist yet.

    Called lazily on first oracle invocation. Safe to call repeatedly — exits
    immediately if tables are already present.
    """
    result = await db.execute(
        select(WordSeedTable).where(WordSeedTable.game_id == game_id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return

    for category, words in DEFAULT_WORD_SEEDS.items():
        table = WordSeedTable(
            game_id=game_id,
            category=category,
            is_active=True,
            is_builtin=True,
        )
        db.add(table)
        await db.flush()

        for word in words.get("action", []):
            db.add(WordSeedEntry(table_id=table.id, word=word, word_type=WordSeedWordType.action))
        for word in words.get("descriptor", []):
            db.add(
                WordSeedEntry(table_id=table.id, word=word, word_type=WordSeedWordType.descriptor)
            )

    await db.flush()


# ---------------------------------------------------------------------------
# Random pair generation
# ---------------------------------------------------------------------------


async def random_word_pair(game_id: int, db: AsyncSession) -> tuple[str, str]:
    """Return a random (action, descriptor) pair from the game's active tables.

    Args:
        game_id: The game to draw from.
        db: Async DB session.

    Returns:
        A tuple of (action_word, descriptor_word).

    Raises:
        ValueError: If no active tables or insufficient words exist.
    """
    result = await db.execute(
        select(WordSeedTable)
        .where(WordSeedTable.game_id == game_id, WordSeedTable.is_active == True)  # noqa: E712
        .options(selectinload(WordSeedTable.entries))
    )
    tables = result.scalars().all()

    actions: list[str] = []
    descriptors: list[str] = []
    for table in tables:
        for entry in table.entries:
            if entry.word_type == WordSeedWordType.action:
                actions.append(entry.word)
            else:
                descriptors.append(entry.word)

    if not actions or not descriptors:
        raise ValueError("No active word seed entries found for this game")

    return random.choice(actions), random.choice(descriptors)
