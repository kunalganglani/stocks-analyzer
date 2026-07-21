# stocks-analyzer

Personal stock screener + buy/sell alert tool distilling **Mark Minervini** (SEPA:
trend template, VCP entries, hard risk management) and **Buffett/Munger** (only
quality businesses). Signals fire **only when every gate agrees**:

```
BUY  =  quality fundamentals  ∧  8/8 trend template  ∧  VCP breakout on volume
        ∧  risk-on market (SPY & QQQ > 200d MA)  ∧  not already bought recently
SELL =  per logged position: stop hit · +20% strength · 50d break on volume
        · 200d break · climax run          (regime-independent, every day)
```

## Architecture ($0/month)

```
GitHub Actions (public repo = unlimited free minutes)   Firebase App Hosting (Next.js 16)
  daily-screen  22:30 UTC weekdays                        web/ dashboard
  weekly-fundamentals  Sun 08:00 UTC                        │  4 pages + password
  + "Run now" button (workflow_dispatch)                    ▼  proxy auth
                      Supabase Postgres  ◀────────────── server-side service key
                        signals · screens · positions · settings
                      Resend ──▶ email (only when something happened)
```

- `screener/` — Python engine. Pure-function analytics (`indicators`, `trend_template`,
  `rs`, `vcp`, `sell_rules`, `regime`), data layer (`universe`, `fetch`), decision core
  (`confluence`, `sizing`), jobs (`run_daily`, `run_weekly`), `alerts`.
- `web/` — Next.js dashboard: Dashboard / Screener / Positions / Signals, single-user
  password auth (HMAC cookie via `src/proxy.ts`), positions CRUD, "Run screener now".
- `supabase/migrations/0001_init.sql` — full schema; RLS on with no policies
  (anon key sees nothing; only the service key is used, server-side).

## Local dev

```bash
cd screener && uv sync && uv run pytest          # 28 unit tests
uv run python -m screener.jobs.run_daily --tickers NVDA,MSFT --dry-run
uv run python -m screener.jobs.run_daily --as-of 2024-03-01 --tickers NVDA,PYPL --dry-run
uv run python -m screener.jobs.run_weekly --tickers NVDA,BA --dry-run --limit 5

cd web && npm install && npm run dev             # needs .env (see .env.example)
```

## Go-live checklist

1. **Supabase** ✅: project created, migration applied via Management API.
2. **Resend** ✅: key in `.env` (local only, never committed).
3. **GitHub Actions secrets**: repo → Settings → Secrets and variables → Actions →
   add `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `RESEND_API_KEY`
   (optionally vars `ALERT_FROM`, `ALERT_TO`). Public repo = unlimited free minutes.
4. **Firebase App Hosting**: console → App Hosting → create backend → connect this
   GitHub repo, root directory `web/`, live branch `main`. Requires the Blaze plan
   (free quotas cover this app). Then set secrets:
   `firebase apphosting:secrets:set supabase-service-key / access-password /
   session-secret / gh-pat` (grant access to the backend when prompted);
   non-secret env is in `web/apphosting.yaml`.
5. **Run-now button**: create a fine-grained PAT (repo-scoped, Actions read/write) →
   `gh-pat` secret above.
6. **First data**: Actions tab → run `weekly-fundamentals` once (populates quality
   universe + RS reference, ~1-2h), then `daily-screen`; check dashboard + inbox.
7. **Verify before trusting money**: add a test position with an entry far above market →
   next daily run must email SELL_STOP; rerun the same day twice → no duplicate email.

## Tuning

All thresholds live in `screener/src/screener/config.py`; account settings
(equity, risk % per trade, regime mode, email policy) live in the `settings`
table and can be changed without redeploying.
