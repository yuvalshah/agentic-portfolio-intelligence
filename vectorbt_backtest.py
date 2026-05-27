import json
import os
import warnings
import pandas as pd
import yfinance as yf
import vectorbt as vbt

warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# STEP 2: Dynamic Signal Ingestion
# ---------------------------------------------------------------------------

def load_signals(filepath="signals_output.json"):
    """
    Read the LangGraph output JSON and classify tickers into
    long_tickers and short_tickers based on Algorithm_Signal.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    signals = data.get("signals", [])

    long_tickers  = []
    short_tickers = []

    for signal in signals:
        algo_signal = signal.get("Algorithm_Signal", "")
        ticker      = signal.get("Stock", "")

        if not ticker:
            continue

        if algo_signal in ["VOLATILITY BUY", "HIDDEN GEM - LONG"]:
            long_tickers.append(ticker)
        elif "SHORT" in algo_signal:
            short_tickers.append(ticker)

    # Remove duplicates while preserving order
    long_tickers  = list(dict.fromkeys(long_tickers))
    short_tickers = list(dict.fromkeys(short_tickers))

    print(f"\n  -> Long  signals loaded  : {long_tickers}")
    print(f"  -> Short signals loaded  : {short_tickers}")

    return long_tickers, short_tickers


# ---------------------------------------------------------------------------
# STEP 3: Real Historical Data Fetching
# ---------------------------------------------------------------------------

def fetch_historical_prices(long_tickers, short_tickers):
    """
    Download adjusted closing prices for all tickers from Yahoo Finance.
    """
    all_tickers = list(dict.fromkeys(long_tickers + short_tickers))

    if not all_tickers:
        print("\n❌ No tickers found in signals_output.json — aborting backtest.")
        exit()

    print(f"\n  -> Fetching historical prices for {len(all_tickers)} ticker(s)...")
    print(f"     Period: 2025-01-01  →  2026-05-26")

    price_df = yf.download(
        all_tickers,
        start="2025-01-01",
        end="2026-05-26",
        progress=False,
    )["Close"]

    # Ensure DataFrame shape even for a single ticker
    if isinstance(price_df, pd.Series):
        price_df = price_df.to_frame(name=all_tickers[0])

    price_df = price_df.ffill()

    print(f"  ✅ Price data loaded: {price_df.shape[0]} trading days × "
          f"{price_df.shape[1]} ticker(s).")

    return price_df


# ---------------------------------------------------------------------------
# STEP 4: Portfolio Simulation
# ---------------------------------------------------------------------------

def run_simulation(price_df, long_tickers, short_tickers):
    """
    Run a vectorbt buy-and-hold simulation using the SEC-derived signals.
    Entries are set on the first available trading day for each position.
    """
    # Initialise boolean signal DataFrames — all False
    entries       = pd.DataFrame(False, index=price_df.index,
                                 columns=price_df.columns)
    short_entries = pd.DataFrame(False, index=price_df.index,
                                 columns=price_df.columns)

    # Set entry on the first row for each relevant ticker
    for ticker in long_tickers:
        if ticker in entries.columns:
            entries.iloc[0][ticker] = True

    for ticker in short_tickers:
        if ticker in short_entries.columns:
            short_entries.iloc[0][ticker] = True

    portfolio = vbt.Portfolio.from_signals(
        price_df,
        entries=entries,
        short_entries=short_entries,
        init_cash=100_000,
        fees=0.001,
        freq="1D",
    )

    print("\n" + "=" * 60)
    print("  INSTITUTIONAL TEAR SHEET: REAL SEC SIGNALS (Jan '25 - May '26)")
    print("=" * 60)
    print(portfolio.stats())


# ---------------------------------------------------------------------------
# STEP 5: Execution Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        long_tickers, short_tickers = load_signals("signals_output.json")
        price_df = fetch_historical_prices(long_tickers, short_tickers)
        run_simulation(price_df, long_tickers, short_tickers)

    except FileNotFoundError:
        print("\n❌ signals_output.json not found.")
        print("   Run main.py first to generate the LangGraph signal output.")
        exit(1)
