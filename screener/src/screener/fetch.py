"""Price fetching: chunked yfinance downloads with retries and a parquet cache.

The reliability linchpin. Yahoo rate-limits datacenter IPs, so:
  - download in chunks (default 75 tickers) with exponential backoff + jitter
  - cache each day's downloads as parquet keyed by (as_of, tickers-hash)
  - tolerate partial failure: return what we got, report the misses

Returned shape: dict[ticker -> OHLCV DataFrame] (ascending DatetimeIndex).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache" / "prices"
CHUNK_SIZE = 75


def _cache_path(chunk: list[str], as_of: str) -> Path:
    key = hashlib.sha1((",".join(sorted(chunk))).encode()).hexdigest()[:16]
    return CACHE_DIR / f"{as_of}_{key}.parquet"


@retry(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=5, max=60),
       reraise=True)
def _download_chunk(chunk: list[str], as_of: str) -> pd.DataFrame:
    # start/end anchored to as_of so --as-of backtests get real history
    end = pd.Timestamp(as_of) + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=800)  # ~2.2y calendar => >252+ trading bars
    df = yf.download(
        tickers=chunk,
        start=start.date().isoformat(),
        end=end.date().isoformat(),
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        threads=True,
        progress=False,
    )
    if df is None or df.empty:
        raise RuntimeError(f"empty download for chunk of {len(chunk)}")
    return df


def _split_multi(df: pd.DataFrame, chunk: list[str]) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    cols = ["Open", "High", "Low", "Close", "Volume"]
    for t in chunk:
        try:
            sub = df[t] if isinstance(df.columns, pd.MultiIndex) else df
        except KeyError:
            continue
        sub = sub.dropna(subset=["Close"])
        if sub.empty:
            continue
        out[t] = sub[cols].sort_index()
    return out


def fetch_prices(tickers: list[str], as_of: str, use_cache: bool = True
                 ) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Fetch daily OHLCV for `tickers`. Returns (prices, missing).

    `as_of` (YYYY-MM-DD) is the cache key date; frames are truncated to bars <= as_of
    so backtest (--as-of) and live runs share one code path.
    """
    prices: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    tickers = sorted(set(tickers))

    for i in range(0, len(tickers), CHUNK_SIZE):
        chunk = tickers[i : i + CHUNK_SIZE]
        cache = _cache_path(chunk, as_of)
        raw = None
        if use_cache and cache.exists():
            try:
                raw = pd.read_parquet(cache)
            except Exception:
                cache.unlink(missing_ok=True)
        if raw is None:
            try:
                raw = _download_chunk(chunk, as_of)
            except Exception as e:
                log.warning("chunk %d-%d failed after retries: %s", i, i + len(chunk), e)
                missing.extend(chunk)
                continue
            if use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                try:
                    raw.to_parquet(cache)
                except Exception as e:
                    log.warning("cache write failed: %s", e)

        got = _split_multi(raw, chunk)
        for t in chunk:
            if t in got:
                df = got[t]
                df = df.loc[df.index <= pd.Timestamp(as_of)]
                if df.empty:
                    missing.append(t)
                else:
                    prices[t] = df
            else:
                missing.append(t)

    # Second pass: yf.download swallows per-ticker errors (e.g. transient sqlite
    # cache locks), so retry the stragglers once, uncached, in one small chunk.
    if missing:
        retry_list, missing = missing, []
        try:
            raw = _download_chunk(retry_list, as_of)
            got = _split_multi(raw, retry_list)
        except Exception as e:
            log.warning("retry pass failed: %s", e)
            got = {}
        for t in retry_list:
            df = got.get(t)
            if df is not None:
                df = df.loc[df.index <= pd.Timestamp(as_of)]
            if df is None or df.empty:
                missing.append(t)
            else:
                prices[t] = df

    return prices, missing
