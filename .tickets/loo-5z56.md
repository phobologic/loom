---
id: loo-5z56
status: closed
deps: []
links: [loo-v2is, loo-i6sp]
created: 2026-02-25T02:29:19Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:security]
---
# HTMX loaded from unpkg CDN without subresource integrity check

**File**: loom/templates/base.html | **Line(s)**: 12 | **Description**: The script tag loads HTMX from https://unpkg.com/htmx.org@2 with no integrity attribute. If unpkg or the htmx package is compromised, an attacker can serve arbitrary JavaScript to all users. The @2 version pin is also loose and will automatically pull new minor/patch versions. | **Suggested Fix**: Pin to an exact version and add a Subresource Integrity (SRI) hash: <script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-<hash>" crossorigin="anonymous" defer></script>. Better still, vendor the asset into loom/static/ to eliminate the CDN dependency entirely.


## Notes

**2026-02-25T02:39:25Z**

Closing: intentionally deferred. SRI hashes and exact version pinning are production hardening concerns. The development plan explicitly selects HTMX as the UI strategy; locking the CDN version is appropriate pre-deploy, not during active UI development.
