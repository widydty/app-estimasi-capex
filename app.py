import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.optimize import linprog

# ==============================================================================
# 1. CONFIGURATION & THEME ENGINE
# ==============================================================================
st.set_page_config(
    page_title="NPK Enterprise Intelligence",
    layout="wide",
    page_icon="🏭",
    initial_sidebar_state="expanded"
)

# ENTERPRISE CSS SYSTEM
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary: #0f172a;
            --secondary: #3b82f6;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg-light: #f8fafc;
            --card-bg: #ffffff;
        }
        
        .stApp { background-color: var(--bg-light); font-family: 'Inter', sans-serif; color: var(--primary); }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] { background-color: white; border-right: 1px solid #e2e8f0; }
        
        /* CARD COMPONENT */
        .ent-card {
            background: var(--card-bg);
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s;
        }
        .ent-card:hover { box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        
        /* METRICS */
        .metric-lbl { font-size: 11px; font-weight: 600; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; }
        .metric-val { font-size: 28px; font-weight: 700; color: #0f172a; margin-top: 4px; }
        .metric-sub { font-size: 13px; color: #94a3b8; margin-top: 2px; display: flex; align-items: center; gap: 4px; }
        
        /* CUSTOM TABS */
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] {
            height: 50px; white-space: pre-wrap; background-color: transparent;
            border-radius: 4px; color: #64748b; font-weight: 600;
        }
        .stTabs [aria-selected="true"] { color: var(--secondary); border-bottom-color: var(--secondary); }
        
        /* TABLE HEADER */
        thead tr th { background-color: #f1f5f9 !important; color: #475569 !important; font-size: 12px !important; }
        div[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; }
        
        /* HEADINGS */
        h1, h2, h3 { color: var(--primary) !important; letter-spacing: -0.02em; }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. EXTENDED ENGINEERING DATABASE
# ==============================================================================

# MATERIAL PROPERTIES (Chemistry + Physics + Cost)
# SGN (Size Guide Number): Average particle size in mm * 100. Important for segregation.
# Hardness: Relative factor (1.0 = Good).
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Source", "Price": 6500,  "SGN": 280, "Hardness": 0.8},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"H2O": 1.0, "Type": "Source", "Price": 2500,  "SGN": 250, "Hardness": 1.0},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "H2O": 1.5, "Type": "Source", "Price": 10500, "SGN": 300, "Hardness": 1.2},
    "TSP (0-46)":   {"N": 0.0,  "P": 46.0,"K": 0.0, "S": 0.0, "H2O": 4.0, "Type": "Acidic", "Price": 9800,  "SGN": 290, "Hardness": 0.9},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "H2O": 0.5, "Type": "Source", "Price": 8200,  "SGN": 260, "Hardness": 1.0},
    "Clay (Wet)":   {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 12.0,"Type": "Filler", "Price": 200,   "SGN": 50,  "Hardness": 1.5}, # Binder
    "Dolomite":     {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Filler", "Price": 350,   "SGN": 100, "Hardness": 0.7}
}

# GUARANTEE BASELINE (BEDP-02) - KEYS MUST MATCH RAW_MATS
# We normalize keys here to ensure no KeyError
GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP (16-45)": 343.3, "KCl (MOP)": 257.5, "ZA (AmSulf)": 94.9, "Clay (Wet)": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP (16-45)": 228.9, "KCl (MOP)": 206.0, "ZA (AmSulf)": 89.8, "Clay (Wet)": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP (16-45)": 366.3, "KCl (MOP)": 274.7, "ZA (AmSulf)": 0.0,  "Clay (Wet)": 158.2}
}

# UTILITY COST ASSUMPTIONS
ENERGY_CONSTANTS = {
    "Gas_Price_USD_MMBTU": 6.0,
    "Elec_Price_IDR_kWh": 1100,
    "Dryer_Efficiency": 0.65,
    "Heat_Vap_Water": 2260, # kJ/kg
    "Power_Per_Ton": 35 # kWh/ton (Crushing/Screening/Conveying)
}

# ==============================================================================
# 3. INTELLIGENCE ENGINE (LOGIC CORE)
# ==============================================================================

def check_compatibility_logic(selected_mats):
    """Checks for hazardous chemical interactions"""
    issues = []
    mats = set(selected_mats)
    
    # 1. Urea + TSP (Water Release)
    if "Urea" in mats and "TSP (0-46)" in mats:
        issues.append(("CRITICAL", "Urea & TSP Incompatibility. Reaction releases water. High caking risk."))
        
    # 2. Urea + Ammonium Nitrate (Not in list, but logic placeholder)
    # 3. High Chloride (Corrosion risk)
    
    return issues

def calculate_quality_metrics(df_recipe):
    """Calculates physical quality predictions based on weighted average"""
    if df_recipe.empty: return 0, 0
    
    total_mass = df_recipe["Mass"].sum()
    
    # SGN Prediction (Segregation Index)
    # Weighted average SGN
    df_recipe["SGN_Contrib"] = df_recipe["Mass"] * df_recipe["Material"].apply(lambda x: RAW_MATS[x]["SGN"])
    avg_sgn = df_recipe["SGN_Contrib"].sum() / total_mass
    
    # Hardness Potential (Binder effectiveness)
    df_recipe["Hard_Contrib"] = df_recipe["Mass"] * df_recipe["Material"].apply(lambda x: RAW_MATS[x]["Hardness"])
    avg_hardness = df_recipe["Hard_Contrib"].sum() / total_mass
    
    return avg_sgn, avg_hardness

def run_optimization_engine(tn, tp, tk, ts, selected_mats, prices, constraints):
    mats = list(selected_mats)
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    
    A_ub, b_ub = [], []
    
    # 1. Nutrient Targets (Min %)
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats]); b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats]); b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats]); b_ub.append(-tk/100 * total_mass)
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats]); b_ub.append(-ts/100 * total_mass)
        
    # 2. Engineering Constraints (Filler & Liquid Phase)
    if constraints['limit_filler']:
        filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
        A_ub.append(filler_row); b_ub.append(constraints['max_filler'])
        
    if constraints['limit_urea']:
        urea_row = [1.0 if RAW_MATS[m]["Type"] == "Urea" else 0.0 for m in mats]
        A_ub.append(urea_row); b_ub.append(constraints['max_urea'])

    # 3. Equality (Total Mass)
    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

