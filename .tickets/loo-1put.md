---
id: loo-1put
status: closed
deps: []
links: []
created: 2026-02-25T04:50:24Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:security]
---
# prompt_id not validated to belong to game_id in session0 routes

**File**: loom/routers/session0.py
**Line(s)**: 175, 229, 263, 298, 323, 348, 370, 394
**Description**: Every session0 route loads the game by game_id and checks membership, but then resolves the prompt by searching game.session0_prompts for a matching prompt.id. This is safe as long as the eager-load is used consistently. However, the pattern relies on the ORM relationship being correctly populated. If a prompt_id from a different game were somehow present in the in-memory list (e.g., due to an identity-map collision or a future refactor that passes the wrong game object), there would be no SQL-level constraint tying the prompt to the game in the query itself. Additionally, the move_prompt route resolves the prompt from game.session0_prompts and swaps order values on two prompts from potentially different games if the list is ever stale.
**Suggested Fix**: Add an explicit game_id filter when fetching the prompt from the database rather than relying solely on the ORM relationship collection:
```python
prompt_result = await db.execute(
    select(Session0Prompt).where(
        Session0Prompt.id == prompt_id,
        Session0Prompt.game_id == game_id,
    )
)
prompt = prompt_result.scalar_one_or_none()
```
This makes the authorization boundary explicit at the database layer.

