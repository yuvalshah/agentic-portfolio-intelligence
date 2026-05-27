import os
import time
import pandas as pd
import yfinance as yf
from datetime import datetime


# ---------------------------------------------------------------------------
# STEP 2: Ledger Management
# ---------------------------------------------------------------------------

def initialize_ledger():
    """Create portfolio_ledger.csv if it does not already exist."""
    if not os.path.exists("portfolio_ledger.csv"):
        df = pd.DataFrame(columns=[
            "Ticker", "Direction", "Entry_Date", "Entry_Price", "Status"
        ])
        df.to_csv("portfolio_ledger.csv", index=False)
        print("✅ Ledger initialized: portfolio_ledger.csv created.")
    else:
        print("✅ Ledger already exists: portfolio_ledger.csv loaded.")


# ---------------------------------------------------------------------------
# STEP 3: Trade Execution (Simulated Entry)
# ---------------------------------------------------------------------------

def execute_trades(entry_date="2026-01-01"):
    """
    Execute the LLM Committee's approved trades into the ledger.
    Fetches the first available closing price on or after entry_date.
    Skips execution if the ledger already contains trades (idempotent).
    """
    approved_trades = [
        {"Ticker": "MCD", "Direction": "SHORT"},
        {"Ticker": "HD",  "Direction": "SHORT"},
        {"Ticker": "GS",  "Direction": "LONG"},
    ]

    ledger = pd.read_csv("portfolio_ledger.csv")

    if not ledger.empty:
        print("ℹ️  Ledger already contains trades — skipping execution to avoid duplicates.")
        return

    print(f"\n{'='*60}")
    print(f"  EXECUTING APPROVED TRADES  (entry date: {entry_date})")
    print(f"{'='*60}")

    rows = []
    for trade in approved_trades:
        ticker    = trade["Ticker"]
        direction = trade["Direction"]

        try:
            time.sleep(2.0)
            tkr  = yf.Ticker(ticker)
            data = tkr.history(start=entry_date, end="2026-01-10")["Close"]

            if data.empty:
                print(f"  [WARNING] No price data found for {ticker} — skipping.")
                continue

            entry_price = round(float(data.iloc[0]), 2)
            actual_date = str(data.index[0].date())

            rows.append({
                "Ticker":      ticker,
                "Direction":   direction,
                "Entry_Date":  actual_date,
                "Entry_Price": entry_price,
                "Status":      "OPEN",
            })
            print(f"  ✅ {direction:<5} {ticker:<5}  Entry: ${entry_price:.2f}  "
                  f"(first available date: {actual_date})")

        except Exception as e:
            print(f"  [ERROR] Failed to fetch price for {ticker}: {e}")

    if rows:
        new_rows = pd.DataFrame(rows)
        ledger   = pd.concat([ledger, new_rows], ignore_index=True)
        ledger.to_csv("portfolio_ledger.csv", index=False)
        print(f"\n✅ {len(rows)} trade(s) written to portfolio_ledger.csv.")
    else:
        print("\n⚠️  No trades were written — all fetches failed.")


# ---------------------------------------------------------------------------
# STEP 4: Mark-to-Market — Live PnL Dashboard
# ---------------------------------------------------------------------------

def calculate_live_pnl():
    """
    Fetch current prices for all OPEN positions and print a live PnL dashboard.
    """
    ledger = pd.read_csv("portfolio_ledger.csv")

    if ledger.empty:
        print("❌ Error: portfolio_ledger.csv is empty. Run execute_trades() first.")
        return

    open_trades = ledger[ledger["Status"] == "OPEN"]

    if open_trades.empty:
        print("ℹ️  No open trades found in the ledger.")
        return

    print(f"\n{'='*60}")
    print(f"  LIVE MARK-TO-MARKET PnL DASHBOARD")
    print(f"  As of: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    pnl_list = []

    for _, row in open_trades.iterrows():
        ticker      = row["Ticker"]
        direction   = row["Direction"]
        entry_price = float(row["Entry_Price"])

        try:
            time.sleep(2.0)
            tkr          = yf.Ticker(ticker)
            current_data = tkr.history(period="1d")["Close"]
            current_price = round(float(current_data.iloc[-1]), 2)

            if direction == "LONG":
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # SHORT
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

            pnl_list.append(pnl_pct)

            arrow = "🟢" if pnl_pct >= 0 else "🔴"
            print(f"  {arrow} [{direction:<5}] {ticker:<5} | "
                  f"Entry: ${entry_price:>8.2f} | "
                  f"Current: ${current_price:>8.2f} | "
                  f"PnL: {pnl_pct:>+7.2f}%")

        except Exception as e:
            print(f"  [ERROR] Could not fetch current price for {ticker}: {e}")

    if pnl_list:
        avg_pnl = sum(pnl_list) / len(pnl_list)
        print(f"\n{'─'*60}")
        arrow = "🟢" if avg_pnl >= 0 else "🔴"
        print(f"  {arrow}  Total Portfolio Average PnL: {avg_pnl:>+7.2f}%")
        print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# STEP 5: Execution Block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    initialize_ledger()
    execute_trades()
    calculate_live_pnl()
