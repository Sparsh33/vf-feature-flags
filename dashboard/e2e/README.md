# E2E tests

Playwright end-to-end tests for the feature-flags dashboard, run against a live stack.

## Prerequisite — stack running

From the repo root:

```
docker-compose up -d           # mongo, redis, backend api, worker, dashboard
# or bring up backend (:8000) + worker + dashboard (:5173) yourself
```

Sanity check: `curl http://localhost:8000/health` and open `http://localhost:5173`.

## Run

From `dashboard/`:

```
npm run test:e2e          # headless
npm run test:e2e:ui       # Playwright UI mode (interactive)
npm run test:e2e:headed   # headed browser
```

## Serial execution + shared state

Specs run **serially** (`workers=1`, `fullyParallel=false`) because they share DB
state. The auth context, captured API key, primary-user credentials, and the
seeded flag id/key are persisted to `e2e/.state/` and consumed by later specs:

| File                 | Written by     | Consumed by                          |
|----------------------|----------------|--------------------------------------|
| `auth.json`          | `01-auth`      | `02-flags-crud`, `03..05`            |
| `api-key.txt`        | `01-auth`      | `04-analytics-audit`, `05-settings`  |
| `primary-user.json`  | `01-auth`      | (informational)                      |
| `flag-info.json`     | `02-flags-crud`| `04-analytics-audit`                 |

`e2e/.state/` is gitignored.

## Specs

- `01-auth.spec.ts` — signup (captures API key), login, bad creds, `/me` persistence.
- `02-flags-crud.spec.ts` — create flag w/ cohorts, 110% disables save, distribute
  remaining, soft delete, cross-client isolation.
- `03-nl-chat.spec.ts` — NL builder round-trip (slow; LLM-dependent; lenient).
- `04-analytics-audit.spec.ts` — seeds 20 eval calls, then analytics overview,
  drilldown, range picker, audit log + drawer.
- `05-settings.spec.ts` — rotate API key; asserts new key differs.

## Reports

HTML report is written to `playwright-report/` (gitignored) after each run.
Open with `npx playwright show-report`.
