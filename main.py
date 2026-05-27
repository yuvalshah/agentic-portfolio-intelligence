import time
import json

from langgraph.graph import StateGraph, END

from state import PortfolioState
from agents import (
    portfolio_analysis_agent,
    smart_inside_strategy_agent,
    institutional_crowding_agent,
    activist_catalyst_agent,
    opportunistic_drift_agent,
    macro_regime_agent,
)
from tools import (
    fetch_form4_data,
    fetch_form144_data,
    fetch_schedule_13d,
    fetch_macro_yields,
    extract_portfolio_from_xml,
)
import requests


# ---------------------------------------------------------------------------
# PRE-PROCESSING HELPERS  (run once per fund, not once per ticker)
# ---------------------------------------------------------------------------

def fetch_fund_sec_data(cik: str) -> dict:
    """
    Fetch the SEC EDGAR submissions JSON for a fund and extract the 3 most
    recent 13F-HR filing URLs.  Returns a dict with keys:
        company_name, thirteen_f_urls, error_message
    """
    padded_cik = str(cik).zfill(10)
    headers = {"User-Agent": "TechMahindra_Intern_Project your.email@techmahindra.com"}
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {"company_name": "", "thirteen_f_urls": [],
                    "error_message": f"SEC API error {response.status_code}"}

        raw = response.json()
        company_name = raw.get("name", "Unknown")

        recent = raw.get("filings", {}).get("recent", {})
        forms        = recent.get("form", [])
        accessions   = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        urls = []
        for i in range(len(forms)):
            if forms[i] == "13F-HR":
                acc = accessions[i].replace("-", "")
                urls.append(
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{padded_cik}/{acc}/{primary_docs[i]}"
                )
                if len(urls) >= 3:
                    break

        return {"company_name": company_name, "thirteen_f_urls": urls, "error_message": ""}

    except Exception as e:
        return {"company_name": "", "thirteen_f_urls": [],
                "error_message": str(e)}


def build_fund_portfolio(thirteen_f_urls: list) -> tuple:
    """
    Parse the two most recent 13F-HR filings and return:
        current_portfolio  – dict  {stock_name: {Stock, Value, Shares}}
        previous_portfolio – dict  (same shape, one quarter older)
    """
    def consolidate(url):
        raw = extract_portfolio_from_xml(url)
        portfolio = {}
        total = 0
        for pos in raw:
            s = pos["Stock"]
            v = pos["Value_($1000s)"]
            sh = pos["Shares"]
            if s in portfolio:
                portfolio[s]["Value_($1000s)"] += v
                portfolio[s]["Shares"] += sh
            else:
                portfolio[s] = {"Stock": s, "Value_($1000s)": v, "Shares": sh}
            total += v
        return portfolio, total

    current_portfolio, current_total = {}, 0
    previous_portfolio = {}

    if len(thirteen_f_urls) >= 1:
        current_portfolio, current_total = consolidate(thirteen_f_urls[0])
    if len(thirteen_f_urls) >= 2:
        previous_portfolio, _ = consolidate(thirteen_f_urls[1])

    return current_portfolio, previous_portfolio, current_total


