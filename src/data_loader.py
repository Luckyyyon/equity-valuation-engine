import yfinance as yf
import pandas as pd
import numpy as np
import requests

def fetch_financial_data(ticker_symbol: str):
    """
    Pulls 3-statement data, info, and risk-free rate for a ticker.
    """
    ticker = yf.Ticker(ticker_symbol)
    
    # Financial statements
    inc_stmt = ticker.financials
    bal_sheet = ticker.balance_sheet
    cash_flow = ticker.cashflow
    info = ticker.info or {}
    
    # Risk-free rate fallback / fetch (10-Yr Treasury yield via ^TNX)
    try:
        tnx = yf.Ticker("^TNX")
        rf_history = tnx.history(period="5d")
        if not rf_history.empty:
            risk_free_rate = float(rf_history["Close"].iloc[-1]) / 100.0
        else:
            risk_free_rate = 0.042  # default 4.2%
    except Exception:
        risk_free_rate = 0.042

    return {
        "ticker": ticker_symbol.upper(),
        "income_statement": inc_stmt,
        "balance_sheet": bal_sheet,
        "cash_flow": cash_flow,
        "info": info,
        "risk_free_rate": risk_free_rate
    }
