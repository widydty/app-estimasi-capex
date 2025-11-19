import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. CONFIGURATION & CLEAN THEME ---
st.set_page_config(page_title="NPK Formulator Pro", layout="wide", page_icon="⚗️")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        /* Base Styles */
        .stApp {
            background-color: #ffffff; /* Pure White */
            font-family: 'Inter', sans-serif;
            color: #111827;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #f9fafb; /* Very Light Grey */
            border-right: 1px solid #e5e7eb;
        }
        
        /* Headings */
        h1, h2, h3 {
            color: #111827 !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        
        /* Custom Metric Box (Clean Style) */
        .metric-box {
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 20px;
            background: white;
            text-align: left;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        .metric-label {
            font-size: 12px;
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 30px;
            font-weight: 700;
            color: #059669; /* Emerald Green */
        }
        .metric-sub {
            font-size: 13px;
            color: #9ca3af;
            margin-top: 4px;
        }
        
        /* Table Clean Up */
        div[data-testid="stDataFrame"] {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
        }
        
        /* Button Styling */
        .stButton>button {
            background-color: #059669;
            color: white;
            border-radius: 8px;
            font-weight: 600;
            border: none;
            padding: 0.5rem 1rem;
        }
        .stButton>button:hover {
            background-color: #047857;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. RAW MATERIAL DATABASE ---
# Kandungan N-P-K dan Harga (Estimasi IDR/kg)
RAW_MATS = {
    "Urea (Prill)":      {"N": 46.0, "P": 0.0,  "K": 0.0,  "Price": 6500},
    "ZA (Amm. Sulf)":    {"N": 21.0, "P": 0.0,  "K": 0.0,  "Price": 2200},
    "DAP (18-46)":       {"N": 18.0, "P": 46.0, "K": 0.0,  "Price": 10500},
    "TSP (0-46)":        {"N": 0.0,  "P": 46.0, "K": 0.0,  "Price": 9800},
    "KCL (MOP flakes)":  {"N": 0.0,  "P": 0.0,  "K": 60.0, "Price": 8200},
    "ZK (SOP)":          {"N": 0.0,  "P": 0.0,  "K": 50.0, "Price": 11500},
    "Dolomite (Filler)": {"N": 0.0,  "P": 0.0,  "K": 0.0,  "Price": 300},
    "Clay (Filler)":     {"N": 0.0,  "P": 0.0,  "K": 0.0,  "Price": 250}
}

# --- 3. CALCULATION ENGINE ---
def solve_optimization(target_n, target_p, target_k, available_mats):
    # Setup Matrix for Linear Programming
    # Variables: x1, x2, ... xn (Mass of each material)
    
    mats = list(available_mats)
    n_vars = len(mats)
    
    # 1. Objective: Minimize Cost
    # c = [Price1, Price2, ...]
    c = [RAW_MATS[m]["Price"] for m in mats]
    
    # 2. Constraints
    A_ub = [] # Inequality (Greater than or Equal -> converted to Less than or Equal)
    b_ub = []
    
    A_eq = [] # Equality
    b_eq = []
    
    # Constraint A: Total Mass MUST be exactly 1000 kg
    A_eq.append([1.0] * n_vars)
    b_eq.append(1000.0)
    
    # Constraint B: Nutrient Targets (Min %)
    # Equation: Sum(Content * Mass) >= Target% * 1000
    # Scipy linprog uses <=, so we multiply by -1:
    # -Sum(Content * Mass) <= -(Target% * 1000)
    
    # N Balance
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-target_n/100 * 1000)
    
    # P Balance
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-target_p/100 * 1000)
    
    # K Balance
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-target_k/100 * 1000)
    
    # Bounds (0 to 1000 kg per item)
    bounds = [(0, 1000) for _ in range(n_vars)]
    
    # Run Solver
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    
    return res, mats

# --- 4. UI LAYOUT ---

# Sidebar
with st.sidebar:
    st.markdown("### 🧪 Formulation Specs")
    st.caption("Target Grade (SNI)")
    
    col_s1, col_s2, col_s3 = st.columns(3)
    tn = col_s1.number_input("N", 0, 50, 15)
    tp = col_s2.number_input("P", 0, 50, 15)
    tk = col_s3.number_input("K", 0, 50, 15)
    
    st.markdown("### 🏭 Inventory")
    st.caption("Select Available Materials")
    
    selected_materials = []
    # Create columns for checkbox layout
    for mat_name in RAW_MATS.keys():
        # Default checked except premium ones
        is_checked = True
        if "ZK" in mat_name or "Clay" in mat_name: is_checked = False 
        
        if st.checkbox(mat_name, value=is_checked):
            selected_materials.append(mat_name)

    st.markdown("---")
    calculate_btn = st.button("CALCULATE RECIPE", type="primary", use_container_width=True)

