# Smoke Test

Run a full end-to-end smoke test of the loom app against a live dev server. Tests each workflow in `tests/e2e/smoke-manifest.md` using the playwright-cli skill, logs failures as tickets under a dated epic, and reports a summary.

## Step 1: Preflight

Check if the server is already running:

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/ 2>/dev/null
```

- If the response is `200`, the server is already running — note this so we do NOT kill it at the end.
- If not running, start it in the background:
  ```bash
  uv run uvicorn loom.main:app --port 8000 > /tmp/loom-smoketest.log 2>&1 &
  sleep 3
  ```
  Note that WE started it, so we kill it at the end.

Then read `tests/e2e/smoke-manifest.md` to get the full ordered list of workflows to test.

## Step 2: Create the smoke test epic

```bash
tk create "Smoke test $(date +%Y-%m-%d)" -t epic -p 1 -d "Automated smoke test run covering all workflows in tests/e2e/smoke-manifest.md."
```

Save the returned epic ID (e.g. `loo-xxxx`) — all failure tickets attach to it.

## Step 3: Run each workflow

Use the playwright-cli skill to execute each workflow from the manifest in order.

**For each workflow:**
1. Attempt the workflow following the manifest's instructions (preconditions, actions, pass criteria)
2. Take a screenshot to `tests/e2e/screenshots/<workflow-slug>-<pass|fail>.png`
3. Mark it: ✅ pass, ❌ fail, or ⚠️ partial
4. On **any failure or partial**:
   ```bash
   tk create "<Workflow name>: <short description of what broke>" -t bug -p <0|1|2> -d "<Steps to reproduce, what was expected, what happened. Reference screenshot path.>"
   ```
   Then link to the epic:
   ```bash
   tk dep <new-ticket-id> <epic-id>
   ```

**Severity guide:**
- P0 — flow cannot be completed at all (blocks all subsequent tests that depend on it)
- P1 — feature is broken but a workaround exists, or the failure is isolated
- P2 — cosmetic, display, or minor UX issue

**Key playwright-cli notes:**
- Use named sessions: `playwright-cli -s=alice` and `playwright-cli -s=bob` for separate browser contexts
- Use `run-code` for form submissions (more reliable than ref-based clicks):
  ```bash
  playwright-cli -s=alice run-code "async page => { await page.fill('[name=foo]', 'bar'); await page.click('button[type=submit]'); await page.waitForTimeout(1000); return page.url(); }"
  ```
- Screenshots go to `tests/e2e/screenshots/` (gitignored)
- Dev login: `http://localhost:8000/dev/login` — click Alice or Bob button
- Each workflow should create its own fresh game for isolation

## Step 4: Teardown

```bash
playwright-cli close-all
```

If WE started the server in Step 1:
```bash
kill $(lsof -ti:8000) 2>/dev/null
```

## Step 5: Report

Print a summary table:

```
| # | Workflow                        | Result | Ticket     |
|---|--------------------------------|--------|------------|
| 1 | Auth — dev login               | ✅     |            |
| 2 | Auth — unauthenticated redirect | ✅     |            |
| 3 | Game creation                  | ❌     | loo-xxxx   |
...
```

Close the epic if all workflows passed; leave it open if there are failures so they show up in `tk ready`.
