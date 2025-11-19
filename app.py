import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.optimize import linprog

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NPK Smart Formulator", layout="wide", page_icon="🌱")

# --- 2. STYLE ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        .stApp { background-color: #f0fdf4; font-family: 'Inter', sans-serif; } /* Light Green Tint */
        
        /* Headers */
        h1, h2, h3 { color: #14532d; letter-spacing: -0.5px; font-weight: 800; }
        
        /* Cards */
        .metric-card {
            background: white; padding: 20px; border-radius: 10px;
            border: 1px solid #bbf7d0; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            text-align: center;
        }
        .metric-val { font-size: 32px; font-weight: 700; color: #16a34a; }
        .metric-lbl { font-size: 12px; text-transform: uppercase; color: #65a30d; font-weight: 600; }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #dcfce7; }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE BAHAN BAKU (RAW MATERIALS) ---
# Default specs (Standard Fertilizer Industry)
# N, P2O5, K2O, Moisture, Cost (Rp/kg)
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0,  "K": 0.0,  "H2O": 0.5, "Price": 6500},
    "ZA (Ammonium Sulfate)": {"N": 21.0, "P": 0.0,  "K": 0.0,  "H2O": 0.2, "Price": 2500},
    "DAP (Diammonium Phos)": {"N": 18.0, "P": 46.0, "K": 0.0,  "H2O": 1.0, "Price": 11000},
    "MAP (Monoammonium Phos)":{"N": 11.0, "P": 52.0, "K": 0.0,  "H2O": 1.0, "Price": 10500},
    "RP (Rock Phosphate)":   {"N": 0.0,  "P": 28.0, "K": 0.0,  "H2O": 3.0, "Price": 1800},
    "KCl (MOP)":             {"N": 0.0,  "P": 0.0,  "K": 60.0, "H2O": 0.5, "Price": 8500},
    "ZK (SOP)":              {"N": 0.0,  "P": 0.0,  "K": 50.0, "H2O": 0.5, "Price": 12000},
    "Dolomite (Filler)":     {"N": 0.0,  "P": 0.0,  "K": 0.0,  "H2O": 0.5, "Price": 500},
    "Clay (Filler)":         {"N": 0.0,  "P": 0.0,  "K": 0.0,  "H2O": 2.0, "Price": 300},
}

# --- 4. OPTIMIZATION ENGINE (LINEAR PROGRAMMING) ---
def optimize_formula(target_n, target_p, target_k, selected_mats, total_mass=1000):
    """
    Menggunakan Simplex Method untuk mencari resep termurah.
    Constraints:
    1. Mass Balance Total = 1000 kg
    2. Total N >= Target N
    3. Total P >= Target P
    4. Total K >= Target K
    Objective: Minimize Cost
    """
    
    mats = [m for m in selected_mats]
    n_vars = len(mats)
    
    # Objective Function (Minimize Cost)
    c = [RAW_MATS[m]["Price"] for m in mats]
    
    # Constraints Matrix (A_eq * x = b_eq) -> Mass Balance Total
    A_eq = [[1.0] * n_vars]
    b_eq = [total_mass]
    
    # Constraints Inequality (A_ub * x >= b_ub  -->  -A_ub * x <= -b_ub)
    # Kita pakai 'greater than or equal' karena spek pupuk itu minimal (misal N minimal 15%)
    # Scipy linprog pakai '<=', jadi kita kalikan -1
    A_ub = []
    b_ub = []
    
    # N Balance
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-target_n/100 * total_mass)
    
    # P Balance
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-target_p/100 * total_mass)
    
    # K Balance
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-target_k/100 * total_mass)

    # Bounds (0 to Total Mass)
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    # Solve
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    
    if res.success:
        return {
            "success": True,
            "recipe": dict(zip(mats, res.x)),
            "total_cost": res.fun
        }
    else:
        return {"success": False, "message": res.message}

# --- 5. UI LAYOUT ---
st.title("🌱 NPK SMART FORMULATOR")
st.markdown("### Least Cost Formulation (LCF) Optimizer")

