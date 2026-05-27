import requests
from typing import Dict, Any

from state import PortfolioState
from tools import fetch_form4_data, fetch_form144_data, fetch_schedule_13d, fetch_macro_yields


# ---------------------------------------------------------------------------
# AGENT 1: Omni-Retrieval — Perception Layer
# ---------------------------------------------------------------------------

def omni_retrieval_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 1: OMNI-RETRIEVAL] Initiating Perception Layer ---")

    target_asset = state.get("target_asset", "UNKNOWN")
    target_cik = state.get("cik")
    padded_cik = str(target_cik).zfill(10)

    print(f"Targeting SEC EDGAR & Alternative Feeds for: {target_asset} (CIK: {padded_cik})")

    # --- STREAM A: Institutional History (Real SEC EDGAR Call) ---
    headers = {"User-Agent": "TechMahindra_Intern_Project your.email@techmahindra.com"}
    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"

    raw_13f = {}
    company_name = ""
    error = ""

    try:
        print(f"  -> [Stream A] Fetching 13F Institutional History...")
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            raw_13f = response.json()
            company_name = raw_13f.get("name", "Unknown Company")
        else:
            error = f"SEC API blocked the request. Status: {response.status_code}"
    except Exception as e:
        error = f"System Failure during 13F retrieval: {str(e)}"

    if error:
        return {"error_message": error}

    # --- STREAM B: Insider Trading Data (Form 4 & 144) ---
    form4 = fetch_form4_data(target_asset)
    form144 = fetch_form144_data(target_asset)

    # --- STREAM C: Activist Catalysts (Schedule 13D) ---
    schedule13d = fetch_schedule_13d(target_asset)

    print(f"Success! Normalized and packaged all data streams for {company_name}.")

    return {
        "company_name": company_name,
        "raw_13f_data": raw_13f,
        "form_4_data": form4,
        "form_144_data": form144,
        "schedule_13d_data": schedule13d,
        "error_message": ""
    }


# ---------------------------------------------------------------------------
# AGENT 2: Data Processing — Filing URL Extraction
# ---------------------------------------------------------------------------

def data_processing_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 2: PROCESSING] Initiating ---")

    raw_data = state.get("raw_13f_data", {})
    cik = state.get("cik")
    padded_cik = str(cik).zfill(10)

    if not raw_data or state.get("error_message"):
        print("Error: No raw data found from Agent 1.")
        return {"thirteen_f_urls": []}

    thirteen_f_urls = []

    try:
        recent_filings = raw_data.get("filings", {}).get("recent", {})
        forms = recent_filings.get("form", [])
        accession_numbers = recent_filings.get("accessionNumber", [])
        primary_documents = recent_filings.get("primaryDocument", [])

        print(f"Scanning {len(forms)} total historical documents...")

        for i in range(len(forms)):
            if forms[i] == "13F-HR":
                acc_num_no_dashes = accession_numbers[i].replace("-", "")
                document_name = primary_documents[i]
                url = f"https://www.sec.gov/Archives/edgar/data/{padded_cik}/{acc_num_no_dashes}/{document_name}"
                thirteen_f_urls.append(url)

                # Limit to the 3 most recent filings
                if len(thirteen_f_urls) >= 3:
                    break

        print(f"Successfully extracted {len(thirteen_f_urls)} recent 13F-HR URLs.")
        return {"thirteen_f_urls": thirteen_f_urls, "error_message": ""}

    except Exception as e:
        error = f"System Failure during processing: {str(e)}"
        print(error)
        return {"error_message": error, "thirteen_f_urls": []}


# ---------------------------------------------------------------------------
# AGENT 3: Portfolio Analysis — Holdings & Historical Trends
# ---------------------------------------------------------------------------

