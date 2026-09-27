import numpy as np
import pandas as pd

def compute_wacc(data: dict, equity_risk_premium: float = 0.055, custom_beta: float = None):
    """
    Computes WACC via CAPM: WACC = (E/V * Re) + (D/V * Rd * (1 - T))
    Ensures WACC is bounded reasonably between 5% and 18%.
    """
    info = data.get("info", {})
    bal = data.get("balance_sheet", pd.DataFrame())
    inc = data.get("income_statement", pd.DataFrame())
    
    # Risk-free rate
    rf = data.get("risk_free_rate", 0.042)
    
    # Beta
    beta = info.get("beta")
    if custom_beta is not None:
        beta = custom_beta
    elif beta is None or np.isnan(beta) or beta <= 0:
        beta = 1.0
        
    # Cost of Equity (Re)
    cost_of_equity = rf + (beta * equity_risk_premium)
    
    # Total Debt & Cash
    total_debt = info.get("totalDebt")
    if total_debt is None or np.isnan(total_debt):
        if not bal.empty and "Total Debt" in bal.index:
            total_debt = float(bal.loc["Total Debt"].iloc[0])
        else:
            total_debt = 0.0
            
    cash = info.get("totalCash")
    if cash is None or np.isnan(cash):
        if not bal.empty and "Cash And Cash Equivalents" in bal.index:
            cash = float(bal.loc["Cash And Cash Equivalents"].iloc[0])
        else:
            cash = 0.0
            
    market_cap = info.get("marketCap")
    if market_cap is None or np.isnan(market_cap) or market_cap <= 0:
        market_cap = 1e11 # default fallback
        
    # Cost of Debt (Rd) - estimated from Interest Expense / Total Debt or default 5%
    interest_expense = 0.0
    if not inc.empty and "Interest Expense" in inc.index:
        interest_expense = float(abs(inc.loc["Interest Expense"].iloc[0]))
        
    if total_debt > 0 and interest_expense > 0:
        cost_of_debt = interest_expense / total_debt
        cost_of_debt = min(max(cost_of_debt, 0.02), 0.12)
    else:
        cost_of_debt = 0.045
        
    # Effective tax rate
    tax_rate = 0.21
    if not inc.empty and "Tax Provision" in inc.index and "Pretax Income" in inc.index:
        tax = float(inc.loc["Tax Provision"].iloc[0])
        ebt = float(inc.loc["Pretax Income"].iloc[0])
        if ebt > 0 and 0 < tax < ebt:
            tax_rate = tax / ebt

    total_value = market_cap + total_debt
    weight_equity = market_cap / total_value
    weight_debt = total_debt / total_value
    
    wacc = (weight_equity * cost_of_equity) + (weight_debt * cost_of_debt * (1 - tax_rate))
    
    # Enforce WACC bounds between 5% and 18%
    wacc = max(0.05, min(0.18, wacc))
    
    return {
        "wacc": wacc,
        "cost_of_equity": cost_of_equity,
        "cost_of_debt": cost_of_debt,
        "weight_equity": weight_equity,
        "weight_debt": weight_debt,
        "risk_free_rate": rf,
        "beta": beta,
        "equity_risk_premium": equity_risk_premium,
        "total_debt": total_debt,
        "cash": cash,
        "market_cap": market_cap,
        "shares_outstanding": info.get("sharesOutstanding", 1e9)
    }

def run_dcf_valuation(projections_df: pd.DataFrame, wacc_data: dict, terminal_growth_rate: float = 0.025, exit_multiple: float = 12.0):
    """
    Computes Enterprise Value and Target Price using both Gordon Growth and Exit Multiple methods.
    """
    wacc = wacc_data["wacc"]
    ufcf_list = projections_df["UFCF"].tolist()
    n_years = len(ufcf_list)
    
    # Discount factors
    discount_factors = [(1 + wacc) ** (i + 1) for i in range(n_years)]
    pv_ufcf = [ufcf / df for ufcf, df in zip(ufcf_list, discount_factors)]
    pv_explicit_cf = sum(pv_ufcf)
    
    # 1. Gordon Growth Terminal Value
    terminal_ufcf = ufcf_list[-1] * (1 + terminal_growth_rate)
    if wacc <= terminal_growth_rate:
        wacc_adj = terminal_growth_rate + 0.01
    else:
        wacc_adj = wacc
    tv_gordon = terminal_ufcf / (wacc_adj - terminal_growth_rate)
    pv_tv_gordon = tv_gordon / discount_factors[-1]
    
    ev_gordon = pv_explicit_cf + pv_tv_gordon
    equity_val_gordon = ev_gordon - wacc_data["total_debt"] + wacc_data["cash"]
    shares = wacc_data["shares_outstanding"] if wacc_data["shares_outstanding"] else 1e9
    target_price_gordon = equity_val_gordon / shares
    
    # 2. Exit Multiple Terminal Value
    terminal_ebitda = projections_df["EBITDA"].iloc[-1]
    tv_exit = terminal_ebitda * exit_multiple
    pv_tv_exit = tv_exit / discount_factors[-1]
    
    ev_exit = pv_explicit_cf + pv_tv_exit
    equity_val_exit = ev_exit - wacc_data["total_debt"] + wacc_data["cash"]
    target_price_exit = equity_val_exit / shares
    
    return {
        "pv_explicit_cf": pv_explicit_cf,
        "discount_factors": discount_factors,
        "pv_ufcf": pv_ufcf,
        "gordon": {
            "terminal_value": tv_gordon,
            "pv_terminal_value": pv_tv_gordon,
            "enterprise_value": ev_gordon,
            "equity_value": equity_val_gordon,
            "target_price": target_price_gordon
        },
        "exit_multiple": {
            "terminal_value": tv_exit,
            "pv_terminal_value": pv_tv_exit,
            "enterprise_value": ev_exit,
            "equity_value": equity_val_exit,
            "target_price": target_price_exit
        }
    }

def generate_sensitivity_matrix(projections_df: pd.DataFrame, wacc_data: dict, base_growth: float = 0.025):
    """
    Generates a 5x5 sensitivity grid of Target Price across WACC (+/- 1.5%) vs. Terminal Growth Rate (+/- 0.75%).
    """
    base_wacc = wacc_data["wacc"]
    wacc_steps = [base_wacc - 0.015, base_wacc - 0.0075, base_wacc, base_wacc + 0.0075, base_wacc + 0.015]
    growth_steps = [base_growth - 0.0075, base_growth - 0.00375, base_growth, base_growth + 0.00375, base_growth + 0.0075]
    
    matrix = np.zeros((5, 5))
    
    for i, w in enumerate(wacc_steps):
        for j, g in enumerate(growth_steps):
            temp_wacc_data = wacc_data.copy()
            temp_wacc_data["wacc"] = w
            res = run_dcf_valuation(projections_df, temp_wacc_data, terminal_growth_rate=g)
            matrix[i, j] = res["gordon"]["target_price"]
            
    df_sens = pd.DataFrame(
        matrix,
        index=[f"{w*100:.2f}%" for w in wacc_steps],
        columns=[f"{g*100:.2f}%" for g in growth_steps]
    )
    df_sens.index.name = "WACC"
    df_sens.columns.name = "Terminal Growth"
    
    return df_sens
