---
id: loo-98u5
status: open
deps: [loo-hdz8]
links: []
created: 2026-02-26T04:40:18Z
type: bug
priority: 3
assignee: Michael Barrett
---
# playwright-cli ref-based clicks unreliable for form submission

Parent: loo-hdz8. During smoke testing with playwright-cli, clicking form submit buttons via snapshot refs (e.g. 'playwright-cli click e30') did not reliably submit forms — the page would remain with form values intact but no POST submitted. Workaround: use 'playwright-cli run-code' with page.click('button[type=submit]'). Affects: character creation form, scene proposal form. Standard playwright-cli ref clicks work fine for navigation links and vote buttons. This may be a playwright-cli issue with buttons inside HTMX-enhanced forms, not an app bug — worth investigating whether the forms have any JS preventing default submission.