def portfolio_analysis_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 3: PORTFOLIO ANALYSIS] Evaluating ticker position ---")

    target_asset   = state.get("target_asset", "UNKNOWN")
    current_portfolio  = state.get("current_portfolio", {})
    previous_portfolio = state.get("previous_portfolio", {})
    current_total      = state.get("current_total", 0)

    if not current_portfolio:
        return {"analyzed_portfolio": []}

    analyzed_portfolio = []

    for stock, current_data in current_portfolio.items():
        # Only analyse positions that match the target ticker
        if target_asset.upper() not in stock.upper():
            continue

        weight = (current_data["Value_($1000s)"] / current_total * 100
                  if current_total > 0 else 0)
        current_data = dict(current_data)          # avoid mutating the cache
        current_data["Weight_%"] = round(weight, 4)

        prev_shares  = previous_portfolio.get(stock, {}).get("Shares", 0)
        share_change = current_data["Shares"] - prev_shares

        if prev_shares == 0:
            current_data["Trade_Action"] = "NEW BUY 🟢"
        elif share_change > 0:
            current_data["Trade_Action"] = f"ADDED (+{share_change:,}) 🟢"
        elif share_change < 0:
            current_data["Trade_Action"] = f"REDUCED ({share_change:,}) 🔴"
        else:
            current_data["Trade_Action"] = "HELD ⚪"

        analyzed_portfolio.append(current_data)

    # Check for complete sell-out since last quarter
    for stock, prev_data in previous_portfolio.items():
        if target_asset.upper() not in stock.upper():
            continue
        if stock not in current_portfolio:
            analyzed_portfolio.append({
                "Stock": stock,
                "Value_($1000s)": 0,
                "Shares": 0,
                "Weight_%": 0.0,
                "Trade_Action": f"SOLD OUT (-{prev_data['Shares']:,}) ❌"
            })

    analyzed_portfolio = sorted(analyzed_portfolio,
                                key=lambda x: x["Weight_%"], reverse=True)
    return {"analyzed_portfolio": analyzed_portfolio, "error_message": ""}


# ---------------------------------------------------------------------------
# AGENT 4: Smart Inside Strategy — Quant Signal Generation
# ---------------------------------------------------------------------------

def smart_inside_strategy_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 4: SMART INSIDE STRATEGY] Initiating Signal Generation ---")

    analyzed_portfolio = state.get("analyzed_portfolio", [])
    form_4_data = state.get("form_4_data", [])

    # Filter live FMP data for actual purchases only — exclude disposals and sales
    insider_buys = [
        trade for trade in form_4_data
        if trade.get("acquistionOrDisposition") == "A"
        or trade.get("transactionType") in ["P-Purchase", "P"]
    ]

    quant_signals = []

    # Bullish insider sentiment multiplier when confirmed insider buys exist
    conviction_multiplier = 1.5 if insider_buys else 1.0

    # Evaluate the top 10 positions only
    for position in analyzed_portfolio[:10]:
        trade_action = position.get("Trade_Action", "")
        stock = position.get("Stock", "UNKNOWN")
        weight = position.get("Weight_%", 0.0)

        # Signal fires when institutional action is bullish AND insider buying exists
        if ("BUY" in trade_action or "ADDED" in trade_action) and insider_buys:
            conviction_score = round(weight * conviction_multiplier, 4)
            quant_signals.append({
                "Stock": stock,
                "13F_Action": trade_action,
                "Form4_Action": "LIVE INSIDER BUY",
                "Algorithm_Signal": "STRONG BUY",
                "Conviction_Score": conviction_score
            })

    print(f"Signal generation complete. {len(quant_signals)} STRONG BUY signal(s) identified.")
    return {"quant_signals": quant_signals}


# ---------------------------------------------------------------------------
# AGENT 5: Institutional Crowding — Market-Neutral Strategy
# ---------------------------------------------------------------------------

