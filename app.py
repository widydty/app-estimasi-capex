import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(page_title="NPK Enterprise System", layout="wide", page_icon="🏭")

# CSS: CLEAN CORPORATE (SWISS STYLE)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #0f172a; }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
        
        /* METRIC CARDS (Minimalist Border) */
        .kpi-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            height: 100%;
        }
        .kpi-label {
            font-size: 11px; font-weight: 600; color: #64748b;
            text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px;
        }
        .kpi-val { font-size: 26px; font-weight: 700; color: #0f172a; }
        .kpi-sub { font-size: 12px; color: #94a3b8; margin-top: 4px; }
        
        /* ALERT BOXES */
        .alert-error { background: #fef2f2; border: 1px solid #fca5a5; color: #b91c1c; padding: 15px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; }
        .alert-warn { background: #fffbeb; border: 1px solid #fcd34d; color: #92400e; padding: 15px; border-radius: 8px; font-size: 14px; margin-bottom: 20px; }
        
        /* TABLE HEADER */
        thead tr th:first-child {display:none} tbody th {display:none}
        div[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; }
        
        /* BUTTONS */
        .stButton>button {
            background-color: #0f172a; color: white; border-radius: 6px; font-weight: 600;
            border: none; padding: 0.6rem 1rem; width: 100%;
        }
        .stButton>button:hover { background-color: #334155; }
        
        h1, h2, h3 { color: #0f172a !important; letter-spacing: -0.5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ENGINEERING DATABASE ---
# Added: Moisture Content (H2O) & Compatibility Type
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Urea", "Price": 6500},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"H2O": 1.0, "Type": "Salt", "Price": 2500},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "H2O": 1.5, "Type": "Salt", "Price": 10500},
    "TSP (0-46)":   {"N": 0.0,  "P": 46.0,"K": 0.0, "S": 0.0, "H2O": 4.0, "Type": "Acid", "Price": 9800},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "H2O": 0.5, "Type": "Salt", "Price": 8200},
    "Clay (Wet)":   {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 12.0,"Type": "Filler","Price": 200},
    "Dolomite":     {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Filler","Price": 350}
}

GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay (Wet)": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay (Wet)": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay (Wet)": 158.2}
}

# --- 3. LOGIC ENGINE ---

def check_compatibility(selected_mats):
    """Checks for dangerous chemical combinations"""
    issues = []
    mats = set(selected_mats)
    
    # CRITICAL SAFETY: Urea + TSP = Adduct formation (Release water -> Sticky mess)
    if "Urea" in mats and "TSP (0-46)" in mats:
        issues.append("❌ **CRITICAL INCOMPATIBILITY:** Urea cannot be mixed with TSP. It causes severe caking and water release (wet slurry). Please choose either Urea-based or TSP-based route.")
        
    return issues

def calculate_optimization(tn, tp, tk, ts, selected_mats, prices):
    mats = list(selected_mats)
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    
    A_ub, b_ub = [], []
    
    # Nutrients Constraints
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # ENGINEERING CONSTRAINTS
    
    # 1. Filler Limit (Max 30% to maintain Granule Hardness)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0) 
        
    # 2. Urea Limit (Liquid Phase Control - Max 60% to prevent melting in Dryer)
    urea_row = [1.0 if RAW_MATS[m]["Type"] == "Urea" else 0.0 for m in mats]
    if sum(urea_row) > 0:
        A_ub.append(urea_row)
        b_ub.append(600.0)

    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

def calculate_energy_cost(df_recipe, gas_price_mmbtu):
    # Energy Intelligence
    # Basis: Evaporate water to reach 1% product moisture
    # Heat of Vaporization ~ 2260 kJ/kg + Efficiency Loss
    # Simplified: 1 kg water evap needs approx 4 MJ of Fuel (Industry Rule of Thumb for Rotary Dryer)
    
    total_water_in = 0
    for _, row in df_recipe.iterrows():
        moist = RAW_MATS[row['Material']]['H2O']
        total_water_in += row['Mass'] * (moist/100)
        
    target_prod_moisture = 0.01 # 1%
    water_out = 1000 * target_prod_moisture
    evap_load = max(0, total_water_in - water_out)
    
    # Cost Calc
    mj_per_kg_evap = 4.0
    total_mj = evap_load * mj_per_kg_evap
    mmbtu_needed = total_mj / 1055 # 1 MMBTU = 1055 MJ
    gas_cost_idr = mmbtu_needed * gas_price_mmbtu * 15500 # Asumsi 1 USD = 15500 IDR
    
    return gas_cost_idr, evap_load

# --- 4. UI LAYOUT ---

# SIDEBAR
with st.sidebar:
    st.header("⚙️ Parameters")
    
    st.subheader("1. Grade Target")
    grade_sel = st.selectbox("Select Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"], label_visibility="collapsed")
    
    if grade_sel == "15-15-15": defs = (15,15,15,2)
    elif grade_sel == "15-10-12": defs = (15,10,12,2)
    elif grade_sel == "16-16-16": defs = (16,16,16,0)
    else: defs = (15,15,15,0)
    
    c1, c2 = st.columns(2)
    tn = c1.number_input("N %", value=float(defs[0]))
    tp = c2.number_input("P %", value=float(defs[1]))
    tk = c1.number_input("K %", value=float(defs[2]))
    ts = c2.number_input("S %", value=float(defs[3]))
    
    st.subheader("2. Energy Cost")
    gas_price = st.number_input("Gas Price ($/MMBTU)", value=6.0, step=0.5)
    
    st.subheader("3. Material Inventory")
    active_mats = st.multiselect("Available Stock", list(RAW_MATS.keys()), default=["Urea", "ZA (AmSulf)", "DAP (16-45)", "KCl (MOP)", "Clay (Wet)"])
    
    st.subheader("4. Market Prices (IDR/kg)")
    curr_prices = {}
    for m in active_mats:
        curr_prices[m] = st.number_input(f"{m}", value=RAW_MATS[m]["Price"], step=50)
        
    st.markdown("---")
    run_btn = st.button("RUN OPTIMIZATION")

# MAIN CONTENT
st.title("NPK Integrated Intelligence")
st.markdown(f"Optimization Target: **NPK {tn}-{tp}-{tk}-{ts}S** | Basis: **1 Metric Ton**")
st.markdown("---")

if run_btn:
    # 1. COMPATIBILITY CHECK
    issues = check_compatibility(active_mats)
    if issues:
        for i in issues:
            st.markdown(f"<div class='alert-error'>{i}</div>", unsafe_allow_html=True)
    else:
        # 2. RUN CALCULATION
        res, mat_list = calculate_optimization(tn, tp, tk, ts, active_mats, curr_prices)
        
        if res.success:
            masses = res.x
            df = pd.DataFrame({"Material": mat_list, "Mass": masses})
            df = df[df["Mass"] > 0.01].sort_values("Mass", ascending=False)
            df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
            df["Mat_Cost"] = df["Mass"] * df["Price"]
            
            # 3. ENERGY CALCULATION
            energy_cost, evap_load = calculate_energy_cost(df, gas_price)
            mat_cost_total = df["Mat_Cost"].sum()
            total_var_cost = mat_cost_total + energy_cost
            
            # 4. BASELINE COMPARISON
            guar_recipe = GUARANTEE_REF.get(grade_sel, {})
            baseline_mat_cost = 0
            if guar_recipe:
                # Hitung biaya material baseline (abaikan material yg tidak dipilih user utk simplifikasi, atau assume user punya semua)
                for m, q in guar_recipe.items():
                    p = RAW_MATS[m]["Price"] # Pakai harga standar jika tidak ada di input user
                    if m in curr_prices: p = curr_prices[m]
                    baseline_mat_cost += q * p
            
            saving_mat = baseline_mat_cost - mat_cost_total
            
            # --- DASHBOARD DISPLAY ---
            
            # ROW 1: FINANCIALS
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Raw Material Cost</div><div class="kpi-val">Rp {mat_cost_total/1e6:.2f} M</div><div class="kpi-sub">Per Ton</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Energy Cost (Gas)</div><div class="kpi-val">Rp {energy_cost:,.0f}</div><div class="kpi-sub">Based on Moisture Load</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="kpi-card"><div class="kpi-label">Total Variable Cost</div><div class="kpi-val">Rp {total_var_cost/1e6:.2f} M</div><div class="kpi-sub">Mat + Energy</div></div>""", unsafe_allow_html=True)
            with c4:
                color = "#10b981" if saving_mat >= 0 else "#ef4444"
                sign = "+" if saving_mat >= 0 else ""
                st.markdown(f"""<div class="kpi-card" style="border-left: 5px solid {color}"><div class="kpi-label">Vs Design Guarantee</div><div class="kpi-val" style="color:{color}">{sign}Rp {saving_mat/1000:,.0f} k</div><div class="kpi-sub">Material Savings/Ton</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # ROW 2: OPERATIONAL INSIGHTS
            if evap_load > 40:
                st.markdown(f"<div class='alert-warn'>⚠️ **High Dryer Load:** Evaporation load is {evap_load:.1f} kg H2O/ton. Ensure Dryer Burner capacity is sufficient. Consider reducing wet filler (Clay).</div>", unsafe_allow_html=True)
            
            col_tbl, col_chart = st.columns([2, 1])
            
            with col_tbl:
                st.markdown("##### 📋 Optimized Recipe & Specs")
                df_show = df.copy()
                df_show["% Mix"] = df_show["Mass"] / 10
                df_show["Moist %"] = df_show["Material"].apply(lambda x: RAW_MATS[x]["H2O"])
                
                st.dataframe(
                    df_show[["Material", "Mass", "% Mix", "Moist %", "Mat_Cost"]],
                    column_config={
                        "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                        "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                        "% Mix": st.column_config.ProgressColumn("Ratio", format="%.1f%%", min_value=0, max_value=100),
                        "Moist %": st.column_config.NumberColumn("H2O", format="%.1f%%"),
                        "Mat_Cost": st.column_config.NumberColumn("Cost (IDR)", format="Rp %.0f"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
            with col_chart:
                st.markdown("##### Cost Structure")
                fig = go.Figure(go.Pie(
                    labels=['Materials', 'Energy'], 
                    values=[mat_cost_total, energy_cost],
                    hole=.6, marker_colors=['#0f172a', '#3b82f6']
                ))
                fig.update_layout(margin=dict(t=0,b=0,l=0,r=0), height=250, showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

            # ROW 3: VALIDATION
            st.markdown("##### 🛡️ Nutrient & Constraint Validation")
            act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
            act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
            act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
            act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
            
            fig_bar = go.Figure()
            labels = ['N', 'P2O5', 'K2O', 'S']
            fig_bar.add_trace(go.Bar(name='Target', x=labels, y=[tn, tp, tk, ts], marker_color='#e2e8f0'))
            fig_bar.add_trace(go.Bar(name='Actual', x=labels, y=[act_n, act_p, act_k, act_s], marker_color='#0f172a', text=[f"{x:.1f}" for x in [act_n, act_p, act_k, act_s]], textposition='auto'))
            fig_bar.update_layout(barmode='group', height=250, margin=dict(t=10,b=10), plot_bgcolor='white')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        else:
            st.error("Optimization Failed: Constraints cannot be met. Try allowing more materials or relaxing constraints.")
            
else:
    st.info("Ready. Adjust parameters and click RUN OPTIMIZATION.")
