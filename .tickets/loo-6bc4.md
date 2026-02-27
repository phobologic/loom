---
id: loo-6bc4
status: open
deps: []
links: []
created: 2026-02-27T15:57:23Z
type: task
priority: 4
assignee: Michael Barrett
parent: loo-1pwe
---
# Audit and validate AI model selection for each interaction

Review every AI call in loom/ai/client.py and related providers to verify we're using the appropriate model for each interaction type. Consider cost vs. capability trade-offs — e.g. simpler/structured tasks (consistency checks, tension adjustment) may be fine on a cheaper/faster model, while richer generative tasks (prose expansion, oracle interpretations) may warrant a more capable one. Document the rationale for each choice.

