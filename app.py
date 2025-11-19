import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. CONFIGURATION & CLEAN CSS ---
st.set_page_config(page_title="NPK Optimizer", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
        /* IMPORT FONT INTER (Standard Corporate Font) */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* RESET STYLING */
        .stApp {
            background-color: #ffffff;
            font-family: 'Inter', sans-serif;
            color: #1e293b; /* Slate 800 */
        }
        
        /* SIDEBAR - Soft Grey */
        section[data-testid="stSidebar"] {
            background-color: #f8fafc; /* Slate 50 */
            border-right: 1px solid #e2e8f0;
        }
        
        /* HEADERS */
        h1, h2, h3 {
            color: #0f172a !important; /* Slate 900 */
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        
        /* KPI CARDS (Clean & Shadowless/Micro-border) */
        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 10px;
        }
        .kpi-label {
            font-size: 12px;
            font-weight: 600;
            color: #64748b; /* Slate 500 */
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
            margin-top: 4px;
        }
        .kpi-sub {
            font-size: 13px;
            color: #64748b;
            margin-top: 4px;
        }
        
        /* PROFIT HIGHLIGHT (Subtle & Classy) */
        .profit-card {
            background-color: #eff6ff; /* Blue 50 */
            border: 1px solid #bfdbfe; /* Blue 200 */
            border-radius: 8px;
            padding: 20px;
        }
        .profit-val {
            font-size: 28px;
            font-weight: 700;
            color: #1d4ed8; /* Blue 700 */
        }
        
        /* CUSTOM TABLE HEADER */
        thead tr th:first-child {display:none}
        tbody th {display:none}
        
        div[data-testid="stDataFrame"] {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }

        /* BUTTONS */
        .stButton>button {
            background-color: #0f172a; /* Black/Slate 900 */
            color: white;
            border-radius: 6px;
            font-weight: 500;
            border: none;
            padding: 0.5rem 1rem;
            transition: background 0.2s;
        }
        .stButton>button:hover {
            background-color: #334155;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (STANDARDIZED NAMES) ---
# Pastikan nama di sini SAMA PERSIS di semua tempat
RAW_MATS = {
    "Urea": {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Source", "Price": 6500},
    "ZA":   {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0, "Type": "Source", "Price": 2500},
    "DAP":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "Type": "Source", "Price": 10500},
    "KCl":  {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "Type": "Source", "Price": 8200},
    "Clay": {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Filler", "Price": 250}
}

# Data Jaminan (Baseline) - Nama kunci harus sama dengan RAW_MATS
GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# --- 3. LOGIC ENGINE ---
def run_optimization(tn, tp, tk, ts, prices):
    mats = list(RAW_MATS.keys())
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    
    A_ub, b_ub = [], []
    
    # Constraints (Nutrients >= Target) -> multiply by -1 for <=
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # Filler Constraint (Max 300kg)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0)

    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

# SIDEBAR
with st.sidebar:
    st.markdown("### 🛠️ Settings")
    
    grade_sel = st.selectbox("Target Grade", ["15-15-15", "15-10-12", "16-16-16"])
    
    if grade_sel == "15-15-15": defs = (15,15,15,2)
    elif grade_sel == "15-10-12": defs = (15,10,12,2)
    else: defs = (16,16,16,0)
    
    st.markdown("#### Nutrient Specs (%)")
    c1, c2 = st.columns(2)
    tn = c1.number_input("N", value=float(defs[0]))
    tp = c2.number_input("P", value=float(defs[1]))
    tk = c1.number_input("K", value=float(defs[2]))
    ts = c2.number_input("S", value=float(defs[3]))
    
    st.markdown("#### Market Prices (IDR)")
    curr_prices = {}
    for m, p in RAW_MATS.items():
        curr_prices[m] = st.number_input(f"{m}", value=p["Price"], step=100)
        
    st.markdown("---")
    run_btn = st.button("Calculate Optimization")

# MAIN CONTENT
st.markdown("## NPK Production Intelligence System")
st.markdown(f"Optimization Target: **NPK {tn}-{tp}-{tk}-{ts}S** | Basis: **1 Metric Ton**")
st.markdown("---")

if run_btn:
    res, mat_list = run_optimization(tn, tp, tk, ts, curr_prices)
    
    if res.success:
        # DATA PROCESSING
        masses = res.x
        df = pd.DataFrame({"Material": mat_list, "Mass": masses})
        df = df[df["Mass"] > 0.01].sort_values("Mass", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        
        total_cost_opt = df["Cost"].sum()
        
        # BASELINE COMPARISON (GUARANTEE)
        # Menggunakan .get() untuk menghindari KeyError jika nama tidak cocok
        guar_recipe = GUARANTEE_REF.get(grade_sel, {})
        
        # Hitung cost guarantee dengan harga saat ini
        total_cost_guar = 0
        for mat, qty in guar_recipe.items():
            price = curr_prices.get(mat, 0) # Jika material tidak ada di input, harga 0
            total_cost_guar += qty * price
            
        saving = total_cost_guar - total_cost_opt
        
        # --- KPI CARDS (CLEAN STYLE) ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Optimized COGS</div>
                <div class="kpi-value">Rp {total_cost_opt/1e6:,.2f} M</div>
                <div class="kpi-sub">Per Metric Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Design Baseline</div>
                <div class="kpi-value" style="color:#64748b">Rp {total_cost_guar/1e6:,.2f} M</div>
                <div class="kpi-sub">Based on Guarantee Recipe</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            # Logic Warna: Hijau jika untung, Merah jika rugi
            color = "#1d4ed8" if saving >= 0 else "#ef4444"
            bg_class = "profit-card"
            sign = "+" if saving >= 0 else ""
            label = "Potential Profit Increase" if saving >= 0 else "Cost Overrun"
            
            st.markdown(f"""
            <div class="{bg_class}" style="border-color:{color}; background-color:{'#eff6ff' if saving >= 0 else '#fef2f2'}">
                <div class="kpi-label" style="color:{color}">{label}</div>
                <div class="profit-val" style="color:{color}">{sign} Rp {saving:,.0f}</div>
                <div class="kpi-sub" style="color:{color}">Vs Design Guarantee</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- CHARTS & TABLES ---
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("##### 📋 Optimized Batch Recipe")
            
            # Clean Table Format
            df_show = df.copy()
            df_show["Mix Ratio"] = df_show["Mass"] / 10
            
            st.dataframe(
                df_show[["Material", "Mass", "Mix Ratio", "Price", "Cost"]],
                column_config={
                    "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                    "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                    "Mix Ratio": st.column_config.ProgressColumn("Mix %", format="%.1f%%", min_value=0, max_value=100),
                    "Price": st.column_config.NumberColumn("Unit Price", format="Rp %.0f"),
                    "Cost": st.column_config.NumberColumn("Total Cost", format="Rp %.0f"),
                },
                use_container_width=True,
                hide_index=True
            )
            
        with col2:
            st.markdown("##### Material Composition")
            # Clean Donut Chart (No childish colors)
            # Corporate Colors: Navy, Blue, Teal, Slate, Grey
            corp_colors = ['#0f172a', '#3b82f6', '#14b8a6', '#64748b', '#cbd5e1']
            
            fig = go.Figure(data=[go.Pie(
                labels=df['Material'], values=df['Mass'], hole=.6,
                marker=dict(colors=corp_colors),
                textinfo='percent'
            )])
            fig.update_layout(
                showlegend=True, 
                margin=dict(t=0, b=0, l=0, r=0),
                height=250,
                legend=dict(orientation="h", y=-0.2)
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- VALIDATION CHART (CLEAN BAR) ---
        st.markdown("---")
        st.markdown("##### 🛡️ Nutrient Validation")
        
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        labels = ['Nitrogen', 'Phosphate', 'Potash', 'Sulfur']
        targets = [tn, tp, tk, ts]
        actuals = [act_n, act_p, act_k, act_s]
        
        fig_bar = go.Figure()
        
        # Target (Outline/Grey)
        fig_bar.add_trace(go.Bar(
            name='Target Spec', x=labels, y=targets,
            marker_color='#e2e8f0', text=targets, textposition='auto',
            textfont=dict(color='#64748b')
        ))
        
        # Actual (Solid Navy)
        fig_bar.add_trace(go.Bar(
            name='Achieved', x=labels, y=actuals,
            marker_color='#0f172a', text=[f"{x:.1f}" for x in actuals], textposition='auto'
        ))
        
        fig_bar.update_layout(
            barmode='group',
            plot_bgcolor='white',
            height=300,
            margin=dict(t=10, b=10, l=10, r=10),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.error("Optimization Infeasible: Constraints cannot be met with selected materials.")

else:
    st.info("Select Grade and Prices on the Sidebar, then click 'Calculate Optimization'.")
