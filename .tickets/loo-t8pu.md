---
id: loo-t8pu
status: closed
deps: [loo-hgie]
links: []
created: 2026-02-26T05:20:36Z
type: task
priority: 1
assignee: Michael Barrett
parent: loo-leil
---
# Step 38: Fortune Roll Oracle Follow-up

On Exceptional Yes or Exceptional No Fortune Roll, prompt: 'That's an exceptional result - want the oracle to suggest what that means?' If accepted, invokes full interpretive oracle with Fortune Roll question as context, exceptional result as constraint, and word seed pair for inspiration. Player can decline. Regular Yes/No don't trigger. Requirements: REQ-ORACLE-008.


## Notes

**2026-02-27T04:44:48Z**

Simplified from original spec: instead of an automatic prompt + constrained AI oracle invocation on exceptional results only, implemented a convenience 'Ask the oracle about this →' link shown to the invoker after any resolved fortune roll. Link pre-fills the oracle question textarea. No new routes, no DB migration, no AI changes. Discussed with user — they agreed the original spec was over-engineered since players can always invoke the oracle manually anyway.
