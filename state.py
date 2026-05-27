from typing import TypedDict, Dict, Any, List


# Shared "digital clipboard" passed between all agents in the pipeline
class PortfolioState(TypedDict):
    target_asset: str           # The stock ticker (e.g., 'AAPL')
    cik: str
    company_name: str
    raw_13f_data: dict          # Raw JSON from SEC EDGAR submissions endpoint
    form_4_data: list           # Insider trading data
    form_144_data: list         # Intent-to-sell data
    schedule_13d_data: list     # Activist catalyst data
    error_message: str
    thirteen_f_urls: List[str]
    analyzed_portfolio: list
    quant_signals: list
    macro_regime: str           # Yield curve regime: NORMAL or INVERTED_YIELD_CURVE
    # Pre-built portfolio cache (populated in main.py before graph invocation)
    current_portfolio: dict     # {stock_name: {Stock, Value_($1000s), Shares}}
    previous_portfolio: dict    # Same shape, one quarter older
    current_total: float        # Total portfolio value in $1000s