# Main Content
st.title("NPK Process Formulator")
st.markdown(f"**Production Basis:** 1.000 kg (1 Ton) • **Target Grade:** NPK {tn}-{tp}-{tk}")
st.markdown("---")

if calculate_btn:
    if not selected_materials:
        st.error("Please select at least one material from the inventory.")
    else:
        # Run Optimization
        with st.spinner("Running Linear Programming Algorithm..."):
            res, mat_names = solve_optimization(tn, tp, tk, selected_materials)
        
        if res.success:
            # --- PROCESS RESULTS ---
            masses = res.x
            total_cost = res.fun
            
            # Create Result DataFrame
            df = pd.DataFrame({
                "Material": mat_names,
                "Mass (kg)": masses,
                "Unit Price": [RAW_MATS[m]["Price"] for m in mat_names],
            })
            
            # Filter out near-zero values (computational artifacts)
            df = df[df["Mass (kg)"] > 0.01].sort_values(by="Mass (kg)", ascending=False)
            
            # Calculate Total Cost per Row
            df["Total Cost (IDR)"] = df["Mass (kg)"] * df["Unit Price"]
            df["% Mix"] = (df["Mass (kg)"] / 1000) * 100
            
            # Calculate Actual Nutrients Achieved
            act_n = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
            act_p = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
            act_k = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10

            # --- 1. KEY METRICS ROW ---
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">COGS per Ton</div>
                    <div class="metric-value">Rp {total_cost:,.0f}</div>
                    <div class="metric-sub">Raw Material Cost Only</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c2:
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Cost per Bag (50kg)</div>
                    <div class="metric-value">Rp {(total_cost/20):,.0f}</div>
                    <div class="metric-sub">Standard Packaging</div>
                </div>
                """, unsafe_allow_html=True)
                
            with c3:
                # Grade Accuracy Check
                grade_str = f"{act_n:.1f} - {act_p:.1f} - {act_k:.1f}"
                color = "#059669" if act_n >= tn and act_p >= tp and act_k >= tk else "#dc2626"
                st.markdown(f"""
                <div class="metric-box">
                    <div class="metric-label">Actual Grade</div>
                    <div class="metric-value" style="color:{color}">{grade_str}</div>
                    <div class="metric-sub">Target: {tn}-{tp}-{tk}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- 2. RECIPE TABLE & VISUAL ---
            col_table, col_chart = st.columns([1.5, 1])
            
            with col_table:
                st.subheader("📋 Production Recipe (Batch Sheet)")
                
                # Format DataFrame for Display
                display_df = df[["Material", "Mass (kg)", "% Mix", "Unit Price", "Total Cost (IDR)"]].copy()
                
                st.dataframe(
                    display_df,
                    column_config={
                        "Mass (kg)": st.column_config.NumberColumn(format="%.2f kg"),
                        "% Mix": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                        "Unit Price": st.column_config.NumberColumn(format="Rp %.0f"),
                        "Total Cost (IDR)": st.column_config.NumberColumn(format="Rp %.0f"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
                
                # Filler Check Alert
                filler_mass = df[df["Material"].str.contains("Filler")]["Mass (kg)"].sum()
                if filler_mass > 0:
                    st.success(f"✅ **Filler Optimization:** Successfully utilized {filler_mass:.2f} kg of filler to reduce cost.")
                else:
                    st.warning("⚠️ **No Filler Used:** The target grade is too high (Concentrated). No room for filler.")

            with col_chart:
                st.subheader("Composition")
                
                # Donut Chart (Clean)
                fig = px.pie(df, values='Mass (kg)', names='Material', hole=0.6,
                             color_discrete_sequence=px.colors.sequential.Teal)
                fig.update_traces(textposition='outside', textinfo='percent+label')
                fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=300)
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Total Mass Check
                total_mass = df["Mass (kg)"].sum()
                st.caption(f"Total Batch Mass Check: {total_mass:.2f} kg (Target: 1000 kg)")

        else:
            st.error("❌ **Optimization Failed (Infeasible)**")
            st.error(f"Reason: Tidak mungkin mencapai grade NPK {tn}-{tp}-{tk} dengan bahan baku yang dipilih dalam batasan 1 ton.")
            st.info("💡 **Suggestion:** Coba centang bahan baku dengan kandungan nutrisi lebih tinggi (misal DAP atau Urea), atau kurangi target grade.")

else:
    st.info("👈 Silakan atur Target Grade dan Ketersediaan Bahan Baku di Sidebar, lalu klik Calculate.")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6b7280; font-size: 12px;">
    <b>NPK Process Intelligence</b> | Linear Programming Engine (Simplex Method) <br>
    Material balance strictly enforced at 1000 kg batch basis.
</div>
""", unsafe_allow_html=True)
