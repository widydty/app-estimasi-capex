import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px  # INI YANG DULU HILANG/ERROR
from scipy.optimize import linprog

# --- 1. CONFIGURATION & 3D STYLING ---
st.set_page_config(page_title="Optimalisasi Formula NPK", layout="wide", page_icon="💎")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&display=swap');
        
        /* BACKGROUND: Soft Gradient (Premium Feel) */
        .stApp {
            background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
            font-family: 'Manrope', sans-serif;
            color: #1f2937;
        }
        
        /* 3D CARD STYLE (GLASS + SHADOW) */
        .card-3d {
            background: rgba(255, 255, 255, 0.8);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 
                0 4px 6px -1px rgba(0, 0, 0, 0.1), 
                0 2px 4px -1px rgba(0, 0, 0, 0.06),
                inset 0 1px 0 rgba(255, 255, 255, 0.5); /* Inner Highlight */
            transition: transform 0.2s;
            margin-bottom: 20px;
        }
        .card-3d:hover {
            transform: translateY(-3px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }
        
        /* HIGHLIGHT CARD (Gradient) */
        .card-highlight {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        /* Efek Kilau pada Card */
        .card-highlight::before {
            content: "";
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 60%);
            transform: rotate(30deg);
        }

        /* TYPOGRAPHY */
        h1, h2, h3 { color: #111827 !important; font-weight: 800 !important; letter-spacing: -0.5px; }
        .metric-label { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; opacity: 0.6; margin-bottom: 5px; }
        .metric-value { font-size: 32px; font-weight: 800; margin-bottom: 0; }
        .metric-sub { font-size: 13px; opacity: 0.8; margin-top: 4px; font-weight: 500; }
        
        /* TABLE CLEANUP */
        div[data-testid="stDataFrame"] {
            background: white;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e5e7eb; }
        
        /* BUTTONS */
        .stButton>button {
            background: linear-gradient(90deg, #2563eb 0%, #3b82f6 100%);
            color: white; border: none; border-radius: 8px; font-weight: 600;
            box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (BEDP SPEC) ---
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Urea",   "Price": 6500},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"Type": "Salt",   "Price": 2500},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "Type": "Salt",   "Price": 10500},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "Type": "Salt",   "Price": 8200},
    "Clay":         {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Filler", "Price": 250}
}

GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# --- 3. LOGIC ENGINE ---
def calculate_optimization(tn, tp, tk, ts, selected_mats, prices):
    mats = list(selected_mats)
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    
    A_ub, b_ub = [], []
    
    # Nutrients Constraints (Multiply by -1 because linprog uses <=)
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # Limit Filler to 30% (Engineering Constraint)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0)
        
    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI ---
with st.sidebar:
    st.header("🎛️ Control Panel")
    grade_sel = st.selectbox("Target Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"])
    
    # Presets
    if grade_sel == "15-15-15": defs = (15.0, 15.0, 15.0, 2.0)
    elif grade_sel == "15-10-12": defs = (15.0, 10.0, 12.0, 2.0)
    elif grade_sel == "16-16-16": defs = (16.0, 16.0, 16.0, 0.0)
    else: defs = (15.0, 15.0, 15.0, 0.0)
    
    col1, col2 = st.columns(2)
    tn = col1.number_input("N %", value=defs[0])
    tp = col2.number_input("P %", value=defs[1])
    tk = col1.number_input("K %", value=defs[2])
    ts = col2.number_input("S %", value=defs[3])
    
    st.markdown("---")
    st.subheader("💲 Market Prices (IDR/kg)")
    current_prices = {}
    for m, data in RAW_MATS.items():
        current_prices[m] = st.number_input(f"{m}", value=data["Price"], step=100)
        
    st.markdown("---")
    run_btn = st.button("RUN OPTIMIZATION", type="primary")

# HEADER
st.title("NPK Intelligent Formulator")
st.markdown(f"**Objective:** Minimize Cost for NPK {tn}-{tp}-{tk}-{ts}S | **Basis:** 1 Metric Ton")
st.markdown("---")

if run_btn:
    res, mat_order = calculate_optimization(tn, tp, tk, ts, list(RAW_MATS.keys()), current_prices)
    
    if res.success:
        # PROCESS DATA
        masses = res.x
        df = pd.DataFrame({"Material": mat_order, "Mass": masses})
        df = df[df["Mass"] > 0.1].sort_values("Mass", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: current_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        df["Mix"] = (df["Mass"] / 1000) * 100
        
        total_cost = df["Cost"].sum()
        
        # CALCULATE SAVINGS VS GUARANTEE
        savings_display = ""
        delta_val = 0
        is_profit = False
        
        if grade_sel in GUARANTEE_REF:
            guar_recipe = GUARANTEE_REF[grade_sel]
            base_cost = sum([qty * current_prices.get(m, 0) for m, qty in guar_recipe.items() if m in current_prices])
            delta_val = base_cost - total_cost
            
            # Logic Formatting Uang (PENTING)
            if delta_val > 0:
                is_profit = True
                savings_display = f"+ Rp {delta_val:,.0f}"
                label_text = "POTENTIAL SAVINGS (PROFIT)"
                sub_text = "Cheaper than Design Guarantee"
            else:
                is_profit = False
                savings_display = f"Rp {delta_val:,.0f}" # Minus sign is automatic
                label_text = "COST OVERRUN (EXPENSIVE)"
                sub_text = "Design Guarantee is currently cheaper"
        else:
            savings_display = "N/A"
            label_text = "COMPARISON"
            sub_text = "No Guarantee Data for Custom Grade"

        # --- ROW 1: 3D METRIC CARDS ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="card-3d">
                <div class="metric-label">Cost of Goods (Raw Material)</div>
                <div class="metric-value">Rp {total_cost/1e6:,.2f} Juta</div>
                <div class="metric-sub">Per Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="card-3d">
                <div class="metric-label">Unit Cost (50kg Bag)</div>
                <div class="metric-value">Rp {total_cost/20:,.0f}</div>
                <div class="metric-sub">Packaging Excluded</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            # Highlight Card Logic
            bg_style = "linear-gradient(135deg, #059669 0%, #10b981 100%)" if is_profit else "linear-gradient(135deg, #dc2626 0%, #ef4444 100%)"
            
            st.markdown(f"""
            <div class="card-highlight" style="background: {bg_style};">
                <div class="metric-label" style="color:rgba(255,255,255,0.8);">{label_text}</div>
                <div class="metric-value" style="color:white;">{savings_display}</div>
                <div class="metric-sub" style="color:rgba(255,255,255,0.8);">{sub_text}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ROW 2: TABLE & CHART ---
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            st.subheader("📋 Production Recipe (BOM)")
            # Gunakan st.dataframe dengan format yang jelas
            st.dataframe(
                df[["Material", "Mass", "Mix", "Price", "Cost"]],
                column_config={
                    "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                    "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                    "Mix": st.column_config.ProgressColumn("Mix Ratio", format="%.1f%%", min_value=0, max_value=100),
                    "Price": st.column_config.NumberColumn("Unit Price", format="Rp %.0f"),
                    "Cost": st.column_config.NumberColumn("Total Cost", format="Rp %.0f"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Tombol Download (Fitur Wajib)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Recipe to CSV", data=csv, file_name="NPK_Recipe.csv", mime="text/csv")

        with col_side:
            st.subheader("Composition Mix")
            # Modern Donut Chart
            fig = go.Figure(data=[go.Pie(
                labels=df['Material'], values=df['Mass'], hole=.5,
                textinfo='percent', hoverinfo='label+value+percent',
                marker=dict(colors=px.colors.qualitative.Prism)
            )])
            fig.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), height=300, paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

        # --- ROW 3: NUTRIENT VALIDATION ---
        st.markdown("---")
        st.subheader("🛡️ Specification Validation")
        
        # Calculate Actuals
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        # Create Clean Bar Chart
        nutrients = ['N', 'P2O5', 'K2O', 'S']
        targets = [tn, tp, tk, ts]
        actuals = [act_n, act_p, act_k, act_s]
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='Target Spec', x=nutrients, y=targets,
            marker_color='#cbd5e1', text=targets, textposition='auto'
        ))
        fig_bar.add_trace(go.Bar(
            name='Achieved', x=nutrients, y=actuals,
            marker_color='#0f172a', text=[f"{x:.1f}" for x in actuals], textposition='auto'
        ))
        fig_bar.update_layout(barmode='group', plot_bgcolor='white', height=300, margin=dict(t=20))
        st.plotly_chart(fig_bar, use_container_width=True)
        
    else:
        st.error("Optimization Infeasible: Check constraints or available materials.")
else:
    st.info("Adjust parameters on the left and click RUN OPTIMIZATION.")
