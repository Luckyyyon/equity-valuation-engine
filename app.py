import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

from src.data_loader import fetch_financial_data
from src.financial_model import project_financials
from src.dcf_engine import compute_wacc, run_dcf_valuation, generate_sensitivity_matrix
from src.comps_engine import fetch_peer_comps
from src.excel_exporter import export_dcf_model_to_excel

st.set_page_config(page_title="Equity Valuation Engine", layout="wide", page_icon="📈")

# Load Apple-inspired custom design
css_path = os.path.join(os.path.dirname(__file__), "assets", "style.css")
if os.path.exists(css_path):
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Header Section
st.title("Institutional Equity Valuation Engine")
st.markdown("<p style='color: #86868B; font-size: 1.1rem; margin-bottom: 2rem;'>Automated 5-Year DCF model, rolling CAPM WACC, 2-way sensitivity matrix, and formula-linked Excel exporter.</p>", unsafe_allow_html=True)

# Sidebar Controls
st.sidebar.header("Valuation Controls")
ticker_input = st.sidebar.text_input("Ticker Symbol", value="AAPL").upper().strip()
peer_input = st.sidebar.text_input("Peer Tickers (comma separated)", value="MSFT, GOOGL, NVDA, AMZN")
peer_list = [p.strip().upper() for p in peer_input.split(",") if p.strip()]

st.sidebar.subheader("Model Assumptions")
custom_rev_growth = st.sidebar.slider("Revenue Growth Rate (%)", min_value=-0.10, max_value=0.50, value=0.08, step=0.01)
custom_ebitda_margin = st.sidebar.slider("EBITDA Margin (%)", min_value=0.05, max_value=0.60, value=0.30, step=0.01)
terminal_growth_rate = st.sidebar.slider("Terminal Growth Rate (%)", min_value=0.005, max_value=0.05, value=0.025, step=0.0025)
equity_risk_premium = st.sidebar.slider("Equity Risk Premium (%)", min_value=0.03, max_value=0.08, value=0.055, step=0.005)

if st.sidebar.button("Run Valuation", type="primary") or "data" not in st.session_state:
    with st.spinner(f"Fetching financial data for {ticker_input}..."):
        try:
            data = fetch_financial_data(ticker_input)
            st.session_state["data"] = data
            st.session_state["ticker"] = ticker_input
        except Exception as e:
            st.error(f"Failed to fetch data for {ticker_input}: {e}")
            st.stop()

data = st.session_state.get("data")
ticker_symbol = st.session_state.get("ticker", ticker_input)

