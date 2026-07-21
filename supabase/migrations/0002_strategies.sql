-- Per-strategy verdicts on every screened ticker (strategy-filter feature).
alter table daily_screens add column if not exists strategies jsonb;