# SIDEBAR INPUT
with st.sidebar:
    st.header("🎯 Target Grade")
    
    c1, c2, c3 = st.columns(3)
    t_n = c1.number_input("N %", 0.0, 30.0, 15.0)
    t_p = c2.number_input("P %", 0.0, 30.0, 15.0)
    t_k = c3.number_input("K %", 0.0, 30.0, 15.0)
    
    st.markdown("---")
    st.header("📦 Raw Material Availability")
    st.write("Uncheck if material is out of stock")
    
    active_mats = []
    for mat in RAW_MATS.keys():
        # Default selected
        def_val = True
        if mat in ["MAP", "ZK", "RP"]: def_val = False # Default off for premium/raw items
        
        if st.checkbox(f"{mat} (Rp {RAW_MATS[mat]['Price']})", value=def_val):
            active_mats.append(mat)
            
    st.markdown("---")
    st.info("Optimization Basis: **1000 kg (1 Ton) Product**")

# MAIN DASHBOARD
if st.button("🚀 OPTIMIZE RECIPE", type="primary"):
    
    if not active_mats:
        st.error("Please select at least some raw materials.")
    else:
        with st.spinner("Calculating optimal formulation..."):
            result = optimize_formula(t_n, t_p, t_k, active_mats)
            
        if result["success"]:
            recipe = result["recipe"]
            total_cost = result["total_cost"]
            
            # --- TOP METRICS ---
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"""<div class="metric-card"><div class="metric-lbl">Cost per Ton</div><div class="metric-val">Rp {total_cost:,.0f}</div></div>""", unsafe_allow_html=True)
            
            # Hitung Real Content
            real_n = sum([recipe[m] * RAW_MATS[m]["N"]/100 for m in active_mats]) / 10
            real_p = sum([recipe[m] * RAW_MATS[m]["P"]/100 for m in active_mats]) / 10
            real_k = sum([recipe[m] * RAW_MATS[m]["K"]/100 for m in active_mats]) / 10
            
            c2.markdown(f"""<div class="metric-card"><div class="metric-lbl">Grade Achieved</div><div class="metric-val">{real_n:.1f}-{real_p:.1f}-{real_k:.1f}</div></div>""", unsafe_allow_html=True)
            
            # Total Mass Check
            total_mass_calc = sum(recipe.values())
            c3.markdown(f"""<div class="metric-card"><div class="metric-lbl">Total Batch Mass</div><div class="metric-val">{total_mass_calc:.0f} kg</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            
            # --- DETAILED RECIPE & VISUALS ---
            col_table, col_chart = st.columns([1, 1])
            
            # Dataframe Prep
            df_recipe = pd.DataFrame.from_dict(recipe, orient='index', columns=['Mass (kg)'])
            df_recipe = df_recipe[df_recipe['Mass (kg)'] > 0.1] # Filter yang 0
            df_recipe['Cost (Rp)'] = df_recipe.index.map(lambda x: df_recipe.loc[x, 'Mass (kg)'] * RAW_MATS[x]['Price'])
            df_recipe['% Composition'] = (df_recipe['Mass (kg)'] / 1000) * 100
            
            with col_table:
                st.subheader("📋 Production Recipe")
                st.dataframe(
                    df_recipe.style.format({"Mass (kg)": "{:.2f}", "Cost (Rp)": "Rp {:,.0f}", "% Composition": "{:.1f}%"}),
                    use_container_width=True
                )
                
                # Download Button
                csv = df_recipe.to_csv().encode('utf-8')
                st.download_button("📥 Download Recipe to DCS/Excel", csv, "NPK_Recipe.csv", "text/csv")
            
            with col_chart:
                st.subheader("📊 Composition vs Cost")
                # Sunburst Chart or Pie Chart
                fig = px.pie(df_recipe, values='Mass (kg)', names=df_recipe.index, 
                             title="Mass Breakdown (kg)", hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Greens_r)
                st.plotly_chart(fig, use_container_width=True)
                
                # Cost Bar
                fig2 = px.bar(df_recipe, x=df_recipe.index, y='Cost (Rp)', 
                              title="Cost Contribution (Where does the money go?)",
                              text_auto='.2s', color='Cost (Rp)', color_continuous_scale='RdYlGn_r')
                st.plotly_chart(fig2, use_container_width=True)
                
        else:
            st.error(f"Optimization Failed: {result['message']}")
            st.warning("Hint: Mungkin target Grade terlalu tinggi untuk bahan baku yang dipilih (misal minta K tinggi tapi KCl tidak dicentang).")

# --- FOOTER ---
st.markdown("---")
st.caption("NPK Process Intelligence System | Linear Programming Engine | Formula Basis: 1000 kg")
