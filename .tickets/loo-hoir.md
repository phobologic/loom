---
id: loo-hoir
status: open
deps: [loo-oqhu]
links: []
created: 2026-02-27T05:02:20Z
type: bug
priority: 2
assignee: Michael Barrett
---
# Fix weak and missing assertions in tests

Several assertions are too weak to catch real regressions:

1. test_oracles.py:448 — oracle tiebreak: comment says 'Should have selected interpretation #2' but assertion is only 'assert event.oracle_selected_interpretation is not None'. Fix: assert == 2.

2. test_notifications.py:208 — truthiness check 'assert bob_notifs' gives no failure context and doesn't verify count. Fix: assert len(bob_notifs) == 1.

3. test_notifications.py:299-305 — unread count uses '>= 1' instead of '== 1'. With StaticPool leakage this could false-pass. Fix: use == 1.

4. test_character_suggestions.py:540 — test_scene_complete_ai_failure_does_not_abort verifies the scene completes but doesn't assert that no partial CharacterUpdateSuggestion rows were created before the error. Add a select + assert suggestions == [].

5. test_notifications.py:329 — 'assert "new]" in r.text or "unread" in r.text' uses two different fallback strings; if the template changes, one branch silently absorbs the failure. Fix: assert one canonical string.


## Notes

**2026-02-27T05:03:19Z**

IMPLEMENTATION DETAILS:

--- Fix 1: Oracle tiebreak assertion (test_oracles.py) ---
Search for 'test_tiebreak_selects_from_votes' in tests/test_oracles.py, around line 421-448.
The test sets up a 2-vs-2 tie between interpretation 0 and interpretation 2, where interpretation 2 has an older vote (should win by timestamp tiebreak).

Current assertion (line ~448):
  assert event.oracle_selected_interpretation is not None
  # Should have selected interpretation #2 (index 2)

Fixed assertion:
  assert event.oracle_selected_interpretation == 2, (
      f'Tiebreak should select interpretation 2 (oldest vote wins), got {event.oracle_selected_interpretation}'
  )

--- Fix 2: Truthiness check (test_notifications.py) ---
Find line ~208, inside test_mark_notification_read or similar.

Current:
  bob_notifs = await _get_notifications(db, user_id=2, game_id=game_id)
  assert bob_notifs
  notif_id = bob_notifs[0].id

Fixed:
  bob_notifs = await _get_notifications(db, user_id=2, game_id=game_id)
  assert len(bob_notifs) == 1, f'Expected 1 notification for Bob, got {len(bob_notifs)}: {bob_notifs}'
  notif_id = bob_notifs[0].id

--- Fix 3: Overly broad >= 1 count (test_notifications.py) ---
Find around lines 299-305 in test_notifications.py (likely in TestUnreadCount or similar).

Current:
  data = r.json()
  assert data['count'] >= 1
  ...
  assert r2.json()['count'] >= 1

Fixed:
  assert data['count'] == 1, f'Expected count=1, got {data["count"]}'
  ...
  assert r2.json()['count'] == 1

--- Fix 4: Missing assertion after AI failure (test_character_suggestions.py) ---
Find 'test_scene_complete_ai_failure_does_not_abort', around line 540.
After the scene completion assertion, add:

  from loom.models import CharacterUpdateSuggestion
  suggestions = list(await db.scalars(
      select(CharacterUpdateSuggestion).where(
          CharacterUpdateSuggestion.character_id == char_id
      )
  ))
  assert suggestions == [], f'Expected no suggestion rows after AI failure, got {len(suggestions)}'

(char_id should already be in scope from the test setup)

--- Fix 5: Dual-string assertion (test_notifications.py) ---
Find around line 329, likely in a test that checks the games list page for an unread indicator.

Current:
  assert 'new]' in r.text or 'unread' in r.text

Look at the actual template (loom/templates/) to find the canonical string that appears when there are unread notifications. Then assert that single string. This removes the 'or' branch that can silently mask a regression.

VERIFICATION: Run 'uv run pytest -v tests/test_oracles.py tests/test_notifications.py tests/test_character_suggestions.py' after each fix.
