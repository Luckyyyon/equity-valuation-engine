import yfinance as yf
import pandas as pd
import numpy as np

def fetch_peer_comps(peer_tickers: list):
    """
    Compares EV/EBITDA, P/E, PEG against custom peer tickers.
    """
    comps_data = []
    
    for ticker_symbol in peer_tickers:
        try:
            t = yf.Ticker(ticker_symbol)
            info = t.info or {}
            
            pe = info.get("trailingPE") or info.get("forwardPE") or np.nan
            ev_ebitda = info.get("enterpriseToEbitda") or np.nan
            peg = info.get("pegRatio") or np.nan
            price = info.get("currentPrice") or info.get("regularMarketPrice") or np.nan
            market_cap = info.get("marketCap") or np.nan
            
            comps_data.append({
                "Ticker": ticker_symbol.upper(),
                "Company": info.get("shortName", ticker_symbol),
                "Price": price,
                "Market Cap": market_cap,
                "P/E": pe,
                "EV/EBITDA": ev_ebitda,
                "PEG": peg
            })
        except Exception:
            continue
            
    df_comps = pd.DataFrame(comps_data)
    return df_comps
