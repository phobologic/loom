---
id: loo-njv1
status: open
deps: []
links: []
created: 2026-02-25T02:29:41Z
type: task
priority: 3
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# Session user_id not validated as integer type before DB lookup

**File**: loom/dependencies.py | **Line(s)**: 19-20 | **Description**: request.session.get('user_id') returns whatever was stored in the signed cookie — typically an int from the dev login flow, but the code does not enforce the type before passing it to db.get(User, user_id). If session data is tampered with (e.g., via a forged cookie using the known default secret key) and contains a non-integer value, the db.get call may raise a database-level error rather than returning a clean 401/302. Combined with the weak default secret, this compounds the risk. | **Suggested Fix**: Validate and cast the session value: user_id = request.session.get('user_id'); if not isinstance(user_id, int): raise HTTPException(302, ...). This is especially important once the secret key issue (loo-5fkq) is resolved.

