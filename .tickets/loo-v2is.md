---
id: loo-v2is
status: closed
deps: []
links: [loo-5z56]
created: 2026-02-25T02:29:58Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:logic]
---
# htmx loaded from unpkg CDN without subresource integrity — supply-chain risk

**File**: loom/templates/base.html | **Line(s)**: 12 | **Description**: The htmx script tag loads from https://unpkg.com/htmx.org@2 with no integrity attribute. A compromised CDN or a typosquat could inject arbitrary JavaScript into every page. The @2 tag also does not pin a specific version, so a breaking change or a malicious patch to htmx v2.x would silently affect all users. | **Suggested Fix**: Pin to an exact version (e.g. htmx.org@2.0.4) and add an integrity= attribute with the SHA-384 hash of the known-good file. Alternatively vendor the file into loom/static/.


## Notes

**2026-02-25T02:32:14Z**

Duplicate of loo-5z56
