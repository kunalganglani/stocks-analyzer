// Single source of plain-language copy for everything the pipeline emits.
// The user is a non-technical trader: no jargon leaves this file untranslated.

export type Tone = "buy" | "danger" | "warn" | "info" | "neutral";
export type SignalMeta = { label: string; explain: string; tone: Tone };

export const SIGNAL_META: Record<string, SignalMeta> = {
  BUY: {
    label: "Buy",
    explain: "Quality stock breaking out while the market is healthy — all checks aligned.",
    tone: "buy",
  },
  WATCH: {
    label: "Watch",
    explain: "Almost a buy — one condition still missing.",
    tone: "warn",
  },
  SELL_STOP: {
    label: "Stop hit — exit now",
    explain: "Price fell to your stop level. Sell to cap the loss — protecting capital comes first.",
    tone: "danger",
  },
  SELL_STRENGTH: {
    label: "Up 20%+ — consider taking profit",
    explain: "Strong gain reached. Selling into strength locks it in (at least partially).",
    tone: "info",
  },
  SELL_TRAIL_50D: {
    label: "Trend weakening",
    explain: "Closed below its 50-day average line on heavy volume — the uptrend may be ending.",
    tone: "danger",
  },
  SELL_200D: {
    label: "Long-term trend broken",
    explain: "Closed below its 200-day average line — the exit signal.",
    tone: "danger",
  },
  CLIMAX_WARN: {
    label: "Going vertical",
    explain: "Climbing unusually fast while far extended — classic top behavior. Consider selling into strength.",
    tone: "warn",
  },
};

export function signalMeta(type: string): SignalMeta {
  return SIGNAL_META[type] ?? { label: type, explain: "", tone: "neutral" };
}

export const WATCH_REASON: Record<string, string> = {
  regime_blocked: "Setup is ready, but the overall market is weak — buys are paused.",
  setup_forming: "Base is building — not at its buy point yet.",
};

export const SETUP_META: Record<string, { label: string; explain: string; tone: Tone }> = {
  breakout: { label: "BUY zone", explain: "Broke above its pivot on strong volume.", tone: "buy" },
  pivot_near: { label: "Almost ready", explain: "Within striking distance of its buy point.", tone: "warn" },
  base_forming: { label: "Building base", explain: "Consolidating — needs more time.", tone: "neutral" },
  none: { label: "—", explain: "", tone: "neutral" },
};

export const TT_CRITERIA_LABELS: Record<string, string> = {
  c1_price_above_150_200: "Price above its 150- and 200-day lines",
  c2_ma150_above_200: "150-day line above the 200-day line",
  c3_ma200_rising_1m: "200-day line rising for a month",
  c4_ma50_above_150_200: "50-day line above both longer lines",
  c5_price_above_50: "Price above its 50-day line",
  c6_above_52w_low_30pct: "At least 30% above its 52-week low",
  c7_within_25pct_of_high: "Within 25% of its 52-week high",
  c8_rs_ge_70: "Stronger than 70%+ of all US stocks",
};

export function regimeCopy(riskOn: boolean | null | undefined): {
  label: string;
  explain: string;
  tone: Tone;
} {
  if (riskOn == null)
    return { label: "No market data yet", explain: "Run the screener to get a first reading.", tone: "neutral" };
  return riskOn
    ? {
        label: "Market healthy",
        explain: "S&P 500 and Nasdaq are both above their 200-day trend lines — buying is allowed.",
        tone: "buy",
      }
    : {
        label: "Market weak — sitting out",
        explain: "New buys are paused until the index trend recovers. Sell protection still runs daily.",
        tone: "danger",
      };
}