def calculate_opex(df_recipe, gas_price):
    # 1. Drying Cost (Gas)
    # Calculate total water input
    water_in = sum(row['Mass'] * RAW_MATS[row['Material']]['H2O']/100 for _, row in df_recipe.iterrows())
    target_moist = 1.0 # 1% product moisture
    water_out = 1000 * target_moist/100
    evap_load = max(0, water_in - water_out)
    
    # Energy needed (MJ) = Mass * Heat_Vap / Efficiency
    energy_mj = evap_load * ENERGY_CONSTANTS['Heat_Vap_Water'] / 1000 / ENERGY_CONSTANTS['Dryer_Efficiency']
    mmbtu = energy_mj / 1055.06
    gas_cost = mmbtu * gas_price * 15500 # Assuming 15500 IDR/USD
    
    # 2. Power Cost (Electricity)
    power_cost = ENERGY_CONSTANTS['Power_Per_Ton'] * ENERGY_CONSTANTS['Elec_Price_IDR_kWh']
    
    return gas_cost, power_cost, evap_load

# ==============================================================================
# 4. UI CONTROLLER (LAYOUT)
# ==============================================================================

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.markdown("### 🎛️ Global Settings")
    
    grade_sel = st.selectbox("Production Grade", list(GUARANTEE_REF.keys()) + ["Custom"])
    
    # Presets Logic
    presets = {"N":15,"P":15,"K":15,"S":2} # Default
    if grade_sel == "15-10-12": presets = {"N":15,"P":10,"K":12,"S":2}
    elif grade_sel == "16-16-16": presets = {"N":16,"P":16,"K":16,"S":0}
    
    with st.expander("🧪 Nutrient Specification", expanded=True):
        c1, c2 = st.columns(2)
        tn = c1.number_input("N %", value=float(presets["N"]))
        tp = c2.number_input("P %", value=float(presets["P"]))
        tk = c1.number_input("K %", value=float(presets["K"]))
        ts = c2.number_input("S %", value=float(presets["S"]))

    with st.expander("⛓️ Engineering Constraints", expanded=False):
        limit_fill = st.checkbox("Limit Filler (<300kg)", value=True)
        limit_urea = st.checkbox("Limit Urea (<600kg)", value=True)
        st.caption("Prevents soft granules & melting issues.")
        
    with st.expander("💲 Market Prices (IDR/kg)", expanded=False):
        curr_prices = {}
        for m, p in RAW_MATS.items():
            curr_prices[m] = st.number_input(f"{m}", value=p["Price"], step=50)
            
    with st.expander("⚡ Energy Prices", expanded=False):
        gas_p = st.number_input("Gas ($/MMBTU)", value=6.0)
        
    st.markdown("---")
    run_btn = st.button("RUN SIMULATION", type="primary", use_container_width=True)

