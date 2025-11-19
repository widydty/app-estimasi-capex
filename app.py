import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. CONFIGURATION & STYLE ---
st.set_page_config(page_title="OPTIMUS NPK", layout="wide", page_icon="💠")

# Styling Modern Enterprise (Tanpa HTML Table yang rentan error)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        .stApp { background-color: #f4f6f9; font-family: 'Inter', sans-serif; }
        
        /* Custom Metric Box */
        .metric-box {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border-left: 5px solid #3b82f6;
            transition: transform 0.2s;
        }
        .metric-box:hover { transform: translateY(-2px); }
        .metric-label { color: #64748b; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .metric-value { color: #1e293b; font-size: 32px; font-weight: 800; margin-top: 5px; }
        .metric-sub { color: #94a3b8; font-size: 13px; margin-top: 2px; }
        
        /* Savings Box (Highlight) */
        .savings-box {
            background: linear-gradient(135deg, #059669 0%, #10b981 100%);
            border-radius: 12px;
            padding: 24px;
            color: white;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e2e8f0; }
        
        /* Chart Container */
        .chart-container {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        
        h1, h2, h3 { color: #0f172a !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE ---
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Urea",   "Price": 6500},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"Type": "Salt",   "Price": 2500},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "Type": "Salt",   "Price": 10500},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "Type": "Salt",   "Price": 8200},
    "Clay":         {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Filler", "Price": 250}
}

# Design Guarantee Data (BEDP-02) - Baseline
GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# --- 3. LOGIC ---
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
        
    # Filler Limit
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0)
        
    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

with st.sidebar:
    st.markdown("### 🛠️ Control Panel")
    grade_sel = st.selectbox("Target Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"])
    
    if grade_sel == "15-15-15": def_vals = (15.0, 15.0, 15.0, 2.0)
    elif grade_sel == "15-10-12": def_vals = (15.0, 10.0, 12.0, 2.0)
    elif grade_sel == "16-16-16": def_vals = (16.0, 16.0, 16.0, 0.0)
    else: def_vals = (15.0, 15.0, 15.0, 0.0)
    
    col1, col2 = st.columns(2)
    tn = col1.number_input("N %", value=def_vals[0])
    tp = col2.number_input("P %", value=def_vals[1])
    tk = col1.number_input("K %", value=def_vals[2])
    ts = col2.number_input("S %", value=def_vals[3])
    
    st.markdown("---")
    st.markdown("### 💵 Market Prices")
    current_prices = {}
    for m, data in RAW_MATS.items():
        current_prices[m] = st.number_input(f"{m}", value=data["Price"], step=100)
        
    st.markdown("---")
    run = st.button("RUN OPTIMIZATION", type="primary", use_container_width=True)

# HEADER
st.title("OPTIMUS NPK Intelligence")
st.markdown(f"**Optimization Target:** NPK {tn}-{tp}-{tk}-{ts}S | **Basis:** 1.000 kg")
st.markdown("---")

if run:
    res, mat_order = calculate_optimization(tn, tp, tk, ts, list(RAW_MATS.keys()), current_prices)
    
    if res.success:
        # Process Results
        masses = res.x
        df = pd.DataFrame({"Material": mat_order, "Mass": masses})
        df = df[df["Mass"] > 0.1].sort_values("Mass", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: current_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        df["Mix"] = (df["Mass"] / 1000) * 100
        
        total_cost = df["Cost"].sum()
        
        # Calculate Savings vs Guarantee
        savings_text = "N/A"
        is_saving = False
        saving_val = 0
        
        if grade_sel in GUARANTEE_REF:
            guar_recipe = GUARANTEE_REF[grade_sel]
            base_cost = sum([qty * current_prices.get(m, 0) for m, qty in guar_recipe.items() if m in current_prices])
            saving_val = base_cost - total_cost
            is_saving = saving_val > 0
        
        # --- ROW 1: KEY METRICS (CARD DESIGN) ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Cost of Goods (RM)</div>
                <div class="metric-value">Rp {total_cost/1e6:.2f} M</div>
                <div class="metric-sub">Per Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-label">Unit Cost (Bag)</div>
                <div class="metric-value">Rp {total_cost/20:,.0f}</div>
                <div class="metric-sub">Per 50kg Bag</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            # Savings Box Highlight
            bg_color = "linear-gradient(135deg, #059669 0%, #10b981 100%)" if is_saving else "#64748b"
            sign = "+" if is_saving else ""
            st.markdown(f"""
            <div class="savings-box" style="background: {bg_color};">
                <div style="font-size:12px; font-weight:600; text-transform:uppercase; opacity:0.9;">Potential Profit Increase</div>
                <div style="font-size:32px; font-weight:800; margin-top:5px;">{sign}Rp {saving_val/1000:,.0f} k</div>
                <div style="font-size:13px; opacity:0.9;">Savings per Ton vs Guarantee</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ROW 2: TABLE & COMPOSITION ---
        col_tbl, col_pie = st.columns([2, 1])
        
        with col_tbl:
            st.subheader("📋 Optimized Recipe")
            # Gunakan st.dataframe dengan column_config (Lebih stabil daripada HTML)
            st.dataframe(
                df[["Material", "Mass", "Mix", "Price", "Cost"]],
                column_config={
                    "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                    "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                    "Mix": st.column_config.ProgressColumn("Mix %", format="%.1f%%", min_value=0, max_value=100),
                    "Price": st.column_config.NumberColumn("Unit Price", format="Rp %.0f"),
                    "Cost": st.column_config.NumberColumn("Total Cost", format="Rp %.0f"),
                },
                use_container_width=True,
                hide_index=True
            )
            
        with col_pie:
            st.subheader("Composition")
            fig_pie = px.pie(df, values='Mass', names='Material', hole=0.6, 
                             color_discrete_sequence=px.colors.sequential.RdBu)
            fig_pie.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 3: NUTRIENT VALIDATION (RADAR CHART / BAR) ---
        st.subheader("🛡️ Nutrient Quality Validation")
        
        # Calculate Actuals
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        # Create Grouped Bar Chart (Clean & Professional)
        fig_val = go.Figure()
        
        nutrients = ['Nitrogen (N)', 'Phosphate (P)', 'Potash (K)', 'Sulfur (S)']
        targets = [tn, tp, tk, ts]
        actuals = [act_n, act_p, act_k, act_s]
        
        fig_val.add_trace(go.Bar(
            name='Target Spec', x=nutrients, y=targets,
            marker_color='#cbd5e1', text=targets, textposition='auto'
        ))
        fig_val.add_trace(go.Bar(
            name='Achieved (Optimized)', x=nutrients, y=actuals,
            marker_color='#0f172a', text=[f"{x:.2f}" for x in actuals], textposition='auto'
        ))
        
        fig_val.update_layout(
            barmode='group',
            plot_bgcolor='white',
            height=350,
            yaxis_title="Percentage (%)",
            margin=dict(t=20, b=20, l=20, r=20),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
        )
        st.plotly_chart(fig_val, use_container_width=True)
        
    else:
        st.error("Optimization Failed: Constraints cannot be met with current materials.")

else:
    st.info("Ready to optimize. Adjust settings in sidebar.")