if data:
    # Run Calculations
    proj_res = project_financials(data, custom_rev_growth=custom_rev_growth, custom_ebitda_margin=custom_ebitda_margin)
    wacc_data = compute_wacc(data, equity_risk_premium=equity_risk_premium)
    dcf_res = run_dcf_valuation(proj_res["projections"], wacc_data, terminal_growth_rate=terminal_growth_rate)
    sens_df = generate_sensitivity_matrix(proj_res["projections"], wacc_data, base_growth=terminal_growth_rate)
    
    info = data.get("info", {})
    current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0.0
    gordon_target = dcf_res["gordon"]["target_price"]
    exit_target = dcf_res["exit_multiple"]["target_price"]
    
    # Top KPI Metrics
    st.subheader(f"Valuation Summary: {ticker_symbol}")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Current Market Price", f"${current_price:.2f}")
    col2.metric("DCF Target (Gordon)", f"${gordon_target:.2f}", delta=f"{((gordon_target/current_price)-1)*100:.1f}%" if current_price else "N/A")
    col3.metric("DCF Target (Exit Mult)", f"${exit_target:.2f}", delta=f"{((exit_target/current_price)-1)*100:.1f}%" if current_price else "N/A")
    col4.metric("Calculated WACC", f"{wacc_data['wacc']*100:.2f}%")
    col5.metric("Cost of Equity (Re)", f"{wacc_data['cost_of_equity']*100:.2f}%")

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs Layout
    tab1, tab2, tab3, tab4 = st.tabs(["Valuation Range", "5-Year DCF Projections", "2-Way Sensitivity", "Peer Multiples"])
    
    with tab1:
        st.subheader("Valuation Range (Football Field)")
        
        high_52 = info.get("fiftyTwoWeekHigh", current_price * 1.2)
        low_52 = info.get("fiftyTwoWeekLow", current_price * 0.8)
        
        dcf_low = min(gordon_target, exit_target) * 0.95
        dcf_high = max(gordon_target, exit_target) * 1.05
        
        categories = ["52-Week Range", "DCF Range", "Current Price"]
        lows = [low_52, dcf_low, current_price]
        highs = [high_52, dcf_high, current_price]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=categories,
            x=[h - l for l, h in zip(lows, highs)],
            base=lows,
            orientation='h',
            marker_color=['#86868B', '#0066CC', '#1D1D1F'],
            opacity=0.9
        ))
        fig.update_layout(
            xaxis_title="Price ($)",
            template="plotly_white",
            height=320,
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#1D1D1F"),
            margin=dict(l=20, r=20, t=20, b=40),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF"
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        st.subheader("5-Year Unlevered Free Cash Flow Projections ($M)")
        df_display = proj_res["projections"].copy() / 1e6
        st.dataframe(df_display.style.format("${:,.2f}"), use_container_width=True)
        
        st.subheader("CAPM WACC Structure")
        col_a, col_b = st.columns(2)
        with col_a:
            st.json({
                "Risk-Free Rate (Rf)": f"{wacc_data['risk_free_rate']*100:.2f}%",
                "Beta": f"{wacc_data['beta']:.2f}",
                "Equity Risk Premium": f"{wacc_data['equity_risk_premium']*100:.2f}%",
                "Cost of Equity (Re)": f"{wacc_data['cost_of_equity']*100:.2f}%"
            })
        with col_b:
            st.json({
                "Cost of Debt (Rd)": f"{wacc_data['cost_of_debt']*100:.2f}%",
                "Weight of Equity (E/V)": f"{wacc_data['weight_equity']*100:.2f}%",
                "Weight of Debt (D/V)": f"{wacc_data['weight_debt']*100:.2f}%",
                "Computed WACC": f"{wacc_data['wacc']*100:.2f}%"
            })

    with tab3:
        st.subheader("2-Way Target Price Sensitivity (WACC vs. Terminal Growth Rate)")
        fig_heat = px.imshow(
            sens_df,
            labels=dict(x="Terminal Growth Rate", y="WACC", color="Target Price ($)"),
            text_auto=".2f",
            color_continuous_scale="Blues"
        )
        fig_heat.update_layout(
            font=dict(family="Plus Jakarta Sans, sans-serif", color="#1D1D1F"),
            plot_bgcolor="#FFFFFF",
            paper_bgcolor="#FFFFFF"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        st.dataframe(sens_df.style.format("${:,.2f}"), use_container_width=True)

    with tab4:
        st.subheader("Peer Trading Multiples Comparison")
        if peer_list:
            with st.spinner("Fetching peer metrics..."):
                df_comps = fetch_peer_comps([ticker_symbol] + peer_list)
                st.dataframe(df_comps.style.format({
                    "Price": "${:,.2f}",
                    "Market Cap": "${:,.0f}",
                    "P/E": "{:,.2f}",
                    "EV/EBITDA": "{:,.2f}",
                    "PEG": "{:,.2f}"
                }), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Export Financial Model")
    
    excel_path = f"{ticker_symbol}_DCF_Model.xlsx"
    export_dcf_model_to_excel(ticker_symbol, proj_res["projections"], wacc_data, dcf_res, sens_df, excel_path)
    
    with open(excel_path, "rb") as f:
        st.download_button(
            label=f"Download Formula-Linked Model ({ticker_symbol}_DCF_Model.xlsx)",
            data=f,
            file_name=excel_path,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

# Footer
st.markdown("""
<div class="footer-text">
  <span>Institutional Equity Valuation Engine</span>
</div>
""", unsafe_allow_html=True)

