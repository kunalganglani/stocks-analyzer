export function TickerLink({ ticker, className = "" }: { ticker: string; className?: string }) {
  return (
    <a
      href={`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(ticker)}`}
      target="_blank"
      rel="noopener noreferrer"
      title={`Open ${ticker} chart on TradingView`}
      className={`inline-flex items-center gap-1 font-semibold hover:text-emerald-600 dark:hover:text-emerald-400 ${className}`}
    >
      {ticker}
      <svg className="size-3 text-faint" viewBox="0 0 24 24" fill="none" stroke="currentColor"
        strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      </svg>
    </a>
  );
}
