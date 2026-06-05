# Browser Testing — Playwright

End-to-end browser tests live in `app/frontend/tests-e2e/`. They run against the React + Vite dashboard at `http://localhost:5173`, which proxies `/api/*` to FastAPI at `http://localhost:8000`.

Two ways to drive the browser:

1. **CLI / CI**: `npm run test:e2e` — checked-in regression suite.
2. **Claude Code agent**: the `playwright` MCP server (configured in `.mcp.json`) lets Claude open pages, click, screenshot, read the console, and inspect network requests during a session.

---

## Prerequisites (one-time)

```bash
# Backend stack
docker compose up -d                       # API + db + redis + worker

# Frontend deps (already installed if you've run vite)
cd app/frontend && npm install
npx playwright install chromium            # ~260 MB cached in ~/Library/Caches/ms-playwright
```

---

## Running tests locally

```bash
cd app/frontend
npm run test:e2e                            # headless run, html report at playwright-report/
npm run test:e2e:ui                         # interactive UI mode — best for authoring
npm run test:e2e:report                     # open the last HTML report
```

`playwright.config.ts` automatically starts `vite dev` if nothing is listening on `:5173`. To run against an already-running dev server (faster, what Claude does), set:

```bash
E2E_NO_WEBSERVER=1 npm run test:e2e
```

To point at a different origin (e.g., a staging URL):

```bash
E2E_BASE_URL=https://nerdy-three.vercel.app npm run test:e2e
```

---

## Authentication

Production auth flows through Clerk JWT. For Playwright we bypass it by setting `DEV_MODE=true` in `.env` — `app/api/deps.py` then accepts the `X-User-Id` header instead of validating a JWT.

**Today** `DEV_MODE=false`. The seed `dashboard-smoke.spec.ts` only checks the unauthenticated React shell, so it works without the flip. Deeper tests (variant cards, Evidence panel, session detail) need:

```bash
# .env
DEV_MODE=true
```

Then restart the API: `docker compose restart api worker`.

Specs that hit authenticated routes should set the header explicitly:

```ts
await page.setExtraHTTPHeaders({ 'X-User-Id': '<seeded-user-id>' })
```

A `tests-e2e/fixtures/authed.ts` helper will land alongside PI-07's first authenticated spec.

---

## Claude Code as a browser agent (MCP)

`.mcp.json` declares a `playwright` server. `.claude/settings.local.json` pre-approves it via `enabledMcpjsonServers`, so a fresh Claude Code session loads it automatically.

After restarting Claude Code, the assistant gains tools like:

- `browser_navigate({ url })`
- `browser_snapshot()` — accessibility-tree snapshot of the current page
- `browser_click({ ref })` / `browser_type({ ref, text })`
- `browser_console_messages()` / `browser_network_requests()`
- `browser_take_screenshot()`

Typical agent loop during PI-08 verification:

1. Boot dev server (`docker compose up -d` + `cd app/frontend && npm run dev`).
2. Ask Claude: "open the dashboard, open the most recent session, open the variants panel, screenshot the Evidence card, and confirm 8 dimensions render with rationales."
3. Claude drives the browser via MCP, reports findings, and can drop the screenshot into `tests-e2e/fixtures/` as a visual baseline.

This is the loop that replaces the manual portion of `PI-MANUAL-TEST-RUNBOOK.md` (Step 7 of PI-11).

---

## Where to put new specs

| Test target | File |
|---|---|
| Unauthenticated shell + nav | `tests-e2e/dashboard-smoke.spec.ts` |
| Variant Evidence panel (PI-08) | `tests-e2e/variants-evidence.spec.ts` |
| Future per-feature suites | `tests-e2e/<feature>.spec.ts` |

Keep specs feature-scoped, not ticket-scoped — `variants-evidence.spec.ts` should outlive PI-08.

---

## CI (future)

Not wired into CI yet. When that lands:

- GitHub Action runs `docker compose up -d` → `npm ci && npx playwright install --with-deps chromium` → `npm run test:e2e`.
- Upload `playwright-report/` as an artifact on failure.
- Block merges to `main` if e2e fails.
