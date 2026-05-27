import random
import requests
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# STREAM B: Insider Trading & Intent-to-Sell (Mock Data)
# ---------------------------------------------------------------------------

def fetch_form4_data(ticker: str) -> list:
    print(f"  -> [Stream B] Fetching Form 4 (Insider) data for {ticker}...")
    try:
        url = f"http://openinsider.com/search?q={ticker}"
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find('table', {'class': 'tinytable'})
        if not table:
            return []
        rows = table.find('tbody').find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 8:
                trade_type = cols[7].text.strip()
                if "P - Purchase" in trade_type:
                    return [{
                        "Date": cols[1].text.strip(),
                        "Executive": cols[4].text.strip(),
                        "Action": "BUY",
                        "Shares": cols[9].text.strip()
                    }]
        return []
    except Exception:
        return []


def fetch_form144_data(ticker: str) -> list:
    print(f"  -> [Stream B] Fetching Form 144 (Intent to Sell) data for {ticker}...")
    # 20% chance to simulate an executive filing intent to sell
    if random.random() > 0.8:
        return [{"Date": "2026-05-15", "Executive": "Jane Doe", "Shares_Proposed": 50000}]
    return []


# ---------------------------------------------------------------------------
# STREAM C: Activist Catalysts (Mock Data)
# ---------------------------------------------------------------------------

def fetch_schedule_13d(ticker: str) -> list:
    print(f"  -> [Stream C] Fetching Schedule 13D (Activist) data for {ticker}...")
    # 10% chance to simulate a hostile takeover catalyst
    if random.random() > 0.9:
        return [{"Activist": "Elliott Management", "Ownership_%": 5.2, "Purpose": "Hostile Takeover / Board Restructuring"}]
    return []


# ---------------------------------------------------------------------------
# XML / BeautifulSoup Extraction Helper
# ---------------------------------------------------------------------------

def extract_portfolio_from_xml(xml_url: str) -> list:
    """
    Given a primary-document URL from SEC EDGAR, locate the information-table
    XML file in the same directory and parse all <infoTable> holdings from it.
    Returns a list of dicts: {Stock, Value_($1000s), Shares}
    """
    # 1. Isolate the base SEC directory URL
    parts = xml_url.split('/')
    base_dir_url = '/'.join(parts[:8])

    # 2. Query the SEC's directory index to find the exact filename
    index_json_url = f"{base_dir_url}/index.json"

    print(f"\n--- [DATA EXTRACTION] Scanning SEC Directory Index ---")
    print(f"Index URL: {index_json_url}")

    headers = {
        "User-Agent": "TechMahindra_Intern_Project your.email@techmahindra.com"
    }

    try:
        index_response = requests.get(index_json_url, headers=headers)
        if index_response.status_code != 200:
            print("Failed to load directory index.")
            return []

        index_data = index_response.json()
        info_table_filename = None

        # Loop through all files in this SEC folder
        for item in index_data.get('directory', {}).get('item', []):
            filename = item.get('name', '')
            # The information table is an XML file, but never primary_doc.xml
            if filename.endswith('.xml') and filename != 'primary_doc.xml':
                info_table_filename = filename
                break

        if not info_table_filename:
            print("Could not find the Information Table XML in the directory.")
            return []

        # 3. Construct the verified URL for the Information Table
        info_table_url = f"{base_dir_url}/{info_table_filename}"
        print(f"Targeting Exact Match: {info_table_url}")

        # 4. Download and parse the portfolio data
        response = requests.get(info_table_url, headers=headers)

        # Use 'html.parser' to strip SEC namespaces cleanly
        soup = BeautifulSoup(response.content, 'html.parser')
        holdings = []

        for info in soup.find_all('infotable'):
            issuer_tag = info.find('nameofissuer')
            issuer = issuer_tag.text.strip() if issuer_tag else 'UNKNOWN'

            value_tag = info.find('value')
            value_in_thousands = int(value_tag.text.strip()) if value_tag else 0

            shares_tag = info.find('sshprnamt')
            shares = int(shares_tag.text.strip()) if shares_tag else 0

            holdings.append({
                "Stock": issuer,
                "Value_($1000s)": value_in_thousands,
                "Shares": shares
            })

        holdings = sorted(holdings, key=lambda x: x['Value_($1000s)'], reverse=True)
        return holdings

    except Exception as e:
        print(f"Failed to parse XML: {str(e)}")
        return []


# ---------------------------------------------------------------------------
# MACRO DATA: Live US Treasury Yield Curve
# ---------------------------------------------------------------------------

def fetch_macro_yields() -> str:
    """
    Fetches live 10-Year (^TNX) and 5-Year (^FVX) US Treasury yields from Yahoo Finance.
    Returns "INVERTED_YIELD_CURVE" if the 5Y yield exceeds the 10Y yield, else "NORMAL".
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res_10y = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5ETNX", headers=headers, timeout=10)
        yield_10y = res_10y.json()['chart']['result'][0]['meta']['regularMarketPrice']
        res_5y = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EFVX", headers=headers, timeout=10)
        yield_5y = res_5y.json()['chart']['result'][0]['meta']['regularMarketPrice']
        if yield_5y > yield_10y:
            return "INVERTED_YIELD_CURVE"
        return "NORMAL"
    except Exception:
        return "NORMAL"
