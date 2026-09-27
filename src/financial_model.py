import pandas as pd
import numpy as np

def project_financials(data: dict, forecast_years: int = 5, custom_rev_growth: float = None, custom_ebitda_margin: float = None):
    """
    Projects revenue, EBITDA, D&A, CapEx, NWC changes, and Tax Rate for 5 forward years based on historical averages.
    """
    inc = data["income_statement"]
    cash = data["cash_flow"]
    bal = data["balance_sheet"]
    
    # Historical revenue & growth
    rev_hist = inc.loc["Total Revenue"] if "Total Revenue" in inc.index else inc.iloc[0]
    rev_hist = rev_hist.sort_index(ascending=True)
    
    latest_rev = rev_hist.iloc[-1]
    rev_growth_rates = rev_hist.pct_change().dropna()
    avg_rev_growth = float(rev_growth_rates.mean()) if len(rev_growth_rates) > 0 else 0.05
    if custom_rev_growth is not None:
        avg_rev_growth = custom_rev_growth
        
    # EBITDA margin
    if "EBITDA" in inc.index:
        ebitda_hist = inc.loc["EBITDA"].sort_index(ascending=True)
    elif "Operating Income" in inc.index:
        ebitda_hist = inc.loc["Operating Income"].sort_index(ascending=True)
    else:
        ebitda_hist = rev_hist * 0.20
        
    ebitda_margins = (ebitda_hist / rev_hist).dropna()
    avg_ebitda_margin = float(ebitda_margins.mean()) if len(ebitda_margins) > 0 else 0.20
    if custom_ebitda_margin is not None:
        avg_ebitda_margin = custom_ebitda_margin

    # D&A % Revenue
    if not cash.empty and "Operating Cash Flow" in cash.index:
        da_hist = cash.loc["Operating Cash Flow"] * 0.05
    else:
        da_hist = rev_hist * 0.04
        
    if not cash.empty:
        for da_name in ["Reconciled Depreciation", "Depreciation And Amortization", "Depreciation & Amortization"]:
            if da_name in cash.index:
                da_hist = cash.loc[da_name].sort_index(ascending=True)
                break
    da_ratio = float((da_hist / rev_hist).dropna().mean()) if len((da_hist / rev_hist).dropna()) > 0 else 0.04
    
    # CapEx % Revenue
    capex_hist = rev_hist * 0.04
    if not cash.empty:
        for capex_name in ["Capital Expenditure", "Capital Expenditures"]:
            if capex_name in cash.index:
                capex_hist = cash.loc[capex_name].abs().sort_index(ascending=True)
                break
    capex_ratio = float((capex_hist / rev_hist).dropna().mean()) if len((capex_hist / rev_hist).dropna()) > 0 else 0.04

    # Effective Tax Rate
    tax_rate = 0.21
    if "Tax Provision" in inc.index and "Pretax Income" in inc.index:
        tax = inc.loc["Tax Provision"].sort_index(ascending=True)
        ebt = inc.loc["Pretax Income"].sort_index(ascending=True)
        tax_rates = (tax / ebt).dropna()
        valid_rates = tax_rates[(tax_rates > 0) & (tax_rates < 0.5)]
        if len(valid_rates) > 0:
            tax_rate = float(valid_rates.mean())
            
    # Projections
    years = [f"Year {i}" for i in range(1, forecast_years + 1)]
    projected_rev = []
    curr_rev = latest_rev
    for _ in range(forecast_years):
        curr_rev *= (1 + avg_rev_growth)
        projected_rev.append(curr_rev)
        
    projected_ebitda = [r * avg_ebitda_margin for r in projected_rev]
    projected_da = [r * da_ratio for r in projected_rev]
    projected_ebit = [e - d for e, d in zip(projected_ebitda, projected_da)]
    projected_capex = [r * capex_ratio for r in projected_rev]
    # NWC change projected as 1.5% of incremental revenue
    projected_nwc_change = [ (projected_rev[i] - (latest_rev if i == 0 else projected_rev[i-1])) * 0.015 for i in range(forecast_years) ]
    
    projected_ufcf = [
        ebit * (1 - tax_rate) + da - capex - nwc
        for ebit, da, capex, nwc in zip(projected_ebit, projected_da, projected_capex, projected_nwc_change)
    ]
    
    df_proj = pd.DataFrame({
        "Revenue": projected_rev,
        "EBITDA": projected_ebitda,
        "D&A": projected_da,
        "EBIT": projected_ebit,
        "CapEx": projected_capex,
        "NWC_Change": projected_nwc_change,
        "UFCF": projected_ufcf
    }, index=years)
    
    return {
        "projections": df_proj,
        "assumptions": {
            "rev_growth": avg_rev_growth,
            "ebitda_margin": avg_ebitda_margin,
            "da_ratio": da_ratio,
            "capex_ratio": capex_ratio,
            "tax_rate": tax_rate,
            "latest_revenue": latest_rev
        }
    }
