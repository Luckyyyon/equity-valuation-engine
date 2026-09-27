import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
import numpy as np

def export_dcf_model_to_excel(ticker: str, projections_df: pd.DataFrame, wacc_data: dict, dcf_results: dict, sens_df: pd.DataFrame, file_path: str):
    """
    Exports institutional-grade, formula-linked .xlsx model using openpyxl.
    - Blue font (#0000FF) for assumptions/hardcodes
    - Black font (#000000) for formulas
    - Light grey header fills (#F2F2F2)
    - Double underline borders for net total rows
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DCF Valuation Model"
    ws.views.sheetView[0].showGridLines = True
    
    # Styles
    title_font = Font(name="Calibri", size=16, bold=True, color="1F497D")
    section_font = Font(name="Calibri", size=12, bold=True, color="1F497D")
    header_font = Font(name="Calibri", size=11, bold=True, color="000000")
    hardcode_font = Font(name="Calibri", size=11, bold=False, color="0000FF")
    formula_font = Font(name="Calibri", size=11, bold=False, color="000000")
    bold_formula_font = Font(name="Calibri", size=11, bold=True, color="000000")
    
    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    
    thin_border_side = Side(style='thin', color='D9D9D9')
    thick_bottom_side = Side(style='double', color='000000')
    top_thin_side = Side(style='thin', color='000000')
    
    border_standard = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    border_summary_total = Border(top=top_thin_side, bottom=thick_bottom_side)
    
    # Title
    ws["B2"] = f"DISCOUNTED CASH FLOW VALUATION MODEL: {ticker.upper()}"
    ws["B2"].font = title_font
    
    # Section 1: Valuation Assumptions
    ws["B4"] = "1. Key Assumptions & WACC Parameters"
    ws["B4"].font = section_font
    
    assumptions = [
        ("Risk-Free Rate (10Y Yield)", wacc_data["risk_free_rate"], "0.00%"),
        ("Beta", wacc_data["beta"], "0.00"),
        ("Equity Risk Premium", wacc_data["equity_risk_premium"], "0.00%"),
        ("Cost of Equity (Re)", "=C5+C6*C7", "0.00%"),
        ("Cost of Debt (Rd)", wacc_data["cost_of_debt"], "0.00%"),
        ("Effective Tax Rate", 0.21, "0.00%"),
        ("Weight of Equity (E/V)", wacc_data["weight_equity"], "0.00%"),
        ("Weight of Debt (D/V)", wacc_data["weight_debt"], "0.00%"),
        ("Calculated WACC", "=(C11*C8)+(C12*C9*(1-C10))", "0.00%"),
        ("Terminal Growth Rate", 0.025, "0.00%"),
        ("Shares Outstanding (M)", wacc_data["shares_outstanding"] / 1e6, "#,##0.00"),
        ("Total Debt ($M)", wacc_data["total_debt"] / 1e6, "$#,##0.00"),
        ("Cash & Equivalents ($M)", wacc_data["cash"] / 1e6, "$#,##0.00")
    ]
    
    for idx, (label, val, fmt) in enumerate(assumptions, start=5):
        ws[f"B{idx}"] = label
        ws[f"B{idx}"].font = header_font
        cell = ws[f"C{idx}"]
        cell.number_format = fmt
        
        if str(val).startswith("="):
            cell.value = val
            cell.font = formula_font
        else:
            cell.value = val
            cell.font = hardcode_font
            
    # Section 2: Financial Projections
    ws["B20"] = "2. 5-Year Unlevered Free Cash Flow Projections ($M)"
    ws["B20"].font = section_font
    
    headers = ["Metric ($M)", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5"]
    for col_num, h in enumerate(headers, start=2):
        col_letter = get_column_letter(col_num)
        cell = ws[f"{col_letter}21"]
        cell.value = h
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center" if col_num > 2 else "left")
        
    proj_metrics = [
        ("Revenue", projections_df["Revenue"].values / 1e6),
        ("EBITDA", projections_df["EBITDA"].values / 1e6),
        ("Less: D&A", projections_df["D&A"].values / 1e6),
        ("EBIT", None), # formula
        ("Less: Tax on EBIT", None), # formula
        ("Plus: D&A", None), # formula
        ("Less: CapEx", projections_df["CapEx"].values / 1e6),
        ("Less: Change in NWC", projections_df["NWC_Change"].values / 1e6),
        ("Unlevered Free Cash Flow (UFCF)", None) # formula
    ]
    
    start_row = 22
    for r_idx, (metric_name, vals) in enumerate(proj_metrics):
        row = start_row + r_idx
        ws[f"B{row}"] = metric_name
        ws[f"B{row}"].font = bold_formula_font if "UFCF" in metric_name or metric_name == "Revenue" else header_font
        
        for c_idx in range(5):
            col_letter = get_column_letter(3 + c_idx)
            cell = ws[f"{col_letter}{row}"]
            cell.number_format = "$#,##0.00"
            
            if metric_name == "Revenue":
                cell.value = vals[c_idx]
                cell.font = hardcode_font
            elif metric_name == "EBITDA":
                cell.value = vals[c_idx]
                cell.font = hardcode_font
            elif metric_name == "Less: D&A":
                cell.value = vals[c_idx]
                cell.font = hardcode_font
            elif metric_name == "EBIT":
                cell.value = f"={col_letter}23-{col_letter}24"
                cell.font = formula_font
            elif metric_name == "Less: Tax on EBIT":
                cell.value = f"={col_letter}25*$C$10"
                cell.font = formula_font
            elif metric_name == "Plus: D&A":
                cell.value = f"={col_letter}24"
                cell.font = formula_font
            elif metric_name == "Less: CapEx":
                cell.value = vals[c_idx]
                cell.font = hardcode_font
            elif metric_name == "Less: Change in NWC":
                cell.value = vals[c_idx]
                cell.font = hardcode_font
            elif metric_name == "Unlevered Free Cash Flow (UFCF)":
                cell.value = f"={col_letter}25-{col_letter}26+{col_letter}27-{col_letter}28-{col_letter}29"
                cell.font = bold_formula_font
                cell.border = border_summary_total

    # Section 3: Valuation Outputs (Gordon Growth Method)
    ws["B33"] = "3. DCF Valuation Summary (Gordon Growth Terminal Value)"
    ws["B33"].font = section_font
    
    val_summary = [
        ("PV of 5-Year Explicit Cash Flows ($M)", "=SUM(C30:G30)", "$#,##0.00"),
        ("Terminal Year UFCF ($M)", "=G30*(1+C14)", "$#,##0.00"),
        ("Terminal Value ($M)", "=C36/(C13-C14)", "$#,##0.00"),
        ("PV of Terminal Value ($M)", "=C37/((1+C13)^5)", "$#,##0.00"),
        ("Enterprise Value ($M)", "=C35+C38", "$#,##0.00"),
        ("Less: Total Debt ($M)", "=C16", "$#,##0.00"),
        ("Plus: Cash & Equivalents ($M)", "=C17", "$#,##0.00"),
        ("Implied Equity Value ($M)", "=C39-C40+C41", "$#,##0.00"),
        ("Diluted Shares Outstanding (M)", "=C15", "#,##0.00"),
        ("Implied Target Price per Share ($)", "=C42/C43", "$#,##0.00")
    ]
    
    for idx, (label, formula, fmt) in enumerate(val_summary, start=35):
        ws[f"B{idx}"] = label
        ws[f"B{idx}"].font = bold_formula_font if "Implied Target Price" in label else header_font
        cell = ws[f"C{idx}"]
        cell.value = formula
        cell.font = bold_formula_font if "Implied Target Price" in label else formula_font
        cell.number_format = fmt
        if "Implied Target Price" in label:
            cell.border = border_summary_total
            
    # Section 4: 2-Way Sensitivity Matrix
    ws["B47"] = "4. Two-Way Sensitivity Analysis: Implied Target Price ($)"
    ws["B47"].font = section_font
    
    # Headers
    ws["B49"] = "WACC \\ Growth"
    ws["B49"].font = header_font
    ws["B49"].fill = header_fill
    
    for col_idx, col_val in enumerate(sens_df.columns, start=3):
        col_letter = get_column_letter(col_idx)
        cell = ws[f"{col_letter}49"]
        cell.value = col_val
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
        
    for row_idx, row_label in enumerate(sens_df.index, start=50):
        cell_lbl = ws[f"B{row_idx}"]
        cell_lbl.value = row_label
        cell_lbl.font = header_font
        cell_lbl.fill = header_fill
        
        for col_idx, col_val in enumerate(sens_df.columns, start=3):
            col_letter = get_column_letter(col_idx)
            cell = ws[f"{col_letter}{row_idx}"]
            val = sens_df.loc[row_label, col_val]
            cell.value = val
            cell.font = formula_font
            cell.number_format = "$#,##0.00"
            cell.border = border_standard

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 14)
        
    wb.save(file_path)