def institutional_crowding_agent(master_signals: list) -> list:
    """
    Scans the aggregated master ledger for herd behaviour across funds.
    - 3+ funds in the same stock  → CROWDED - SHORT (fade the crowd)
    - Exactly 1 fund in the stock → HIDDEN GEM - LONG (contrarian opportunity)
    Returns a list of crowding signals sorted by Fund_Count descending.
    """
    # Count how many funds are accumulating each stock
    stock_counts = {}
    for signal in master_signals:
        stock = signal.get("Stock", "UNKNOWN")
        if stock in stock_counts:
            stock_counts[stock] += 1
        else:
            stock_counts[stock] = 1

    crowding_signals = []

    for stock, count in stock_counts.items():
        if count >= 3:
            crowding_signals.append({
                "Stock": stock,
                "Fund_Count": count,
                "Strategy_Action": "CROWDED - SHORT 🔴"
            })
        elif count == 1:
            crowding_signals.append({
                "Stock": stock,
                "Fund_Count": count,
                "Strategy_Action": "HIDDEN GEM - LONG 🟢"
            })

    crowding_signals = sorted(crowding_signals, key=lambda x: x["Fund_Count"], reverse=True)
    return crowding_signals


# ---------------------------------------------------------------------------
# AGENT 6: Activist Catalyst — Event-Driven Signal
# ---------------------------------------------------------------------------

def activist_catalyst_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 6: ACTIVIST CATALYST] Scanning for Event-Driven Catalysts ---")

    quant_signals = list(state.get("quant_signals", []))
    schedule_13d_data = state.get("schedule_13d_data", [])

    if schedule_13d_data:
        target_asset = state.get("target_asset", "UNKNOWN")
        quant_signals.append({
            "Stock": target_asset,
            "13F_Action": "EVENT DRIVEN",
            "Form4_Action": "HOSTILE 13D FILED",
            "Algorithm_Signal": "VOLATILITY BUY",
            "Conviction_Score": 9.5
        })
        print(f"  -> Activist catalyst detected for {target_asset}. VOLATILITY BUY signal appended.")
    else:
        print("  -> No activist catalyst detected.")

    return {"quant_signals": quant_signals}


# ---------------------------------------------------------------------------
# AGENT 7: Opportunistic Drift — Insider Delay Detection
# ---------------------------------------------------------------------------

def opportunistic_drift_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 7: OPPORTUNISTIC DRIFT] Scanning for Insider Delay Pattern ---")

    quant_signals = list(state.get("quant_signals", []))
    form_144_data = state.get("form_144_data", [])
    form_4_data = state.get("form_4_data", [])

    # Signal fires when an executive filed intent to sell (Form 144) but has
    # NOT yet executed the trade (Form 4 is empty) — classic price-pump delay
    if form_144_data and not form_4_data:
        target_asset = state.get("target_asset", "UNKNOWN")
        quant_signals.append({
            "Stock": target_asset,
            "13F_Action": "EVENT DRIVEN",
            "Form4_Action": "144 DELAY DETECTED",
            "Algorithm_Signal": "OPPORTUNISTIC SHORT",
            "Conviction_Score": 8.0
        })
        print(f"  -> 144 delay pattern detected for {target_asset}. OPPORTUNISTIC SHORT signal appended.")
    else:
        print("  -> No insider delay pattern detected.")

    return {"quant_signals": quant_signals}


# ---------------------------------------------------------------------------
# AGENT 8: Macro-Regime Filter — Yield Curve Risk Overlay
# ---------------------------------------------------------------------------

def macro_regime_agent(state: PortfolioState) -> Dict[str, Any]:
    print("\n--- [AGENT 8: MACRO-REGIME FILTER] Checking Live Treasury Yield Curve ---")

    regime = fetch_macro_yields()
    quant_signals = list(state.get("quant_signals", []))

    print(f"  -> Macro Regime Detected: {regime}")

    if regime == "INVERTED_YIELD_CURVE" and quant_signals:
        print("  -> ⚠️  Yield curve inverted. Overriding all long signals with MACRO WARNING.")
        for signal in quant_signals:
            signal["Algorithm_Signal"] = "MACRO WARNING ⚠️ - AVOID LONG"

    return {"macro_regime": regime, "quant_signals": quant_signals}