# ---------------------------------------------------------------------------
# LANGGRAPH PIPELINE EXECUTION
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    institutional_ciks = [
        "0001067983",  # Berkshire Hathaway
        "0001037389",  # Vanguard
        "0001423053",  # Citadel
        "0001350694",  # Bridgewater
        "0001273087",  # BlackRock
        "0001179929",  # State Street
        "0001006438",  # Fidelity
        "0001336528",  # Renaissance Technologies
        "0001167483",  # Two Sigma
        "0001167557",  # D.E. Shaw
    ]

    target_universe = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "JNJ",
        "WMT", "PG", "MA", "UNH", "DIS", "HD", "BAC", "VZ", "NFLX", "ADBE",
        "CRM", "CMCSA", "PFE", "INTC", "T", "ABT", "PEP", "KO", "CSCO", "XOM",
        "CVX", "NKE", "MCD", "MDT", "COST", "MRK", "TMO", "AVGO", "TXN", "ACN",
        "QCOM", "HON", "UNP", "LIN", "PM", "NEE", "BMY", "LOW", "SBUX", "BA",
        "IBM", "GS", "CAT", "GE", "MMM", "C", "RTX", "CVS", "INTU", "AMD",
        "ISRG", "SYK", "ZTS", "GILD", "BKNG", "MDLZ", "LMT", "TJX", "ADP", "CB",
        "MMC",
    ]

    # ------------------------------------------------------------------
    # Compile the LangGraph workflow (strategy agents only — no network I/O)
    # ------------------------------------------------------------------
    print("\n=== COMPILING LANGGRAPH WORKFLOW ===")

    workflow = StateGraph(PortfolioState)
    workflow.add_node("AnalysisNode",    portfolio_analysis_agent)
    workflow.add_node("SmartInsideNode", smart_inside_strategy_agent)
    workflow.add_node("ActivistNode",    activist_catalyst_agent)
    workflow.add_node("DriftNode",       opportunistic_drift_agent)
    workflow.add_node("MacroNode",       macro_regime_agent)

    workflow.set_entry_point("AnalysisNode")
    workflow.add_edge("AnalysisNode",    "SmartInsideNode")
    workflow.add_edge("SmartInsideNode", "ActivistNode")
    workflow.add_edge("ActivistNode",    "DriftNode")
    workflow.add_edge("DriftNode",       "MacroNode")
    workflow.add_edge("MacroNode",       END)

    app = workflow.compile()

    # ------------------------------------------------------------------
    # Fetch macro regime ONCE — same for every fund and ticker
    # ------------------------------------------------------------------
    print("\n  -> Fetching live macro regime (Treasury yield curve)...")
    macro_regime_value = fetch_macro_yields()
    print(f"  -> Macro Regime: {macro_regime_value}")

    master_quant_signals = []

    # ------------------------------------------------------------------
    # OUTER LOOP: one SEC EDGAR fetch per fund  (10 network calls total)
    # ------------------------------------------------------------------
    for cik in institutional_ciks:
        print(f"\n{'='*60}")
        print(f"  PROCESSING FUND CIK: {cik}")
        print(f"{'='*60}")

        # --- Phase 1: fetch SEC data ONCE for this fund ---
        print("  -> [Phase 1] Fetching SEC EDGAR submissions...")
        sec_data = fetch_fund_sec_data(cik)

        if sec_data["error_message"]:
            print(f"  -> [ERROR] {sec_data['error_message']} — skipping fund.")
            continue

        print(f"  -> Fund: {sec_data['company_name']} | "
              f"{len(sec_data['thirteen_f_urls'])} 13F-HR filing(s) found.")

        if not sec_data["thirteen_f_urls"]:
            print("  -> No 13F-HR filings found — skipping fund.")
            continue

        # --- Phase 2: parse the 13F XML filings ONCE for this fund ---
        print("  -> [Phase 2] Parsing 13F portfolio XML...")
        current_portfolio, previous_portfolio, current_total = \
            build_fund_portfolio(sec_data["thirteen_f_urls"])

        time.sleep(0.2)  # Respect SEC rate limit after the XML fetches

        if not current_portfolio:
            print("  -> Empty portfolio parsed — skipping fund.")
            continue

        print(f"  -> Portfolio loaded: {len(current_portfolio)} unique positions.")

        # Fetch alternative data streams ONCE per fund
        # (Form 4 / 144 / 13D are ticker-specific but cheap — fetched per ticker below)

        # ------------------------------------------------------------------
        # INNER LOOP: pure in-memory strategy evaluation per ticker
        # ------------------------------------------------------------------
        for ticker in target_universe:

            # Check if this fund even holds the target ticker (fast dict lookup)
            ticker_upper = ticker.upper()
            held = any(ticker_upper in stock.upper() for stock in current_portfolio)
            if not held:
                continue  # Fund doesn't hold this stock — skip immediately

            print(f"\n  --- [{cik}] Evaluating ticker: {ticker} ---")

            # Fetch ticker-specific alternative data (lightweight)
            form4   = fetch_form4_data(ticker)
            form144 = fetch_form144_data(ticker)
            sched13d = fetch_schedule_13d(ticker)

            # Build the pre-populated state — no SEC calls needed inside the graph
            initial_input: PortfolioState = {
                "target_asset":        ticker,
                "cik":                 cik,
                "company_name":        sec_data["company_name"],
                "raw_13f_data":        {},
                "form_4_data":         form4,
                "form_144_data":       form144,
                "schedule_13d_data":   sched13d,
                "error_message":       "",
                "thirteen_f_urls":     sec_data["thirteen_f_urls"],
                "analyzed_portfolio":  [],
                "quant_signals":       [],
                "macro_regime":        macro_regime_value,
                # Pre-built portfolio cache — AnalysisNode reads these directly
                "current_portfolio":   current_portfolio,
                "previous_portfolio":  previous_portfolio,
                "current_total":       current_total,
            }

            final_state = app.invoke(initial_input)

            # Aggregate signals into the master ledger
            signals = final_state.get("quant_signals", [])
            for signal in signals:
                signal["Fund_CIK"] = cik
                master_quant_signals.append(signal)

    # ---------------------------------------------------------------------------
    # Final aggregated output — Master Quant Signal Ledger
    # ---------------------------------------------------------------------------

    print(f"\n\n{'='*60}")
    print("  MASTER QUANT SIGNAL LEDGER — 10-FUND UNIVERSE")
    print(f"{'='*60}")

    if master_quant_signals:
        col_w = [14, 28, 30, 18, 22, 17]
        headers = ["Fund_CIK", "Stock", "13F_Action", "Form4_Action",
                   "Algorithm_Signal", "Conviction_Score"]
        divider    = "  ".join("-" * w for w in col_w)
        header_row = "  ".join(h.ljust(col_w[i]) for i, h in enumerate(headers))

        print(divider)
        print(header_row)
        print(divider)

        for sig in master_quant_signals:
            row = "  ".join([
                str(sig.get("Fund_CIK",         "")).ljust(col_w[0]),
                str(sig.get("Stock",            "")).ljust(col_w[1]),
                str(sig.get("13F_Action",       "")).ljust(col_w[2]),
                str(sig.get("Form4_Action",     "")).ljust(col_w[3]),
                str(sig.get("Algorithm_Signal", "")).ljust(col_w[4]),
                str(sig.get("Conviction_Score", "")).ljust(col_w[5]),
            ])
            print(row)

        print(divider)
        print(f"\n✅ {len(master_quant_signals)} signal(s) aggregated across "
              f"{len(institutional_ciks)} funds × {len(target_universe)} tickers.")
    else:
        print("\nℹ️  No quant signals generated across the fund universe.")

    # ---------------------------------------------------------------------------
    # Institutional Crowding Strategy — Market-Neutral Portfolio
    # ---------------------------------------------------------------------------

    market_neutral_portfolio = institutional_crowding_agent(master_quant_signals)

    print(f"\n\n{'='*60}")
    print("  INSTITUTIONAL CROWDING STRATEGY (MARKET-NEUTRAL)")
    print(f"{'='*60}")

    if market_neutral_portfolio:
        col_w = [30, 20, 26]
        headers = ["Stock", "Funds_Accumulating", "Target_Position"]
        divider    = "  ".join("-" * w for w in col_w)
        header_row = "  ".join(h.ljust(col_w[i]) for i, h in enumerate(headers))

        print(divider)
        print(header_row)
        print(divider)

        for entry in market_neutral_portfolio:
            row = "  ".join([
                str(entry.get("Stock",           "")).ljust(col_w[0]),
                str(entry.get("Fund_Count",      "")).ljust(col_w[1]),
                str(entry.get("Strategy_Action", "")).ljust(col_w[2]),
            ])
            print(row)

        print(divider)
        longs  = sum(1 for e in market_neutral_portfolio if "LONG"  in e["Strategy_Action"])
        shorts = sum(1 for e in market_neutral_portfolio if "SHORT" in e["Strategy_Action"])
        print(f"\n✅ Market-Neutral Portfolio: {longs} LONG  |  {shorts} SHORT")
    else:
        print("\nℹ️  No crowding signals detected across the fund universe.")

    # ---------------------------------------------------------------------------
    # Export Master Ledger to JSON for AutoGen Investment Committee
    # ---------------------------------------------------------------------------

    output_data = {
        "macro_regime": macro_regime_value if "macro_regime_value" in dir() else "NORMAL",
        "signals": master_quant_signals,
    }

    with open("signals_output.json", "w") as f:
        json.dump(output_data, f, indent=4)

    print("\n✅ Master Ledger exported to signals_output.json. Ready for AutoGen Committee.")
