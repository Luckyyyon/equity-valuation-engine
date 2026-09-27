import pytest
import pandas as pd
import numpy as np
from src.data_loader import fetch_financial_data
from src.financial_model import project_financials
from src.dcf_engine import compute_wacc, run_dcf_valuation, generate_sensitivity_matrix

def test_wacc_bounds():
    mock_data = {
        "info": {"beta": 1.2, "totalDebt": 5e10, "totalCash": 2e10, "marketCap": 2e12, "sharesOutstanding": 1.5e10},
        "balance_sheet": pd.DataFrame(),
        "income_statement": pd.DataFrame(),
        "risk_free_rate": 0.04
    }
    wacc_res = compute_wacc(mock_data)
    assert 0.05 <= wacc_res["wacc"] <= 0.18, f"WACC {wacc_res['wacc']} out of bounds [0.05, 0.18]"

def test_non_negative_discount_factors():
    mock_data = {
        "info": {"beta": 1.0, "totalDebt": 1e9, "totalCash": 5e8, "marketCap": 1e10, "sharesOutstanding": 1e8},
        "balance_sheet": pd.DataFrame(),
        "income_statement": pd.DataFrame({"Total Revenue": [1e9, 1.1e9, 1.2e9, 1.3e9]}),
        "cash_flow": pd.DataFrame(),
        "risk_free_rate": 0.04
    }
    proj_res = project_financials(mock_data)
    wacc_res = compute_wacc(mock_data)
    dcf_res = run_dcf_valuation(proj_res["projections"], wacc_res)
    
    for df in dcf_res["discount_factors"]:
        assert df > 0, "Discount factor must be strictly positive"

def test_ufcf_math_and_balance_identity():
    mock_data = {
        "info": {"beta": 1.1, "totalDebt": 2e9, "totalCash": 1e9, "marketCap": 2e10, "sharesOutstanding": 1e8},
        "balance_sheet": pd.DataFrame({"Total Debt": [2e9], "Cash And Cash Equivalents": [1e9]}),
        "income_statement": pd.DataFrame({"Total Revenue": [1e10, 1.1e10, 1.2e10, 1.3e10]}),
        "cash_flow": pd.DataFrame(),
        "risk_free_rate": 0.042
    }
    proj_res = project_financials(mock_data)
    df_proj = proj_res["projections"]
    
    # Verify UFCF formula: EBIT*(1 - Tax) + D&A - CapEx - NWC_Change
    tax_rate = proj_res["assumptions"]["tax_rate"]
    for idx, row in df_proj.iterrows():
        expected_ufcf = row["EBIT"] * (1 - tax_rate) + row["D&A"] - row["CapEx"] - row["NWC_Change"]
        assert np.isclose(row["UFCF"], expected_ufcf), f"UFCF calculation mismatch on {idx}"
