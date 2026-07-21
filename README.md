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
Cloud Scheduler ──▶ Cloud Build (python 3.12 + uv)          Vercel (Next.js 16)
  daily 22:30 UTC     screener/ jobs                          web/ dashboard
  weekly Sun 08:00      │  yfinance prices+fundamentals         │  4 pages + password
  + "Run now" button    ▼                                       ▼  proxy auth
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

1. **Supabase**: create free project → SQL editor → run `supabase/migrations/0001_init.sql`
   → copy URL + service-role key.
2. **Resend**: create API key (free tier). Default `ALERT_FROM` uses onboarding@resend.dev;
   verify a domain later for nicer sender.
3. **GitHub**: push this repo (private is fine — compute runs on GCP).
4. **GCP**: console → Cloud Build → connect the GitHub repo (2nd-gen connection), then
   `PROJECT=<id> REPO_OWNER=<you> bash scripts/setup-gcp.sh` (writes secret, 2 triggers,
   2 scheduler jobs). Test: `gcloud builds triggers run stocks-daily --branch main`.
5. **Vercel**: import `web/` → set env vars from `web/.env.example`
   (`CLOUD_BUILD_TRIGGER_ID` = daily trigger id from step 4).
6. **First data**: run the weekly trigger once (populates quality universe + RS reference),
   then the daily trigger; check the dashboard and your inbox.
7. **Verify before trusting money**: add a test position with an entry far above market →
   next daily run must email SELL_STOP; rerun the same day twice → no duplicate email.

## Tuning

All thresholds live in `screener/src/screener/config.py`; account settings
(equity, risk % per trade, regime mode, email policy) live in the `settings`
table and can be changed without redeploying.
