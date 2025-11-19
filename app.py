import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.optimize import linprog

st.set_page_config(page_title="NPK Engineer Pro", layout="wide", page_icon="🏭")

# CSS Clean Theme
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        .stApp { background-color: #f3f4f6; font-family: 'Inter', sans-serif; color: #1f2937; }
        .warning-box { background-color: #fef3c7; border-left: 5px solid #d97706; padding: 15px; margin-bottom: 20px; }
        .success-box { background-color: #d1fae5; border-left: 5px solid #059669; padding: 15px; }
    </style>
""", unsafe_allow_html=True)

# DATABASE MATERIAL (Updated with Compatibility Groups)
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0,  "K": 0.0,  "Price": 6500, "Type": "Urea_Base"},
    "ZA (Ammonium Sulf)": {"N": 21.0, "P": 0.0,  "K": 0.0,  "Price": 2200, "Type": "Neutral"},
    "DAP (18-46)":  {"N": 18.0, "P": 46.0, "K": 0.0,  "Price": 10500, "Type": "Neutral"},
    "TSP (0-46)":   {"N": 0.0,  "P": 46.0, "K": 0.0,  "Price": 9800, "Type": "Acidic_P"},
    "KCL (MOP)":    {"N": 0.0,  "P": 0.0,  "K": 60.0, "Price": 8200, "Type": "Potash"},
    "Dolomite":     {"N": 0.0,  "P": 0.0,  "K": 0.0,  "Price": 300, "Type": "Filler"},
    "Clay":         {"N": 0.0,  "P": 0.0,  "K": 0.0,  "Price": 250, "Type": "Filler"}
}

def check_compatibility(selected_mats):
    issues = []
    mats = set(selected_mats)
    
    # Rule 1: Urea vs TSP (The Water Release Problem)
    if "Urea" in mats and "TSP (0-46)" in mats:
        issues.append("❌ **CRITICAL:** Urea cannot be mixed with TSP/Superphosphate! It forms adducts and releases water (wet sticky mess).")
    
    # Rule 2: Filler Limit (Granulation Physics)
    # This is a heuristic check, not optimization constraint yet
    return issues

def optimize(tn, tp, tk, mats):
    # Linear Programming Engine
    n_vars = len(mats)
    c = [RAW_MATS[m]["Price"] for m in mats]
    
    # Equality: Total = 1000 kg
    A_eq = [[1.0] * n_vars]
    b_eq = [1000.0]
    
    # Inequalities: Nutrients >= Target
    A_ub = []
    b_ub = []
    
    # N, P, K Constraints
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * 1000)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * 1000)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * 1000)
    
    # ENGINEERING CONSTRAINTS (Hard Limits)
    # Contoh: Batasi Filler maks 20% (200kg) agar granul tidak rapuh
    filler_indices = [i for i, m in enumerate(mats) if RAW_MATS[m]["Type"] == "Filler"]
    if filler_indices:
        filler_row = [0.0] * n_vars
        for idx in filler_indices: filler_row[idx] = 1.0
        A_ub.append(filler_row)
        b_ub.append(250.0) # Max 250 kg filler allowed
    
    bounds = [(0, 1000) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res

# --- UI ---
st.title("🏭 NPK Process Formulator (Engineering Grade)")
st.markdown("**Feasibility Check Enabled:** Chemical Compatibility & Granulation Limits")

with st.sidebar:
    st.header("Target NPK")
    c1, c2, c3 = st.columns(3)
    tn = c1.number_input("N", value=15)
    tp = c2.number_input("P", value=15)
    tk = c3.number_input("K", value=15)
    
    st.header("Raw Materials")
    selected = []
    for m in RAW_MATS:
        if st.checkbox(m, value=True):
            selected.append(m)

    calc = st.button("Run Simulation", type="primary")

if calc:
    # 1. PRE-CHECK (Engineering Logic)
    compatibility_issues = check_compatibility(selected)
    
    if compatibility_issues:
        st.error("Process Safety / Compatibility Violation Detected!")
        for issue in compatibility_issues:
            st.markdown(f"<div class='warning-box'>{issue}</div>", unsafe_allow_html=True)
        st.stop() # Stop calculation
        
    # 2. OPTIMIZATION
    res = optimize(tn, tp, tk, selected)
    
    if res.success:
        st.success("✅ Formulation Feasible & Optimized")
        
        # Data processing
        df = pd.DataFrame({"Material": selected, "Mass (kg)": res.x})
        df = df[df["Mass (kg)"] > 0.1].sort_values("Mass (kg)", ascending=False)
        df["Cost"] = df["Material"].apply(lambda x: RAW_MATS[x]["Price"]) * df["Mass (kg)"]
        
        # 3. POST-CHECK (Granulation Logic)
        # Cek rasio liquid phase potential (Urea)
        urea_amt = df[df["Material"] == "Urea"]["Mass (kg)"].sum()
        if urea_amt > 600:
            st.warning(f"⚠️ **Warning:** Urea content ({urea_amt:.0f} kg) is very high (>60%). Granules might melt in dryer. Check dryer temperature limits.")
            
        filler_amt = df[df["Material"].isin(["Dolomite", "Clay"])]["Mass (kg)"].sum()
        if filler_amt > 200: # Batas dari hard constraint tadi
            st.warning("⚠️ Filler content is high. Check granule hardness.")

        # Display
        c1, c2 = st.columns([1.5, 1])
        with c1:
            st.subheader("Batch Recipe (1000 kg)")
            st.dataframe(
                df.style.format({"Mass (kg)": "{:.1f}", "Cost": "Rp {:,.0f}"}),
                use_container_width=True
            )
        with c2:
            st.subheader("Cost Structure")
            st.metric("COGS Material", f"Rp {res.fun:,.0f}")
            fig = px.pie(df, values="Mass (kg)", names="Material", hole=0.5)
            st.plotly_chart(fig, use_container_width=True)
            
    else:
        st.error("Optimization Failed. Target grade cannot be achieved with selected materials/constraints.")
