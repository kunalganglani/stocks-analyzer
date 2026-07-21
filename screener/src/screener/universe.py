"""US common-stock universe from nasdaqtrader.com symbol directories.

Two pipe-delimited files, refreshed nightly by Nasdaq:
  nasdaqlisted.txt — NASDAQ listings (Test Issue, ETF flags)
  otherlisted.txt  — NYSE/AMEX/etc ("ACT Symbol", Exchange, ETF, Test Issue)

We keep plain common stock: drop ETFs, test issues, and symbols with
suffixes indicating warrants/units/rights/preferreds ($, ., =, -, ^).
Liquidity (price/dollar-volume) is filtered later, using price data.
"""

from __future__ import annotations

import io
import re

import httpx
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

NASDAQ_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_URL = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

_CLEAN_SYMBOL = re.compile(r"^[A-Z]{1,5}$")


@retry(stop=stop_after_attempt(4), wait=wait_exponential_jitter(initial=2, max=30))
def _get(url: str) -> str:
    r = httpx.get(url, timeout=30, follow_redirects=True)
    r.raise_for_status()
    return r.text


def _parse(text: str, symbol_col: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(text), sep="|")
    df = df[~df[symbol_col].astype(str).str.startswith("File Creation")]
    return df


def fetch_symbols() -> pd.DataFrame:
    """Return DataFrame[ticker, name, exchange] of US common stocks."""
    frames = []

    nas = _parse(_get(NASDAQ_URL), "Symbol")
    nas = nas[(nas["Test Issue"] == "N") & (nas["ETF"] == "N")]
    frames.append(pd.DataFrame({
        "ticker": nas["Symbol"].astype(str),
        "name": nas["Security Name"].astype(str),
        "exchange": "NASDAQ",
    }))

    oth = _parse(_get(OTHER_URL), "ACT Symbol")
    oth = oth[(oth["Test Issue"] == "N") & (oth["ETF"] == "N")]
    exch_map = {"N": "NYSE", "A": "AMEX", "P": "NYSEARCA", "Z": "BATS", "V": "IEXG"}
    frames.append(pd.DataFrame({
        "ticker": oth["ACT Symbol"].astype(str),
        "name": oth["Security Name"].astype(str),
        "exchange": oth["Exchange"].map(exch_map).fillna("OTHER"),
    }))

    df = pd.concat(frames, ignore_index=True)
    df = df[df["ticker"].str.match(_CLEAN_SYMBOL)]  # drops warrants/units/rights/preferreds
    name_l = df["name"].str.lower()
    junk = name_l.str.contains(
        r"\b(?:warrants?|rights?|units?|preferred|depositary|acquisition|etn|notes?)\b"
        r"|%|due \d{4}|fund|trust, ",
        regex=True,
    )
    df = df[~junk]
    return df.drop_duplicates("ticker").reset_index(drop=True)


def liquidity_filter(prices: dict[str, pd.DataFrame],
                     min_price: float, min_avg_dollar_volume: float) -> list[str]:
    """Tickers whose last close and 50d avg dollar volume clear the bars."""
    from .indicators import avg_dollar_volume

    keep = []
    for t, df in prices.items():
        if df is None or df.empty or len(df) < 60:
            continue
        if float(df["Close"].iloc[-1]) < min_price:
            continue
        adv = avg_dollar_volume(df)
        if adv is not None and adv >= min_avg_dollar_volume:
            keep.append(t)
    return keep
