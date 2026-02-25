---
id: loo-i6sp
status: closed
deps: []
links: [loo-5z56]
created: 2026-02-25T02:30:13Z
type: task
priority: 2
assignee: Michael Barrett
parent: loo-yacr
tags: [code-review, reviewer:readability]
---
# HTMX loaded from unpkg CDN with no integrity hash or version pin

**File**: loom/templates/base.html line 12. The base template loads HTMX via '<script src="https://unpkg.com/htmx.org@2" defer></script>'. The @2 tag floats with the latest 2.x release, meaning the dependency can change between deploys. There is no subresource integrity (SRI) hash. **Suggested Fix**: Pin to a specific patch version (e.g., htmx.org@2.0.4) and add an integrity attribute with a sha384 hash so the browser verifies the script has not been tampered with. Alternatively, vendor HTMX into loom/static/ to eliminate the external dependency entirely.


## Notes

**2026-02-25T02:32:16Z**

Duplicate of loo-5z56
