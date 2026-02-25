---
id: loo-1eu3
status: closed
deps: []
links: []
created: 2026-02-25T04:51:19Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-qkrm
tags: [code-review, reviewer:logic]
---
# respond_to_prompt does not validate content is non-empty

**File**: loom/routers/session0.py
**Line(s)**: 218-248
**Description**: respond_to_prompt strips the content (content.strip()) before saving but does not check whether the result is an empty string. A player can submit a response consisting entirely of whitespace and have it saved as an empty string in the database. session0_synthesis will then receive an empty string as one of its inputs. Unlike characters.py which returns 422 for empty name, and safety_tools.py which rejects empty description, this handler silently accepts blank content.
**Suggested Fix**: Add a check after stripping: if not content.strip(): raise HTTPException(status_code=422, detail='Response cannot be empty')

