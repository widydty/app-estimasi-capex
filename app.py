import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="NPK Optimization System", layout="wide", page_icon="🏭")

# CSS for Enterprise Dashboard Look
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        .stApp { background-color: #f3f4f6; font-family: 'Inter', sans-serif; color: #111827; }
        
        /* KPI Cards */
        .kpi-card {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e5e7eb;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
        .kpi-label { font-size: 12px; text-transform: uppercase; color: #6b7280; font-weight: 600; letter-spacing: 0.05em; }
        .kpi-value { font-size: 24px; font-weight: 700; color: #111827; margin-top: 5px; }
        .kpi-sub { font-size: 12px; color: #9ca3af; margin-top: 2px; }
        
        /* Tables */
        div[data-testid="stDataFrame"] { background: white; border-radius: 8px; padding: 10px; }
        
        /* Alerts */
        .alert-box { padding: 12px; border-radius: 6px; font-size: 14px; margin-bottom: 10px; border-left: 4px solid; }
        .alert-warn { background: #fffbeb; border-color: #f59e0b; color: #92400e; }
        .alert-error { background: #fef2f2; border-color: #ef4444; color: #b91c1c; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ENGINEERING DATABASE ---
# Compositions based on BEDP-04
# Prices are default placeholders (User can edit)
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Urea",   "Price": 6500},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"H2O": 1.0, "Type": "Salt",   "Price": 2500},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "H2O": 1.5, "Type": "Salt",   "Price": 10500},
    "TSP (0-46)":   {"N": 0.0,  "P": 46.0,"K": 0.0, "S": 0.0, "H2O": 4.0, "Type": "Acidic", "Price": 9800},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "H2O": 0.5, "Type": "Salt",   "Price": 8200},
    "ZK (SOP)":     {"N": 0.0,  "P": 0.0, "K": 50.0,"S": 18.0,"H2O": 0.5, "Type": "Salt",   "Price": 12000},
    "Dolomite":     {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Filler", "Price": 300},
    "Clay":         {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 2.0, "Type": "Filler", "Price": 250}
}

# Design Guarantee Data (BEDP-02) for Benchmark
GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# Product Selling Price Assumption (Rp/kg) - For Margin Calc
PRODUCT_PRICE = 14000 

# --- 3. LOGIC ENGINE ---

def check_compatibility(selected_mats):
    """Engineering Safety Checks"""
    issues = []
    mats = set(selected_mats)
    
    # Rule 1: Urea vs TSP (Hygroscopicity & Water Release)
    if "Urea" in mats and "TSP (0-46)" in mats:
        issues.append("CRITICAL: Urea and TSP incompatibility. Mixture will become wet/sticky.")
        
    return issues

def calculate_optimization(tn, tp, tk, ts, selected_mats, prices):
    mats = list(selected_mats)
    n_vars = len(mats)
    total_mass = 1000.0 # Basis
    
    # Objective: Minimize Cost
    c = [prices[m] for m in mats]
    
    # Constraints
    A_ub = [] # Inequality
    b_ub = []
    
    # Nutrients (Target is Minimum) -> -Ax <= -b
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # Engineering Constraint: Limit Filler (Max 30% to maintain granule hardness)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0) # Max 300kg filler
        
    # Equality: Total Mass = 1000
    A_eq = [[1.0] * n_vars]
    b_eq = [total_mass]
    
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

# SIDEBAR
with st.sidebar:
    st.subheader("1. Grade Specification")
    grade_sel = st.selectbox("Select Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"])
    
    # Auto-fill based on selection
    if grade_sel == "15-15-15": def_n, def_p, def_k, def_s = 15.0, 15.0, 15.0, 2.0
    elif grade_sel == "15-10-12": def_n, def_p, def_k, def_s = 15.0, 10.0, 12.0, 2.0
    elif grade_sel == "16-16-16": def_n, def_p, def_k, def_s = 16.0, 16.0, 16.0, 0.0
    else: def_n, def_p, def_k, def_s = 15.0, 15.0, 15.0, 0.0
    
    c1, c2 = st.columns(2)
    tn = c1.number_input("N %", value=def_n)
    tp = c2.number_input("P2O5 %", value=def_p)
    tk = c1.number_input("K2O %", value=def_k)
    ts = c2.number_input("S %", value=def_s)
    
    st.subheader("2. Raw Material Prices (IDR/kg)")
    st.caption("Adjust to current market rates")
    
    current_prices = {}
    for m, data in RAW_MATS.items():
        current_prices[m] = st.number_input(f"{m}", value=data["Price"], step=100)
        
    st.subheader("3. Inventory Control")
    active_mats = st.multiselect("Available Materials", list(RAW_MATS.keys()), default=["Urea", "ZA (AmSulf)", "DAP (16-45)", "KCl (MOP)", "Clay"])

    run_calc = st.button("RUN OPTIMIZATION", type="primary", use_container_width=True)

# MAIN AREA
st.title("NPK Production Optimization System")
st.markdown(f"**Target Formulation:** NPK {tn}-{tp}-{tk}-{ts}S | **Basis:** 1000 kg (Wet Basis)")
st.markdown("---")

if run_calc:
    # 1. COMPATIBILITY CHECK
    issues = check_compatibility(active_mats)
    if issues:
        for issue in issues:
            st.error(issue)
        st.stop()
        
    # 2. OPTIMIZATION
    res, mat_order = calculate_optimization(tn, tp, tk, ts, active_mats, current_prices)
    
    if res.success:
        masses = res.x
        total_cost = res.fun
        
        # Process Result Data
        df = pd.DataFrame({"Material": mat_order, "Mass (kg)": masses})
        df = df[df["Mass (kg)"] > 0.1].sort_values("Mass (kg)", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: current_prices[x])
        df["Cost (IDR)"] = df["Mass (kg)"] * df["Price"]
        
        # Engineering Calculations
        # Moisture Load (Air yang harus diuapkan di Dryer)
        df["Moisture Content"] = df["Material"].apply(lambda x: RAW_MATS[x]["H2O"])
        df["Water Mass (kg)"] = (df["Mass (kg)"] * df["Moisture Content"]) / 100
        total_water_in = df["Water Mass (kg)"].sum()
        target_product_moisture = 1.5 # Target 1.5% moisture in product
        evaporation_load = total_water_in - (1000 * target_product_moisture/100)
        if evaporation_load < 0: evaporation_load = 0
        
        # Financials
        rm_cost_per_ton = df["Cost (IDR)"].sum()
        sales_revenue = 1000 * PRODUCT_PRICE
        gross_margin = sales_revenue - rm_cost_per_ton
        margin_percent = (gross_margin / sales_revenue) * 100
        
        # --- SECTION A: KEY PERFORMANCE INDICATORS ---
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">RM Cost / Ton</div>
                <div class="kpi-value">Rp {rm_cost_per_ton/1000000:.2f} Jt</div>
                <div class="kpi-sub">Optimized Formula Cost</div>
            </div>""", unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Est. Margin</div>
                <div class="kpi-value" style="color: #059669;">{margin_percent:.1f}%</div>
                <div class="kpi-sub">Rp {gross_margin/1000000:.2f} Jt / Ton</div>
            </div>""", unsafe_allow_html=True)
            
        with c3:
            # Comparison with Guarantee Baseline (If available)
            if grade_sel in GUARANTEE_REF:
                guar_recipe = GUARANTEE_REF[grade_sel]
                # Calculate Baseline Cost using CURRENT prices
                base_cost = sum([qty * current_prices.get(m, 0) for m, qty in guar_recipe.items() if m in current_prices])
                delta = base_cost - rm_cost_per_ton
                color = "#059669" if delta > 0 else "#dc2626"
                
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">Vs. Design Basis</div>
                    <div class="kpi-value" style="color:{color}">Rp {delta/1000:,.0f} k</div>
                    <div class="kpi-sub">Savings per Ton</div>
                </div>""", unsafe_allow_html=True)
            else:
                 st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Vs. Design</div><div class="kpi-value">-</div></div>""", unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Dryer Load</div>
                <div class="kpi-value" style="color: #d97706;">{evaporation_load:.1f} kg</div>
                <div class="kpi-sub">H2O Evaporation / Ton</div>
            </div>""", unsafe_allow_html=True)
            
        st.markdown("---")
        
        # --- SECTION B: DETAILED RECIPE & COMPOSITION ---
        c_table, c_chart = st.columns([1.5, 1])
        
        with c_table:
            st.subheader("📋 Production Recipe (Solid Feed)")
            st.caption("Data input untuk DCS Weigh Feeder System")
            
            # Format Table
            df_display = df[["Material", "Mass (kg)", "Moisture Content", "Cost (IDR)"]].copy()
            df_display["% Mix"] = (df_display["Mass (kg)"] / 1000) * 100
            
            st.dataframe(
                df_display,
                column_config={
                    "Mass (kg)": st.column_config.NumberColumn(format="%.2f"),
                    "Moisture Content": st.column_config.NumberColumn(label="H2O %", format="%.1f%%"),
                    "% Mix": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                    "Cost (IDR)": st.column_config.NumberColumn(format="Rp %.0f")
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Composition Checks (Engineering Limits)
            urea_mass = df[df["Material"] == "Urea"]["Mass (kg)"].sum()
            if urea_mass > 500:
                st.markdown(f"<div class='alert-warn'>⚠️ **High Urea Alert:** Urea content is {urea_mass:.0f} kg (>50%). Monitor dryer outlet temperature to prevent melting.</div>", unsafe_allow_html=True)
                
        with c_chart:
            st.subheader("Batch Composition")
            fig = go.Figure(data=[go.Pie(labels=df['Material'], values=df['Mass (kg)'], hole=.4)])
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
            
            # Nutrient Verification Chart
            act_n = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
            act_p = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
            act_k = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
            act_s = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
            
            fig_ver = go.Figure(data=[
                go.Bar(name='Target', x=['N','P','K','S'], y=[tn, tp, tk, ts], marker_color='#9ca3af'),
                go.Bar(name='Achieved', x=['N','P','K','S'], y=[act_n, act_p, act_k, act_s], marker_color='#10b981')
            ])
            fig_ver.update_layout(title="Nutrient Validation (%)", barmode='group', height=250, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_ver, use_container_width=True)

    else:
        st.error("Optimization Failed: Cannot meet grade targets with available materials.")

else:
    st.info("Select parameters on the sidebar and click RUN to optimize.")

# --- FOOTER ---
st.markdown("---")
st.caption("System ID: NPK-OPT-2025 | Linear Programming Engine | Calculation Basis: 1 Metric Ton Product")