# --- MAIN DASHBOARD ---
st.title("NPK Integrated Intelligence System")
st.markdown(f"Target: **{grade_sel}** | Basis: **1000 kg** | Status: **{'Online' if run_btn else 'Ready'}**")

if run_btn:
    # 1. COMPATIBILITY CHECK
    mats_avail = list(RAW_MATS.keys())
    alerts = check_compatibility_logic(mats_avail)
    
    if alerts:
        for lvl, msg in alerts:
            if lvl == "CRITICAL": st.error(msg)
            else: st.warning(msg)
    
    # 2. OPTIMIZATION
    constraints = {"limit_filler": limit_fill, "max_filler": 300, "limit_urea": limit_urea, "max_urea": 600}
    res, mat_list = run_optimization_engine(tn, tp, tk, ts, mats_avail, curr_prices, constraints)
    
    if res.success:
        # DATA PREP
        masses = res.x
        df = pd.DataFrame({"Material": mat_list, "Mass": masses})
        df = df[df["Mass"] > 0.1].sort_values("Mass", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        
        # CALCULATE METRICS
        mat_cost_ton = df["Cost"].sum()
        gas_cost, power_cost, evap_load = calculate_opex(df, gas_p)
        total_opex = mat_cost_ton + gas_cost + power_cost
        
        # GUARANTEE COMPARISON
        guar_recipe = GUARANTEE_REF.get(grade_sel, {})
        baseline_mat_cost = 0
        if guar_recipe:
            for m, q in guar_recipe.items():
                # Fallback if material name mismatch
                p = curr_prices.get(m, 0) 
                baseline_mat_cost += q * p
        
        saving = baseline_mat_cost - mat_cost_ton
        
        # QUALITY PREDICTION
        sgn, hardness = calculate_quality_metrics(df)
        
        # --- TABS LAYOUT (ENTERPRISE) ---
        tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "⚙️ Process Insights", "📈 Sensitivity Analysis"])
        
        with tab1:
            # KPI ROW
            c1, c2, c3, c4 = st.columns(4)
            
            with c1:
                st.markdown(f"""
                <div class="ent-card">
                    <div class="metric-lbl">Raw Material Cost</div>
                    <div class="metric-val">Rp {mat_cost_ton/1e6:.2f} M</div>
                    <div class="metric-sub">Per Metric Ton</div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(f"""
                <div class="ent-card">
                    <div class="metric-lbl">Production OPEX</div>
                    <div class="metric-val">Rp {(gas_cost+power_cost)/1e3:.0f} k</div>
                    <div class="metric-sub">Energy + Power</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c3:
                color = "#10b981" if saving >= 0 else "#ef4444"
                sign = "+" if saving >= 0 else ""
                st.markdown(f"""
                <div class="ent-card" style="border-left: 4px solid {color};">
                    <div class="metric-lbl">Profit Impact</div>
                    <div class="metric-val" style="color:{color}">{sign}Rp {saving/1000:,.0f} k</div>
                    <div class="metric-sub">Vs Design Guarantee</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c4:
                st.markdown(f"""
                <div class="ent-card">
                    <div class="metric-lbl">Quality Prediction</div>
                    <div class="metric-val">{sgn:.0f} SGN</div>
                    <div class="metric-sub">Target: 250-300</div>
                </div>
                """, unsafe_allow_html=True)
                
            # MAIN TABLE & CHART
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                st.markdown("##### Optimized Formulation Recipe")
                df_show = df.copy()
                df_show["Mix %"] = df_show["Mass"] / 10
                st.dataframe(
                    df_show[["Material", "Mass", "Mix %", "Price", "Cost"]],
                    column_config={
                        "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                        "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.1f"),
                        "Mix %": st.column_config.ProgressColumn("Ratio", format="%.1f%%", min_value=0, max_value=100),
                        "Price": st.column_config.NumberColumn("Price", format="Rp %.0f"),
                        "Cost": st.column_config.NumberColumn("Total", format="Rp %.0f"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
            with c_right:
                st.markdown("##### Cost Structure Breakdown")
                # Waterfall Chart for Costs
                fig_water = go.Figure(go.Waterfall(
                    orientation = "v",
                    measure = ["relative"] * 3 + ["total"],
                    x = ["Materials", "Gas (Drying)", "Electricity", "Total COGS"],
                    y = [mat_cost_ton, gas_cost, power_cost, 0],
                    connector = {"line":{"color":"rgb(63, 63, 63)"}},
                ))
                fig_water.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_water, use_container_width=True)

        with tab2:
            # PROCESS ENGINEERING VALIDATION
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("##### 🧪 Nutrient Verification")
                # Actual Nutrients
                act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
                act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
                act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
                act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
                
                fig_rad = go.Figure(data=go.Scatterpolar(
                    r=[act_n/tn*100, act_p/tp*100, act_k/tk*100, 100],
                    theta=['N', 'P', 'K', 'Ref'],
                    fill='toself', name='Achieved %'
                ))
                fig_rad.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 120])), showlegend=False, height=300)
                st.plotly_chart(fig_rad, use_container_width=True)
                
            with c2:
                st.markdown("##### 🔥 Thermal Load Analysis")
                st.info(f"**Evaporation Load:** {evap_load:.1f} kg H2O/ton product")
                if evap_load > 40:
                    st.warning("High drying load detected. Check burner capacity.")
                else:
                    st.success("Drying load within normal operating range.")
                
                st.markdown("##### 💎 Physical Quality")
                st.progress(min(hardness/1.5, 1.0), text=f"Hardness Index: {hardness:.2f} (Higher is better)")
        
        with tab3:
            st.markdown("##### 🎲 Sensitivity Analysis: Urea Price Impact")
            st.caption("How does Urea price fluctuation affect Total Production Cost?")
            
            # Generate Sensitivity Data
            base_urea_price = curr_prices["Urea"]
            range_pct = np.linspace(0.8, 1.2, 10) # +/- 20%
            sim_costs = []
            sim_prices = []
            
            for r in range_pct:
                p_sim = base_urea_price * r
                # Simplified estimation: assume recipe static (worst case) or re-optimize (best case)
                # Here we assume simple linear impact on current recipe for speed
                urea_mass = df[df["Material"]=="Urea"]["Mass"].sum()
                cost_diff = (p_sim - base_urea_price) * urea_mass
                sim_costs.append(total_opex + cost_diff)
                sim_prices.append(p_sim)
                
            fig_sens = px.line(x=sim_prices, y=sim_costs, labels={"x": "Urea Price (IDR)", "y": "Total Cost (IDR)"})
            fig_sens.add_vline(x=base_urea_price, line_dash="dash", annotation_text="Current Price")
            st.plotly_chart(fig_sens, use_container_width=True)

    else:
        st.error("Infeasible Solution. Please check constraints.")
else:
    st.info("System Ready. Configure parameters in sidebar to start.")

# --- FOOTER ---
st.markdown("---")
st.markdown("<div style='text-align:center; color:#94a3b8; font-size:12px;'>NPK Enterprise System v6.0 | Linear Programming & Process Engineering Engine</div>", unsafe_allow_html=True)
