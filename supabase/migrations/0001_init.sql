-- stocks-analyzer initial schema
-- Run in Supabase SQL editor (or supabase db push).

create table positions (
  id bigint generated always as identity primary key,
  ticker text not null,
  entry_price numeric not null,
  shares numeric not null,
  entry_date date not null,
  stop_price numeric,                -- default computed = entry*0.92; user-overridable
  status text not null default 'open' check (status in ('open','closed')),
  exit_price numeric,
  closed_at date,
  notes text,
  created_at timestamptz not null default now()
);

create table quality_universe (
  ticker text primary key,
  name text,
  exchange text,
  passes boolean not null,
  fail_reasons text[] not null default '{}',
  roe numeric,
  roic numeric,
  debt_to_equity numeric,
  fcf numeric,
  rev_growth_3y numeric,
  eps_growth_3y numeric,
  gross_margin_avg numeric,
  gross_margin_stdev numeric,
  raw jsonb,
  checked_at timestamptz not null default now()
);

create table daily_screens (
  id bigint generated always as identity primary key,
  screen_date date not null,
  ticker text not null,
  close numeric,
  ma50 numeric,
  ma150 numeric,
  ma200 numeric,
  pct_above_52w_low numeric,
  pct_off_52w_high numeric,
  rs_score numeric,
  rs_percentile numeric,
  tt_criteria jsonb not null,
  tt_pass boolean not null,
  vcp jsonb,
  setup_status text check (setup_status in ('none','base_forming','pivot_near','breakout')),
  unique (screen_date, ticker)
);
create index on daily_screens (screen_date desc, tt_pass, rs_percentile desc);

create table signals (
  id bigint generated always as identity primary key,
  signal_date date not null,
  ticker text not null,
  type text not null check (type in
    ('BUY','WATCH','SELL_STOP','SELL_STRENGTH','SELL_TRAIL_50D','SELL_200D','CLIMAX_WARN')),
  price numeric,
  buy_point numeric,
  stop_price numeric,
  sizing jsonb,
  details jsonb,
  position_id bigint references positions(id),
  emailed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (signal_date, ticker, type)
);

create table rs_reference (
  as_of date primary key,
  breakpoints jsonb not null           -- 101-element array: RS score at percentile 0..100
);

create table runs (
  id bigint generated always as identity primary key,
  run_date date not null,
  kind text not null check (kind in ('daily','weekly')),
  status text not null default 'running' check (status in ('running','ok','failed','skipped')),
  regime jsonb,
  stats jsonb,
  error text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

insert into settings (key, value) values
  ('equity',        '100000'),
  ('risk_pct',      '1.25'),
  ('max_position_pct', '25'),
  ('regime_mode',   '"both"'),         -- both | either | spy_only
  ('email_policy',  '"on_change"');

-- Single-user app: RLS on with no policies => anon key sees nothing.
-- Screener job and the web server both use the service key, which bypasses RLS.
alter table positions enable row level security;
alter table quality_universe enable row level security;
alter table daily_screens enable row level security;
alter table signals enable row level security;
alter table rs_reference enable row level security;
alter table runs enable row level security;
alter table settings enable row level security;
