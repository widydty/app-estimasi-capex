import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. SETUP HALAMAN & TEMA PREMIUM ---
st.set_page_config(page_title="NPK OPTIMIZER PRO", layout="wide", page_icon="💎")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        
        /* RESET & BASE */
        .stApp {
            background-color: #f8fafc;
            font-family: 'Plus Jakarta Sans', sans-serif;
            color: #0f172a;
        }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] {
            background-color: white;
            border-right: 1px solid #e2e8f0;
        }
        
        /* 3D CARDS (NEUMORPHISM STYLE) */
        .card-3d {
            background: white;
            border-radius: 16px;
            padding: 24px;
            border: 1px solid #f1f5f9;
            box-shadow: 
                0 4px 6px -1px rgba(0, 0, 0, 0.05), 
                0 10px 15px -3px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s;
            height: 100%;
        }
        .card-3d:hover {
            transform: translateY(-2px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }
        
        /* SAVINGS CARD (HIGHLIGHT) */
        .card-profit {
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            color: white;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 20px -5px rgba(15, 23, 42, 0.3);
            position: relative;
            overflow: hidden;
        }
        .card-profit::after {
            content: "";
            position: absolute;
            top: 0; right: 0; bottom: 0; left: 0;
            background: radial-gradient(circle at top right, rgba(255,255,255,0.1), transparent 70%);
        }

        /* TYPOGRAPHY */
        .label-text {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #64748b;
            margin-bottom: 8px;
        }
        .profit-label {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #94a3b8; /* Light grey for dark bg */
            margin-bottom: 8px;
            z-index: 2; position: relative;
        }
        .value-text {
            font-size: 28px;
            font-weight: 800;
            color: #0f172a;
            letter-spacing: -0.02em;
        }
        .profit-value {
            font-size: 32px;
            font-weight: 800;
            color: #ffffff;
            z-index: 2; position: relative;
        }
        .sub-text { font-size: 13px; color: #94a3b8; font-weight: 500; margin-top: 4px; }
        
        /* CUSTOM TABLE */
        div[data-testid="stDataFrame"] {
            background: white;
            padding: 5px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        }
        
        /* BUTTONS */
        .stButton>button {
            background-color: #2563eb;
            color: white;
            border-radius: 10px;
            padding: 0.6rem 1rem;
            font-weight: 600;
            border: none;
            width: 100%;
            transition: background 0.2s;
        }
        .stButton>button:hover { background-color: #1d4ed8; }

        h1, h2, h3 { color: #0f172a !important; letter-spacing: -0.5px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & PARAMETERS ---
# Harga Default (Bisa diedit user di sidebar)
DEFAULT_PRICES = {
    "Urea": 6500, "ZA": 2500, "DAP": 10500, "KCl": 8200, "Clay": 250
}

# Komposisi Nutrisi (BEDP-04)
RAW_MATS = {
    "Urea": {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Source"},
    "ZA":   {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0, "Type": "Source"},
    "DAP":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "Type": "Source"},
    "KCl":  {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "Type": "Source"},
    "Clay": {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Filler"}
}

# Resep Jaminan (BEDP-02) - Baseline
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
    
    # Objective: Minimize Cost
    c = [prices[m] for m in mats]
    
    # Constraints
    A_ub, b_ub = [], []
    
    # Nutrient Targets (Min %) -> Scipy uses <= so multiply by -1
    # Example: N >= 15%  -->  -N <= -15%
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
    
    # Engineering Constraint: Batasi Filler Maks 300kg (Agar granulasi bagus)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    A_ub.append(filler_row)
    b_ub.append(300.0)

    # Equality: Total Mass = 1000
    A_eq = [[1.0] * n_vars]
    b_eq = [total_mass]
    
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

# Sidebar
with st.sidebar:
    st.header("🎛️ Configuration")
    
    # 1. Grade
    grade = st.selectbox("Target Grade", ["15-15-15", "15-10-12", "16-16-16"])
    
    # Presets
    if grade == "15-15-15": defs = (15,15,15,2)
    elif grade == "15-10-12": defs = (15,10,12,2)
    else: defs = (16,16,16,0)
    
    col1, col2 = st.columns(2)
    tn = col1.number_input("N", value=float(defs[0]))
    tp = col2.number_input("P", value=float(defs[1]))
    tk = col1.number_input("K", value=float(defs[2]))
    ts = col2.number_input("S", value=float(defs[3]))
    
    st.markdown("---")
    st.subheader("💲 Market Prices")
    
    curr_prices = {}
    for m, p in DEFAULT_PRICES.items():
        curr_prices[m] = st.number_input(f"{m} (Rp/kg)", value=p, step=100)
        
    st.markdown("---")
    calc_btn = st.button("RUN OPTIMIZATION", type="primary")

# Main Content
st.markdown("## 🏭 NPK Production Intelligence")
st.markdown(f"Optimization Target: **NPK {tn}-{tp}-{tk}-{ts}S** | Basis: **1 Metric Ton**")
st.markdown("---")

if calc_btn:
    res, mat_list = run_optimization(tn, tp, tk, ts, curr_prices)
    
    if res.success:
        # --- DATA PROCESSING ---
        opt_mass = res.x
        df = pd.DataFrame({"Material": mat_list, "Mass (kg)": opt_mass})
        df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
        df["Cost"] = df["Mass (kg)"] * df["Price"]
        df = df[df["Mass (kg)"] > 0.1].sort_values("Mass (kg)", ascending=False) # Clean zeros
        
        total_cost_opt = df["Cost"].sum()
        
        # Calculate Baseline (Guarantee) Cost
        guar_recipe = GUARANTEE_REF[grade]
        total_cost_guar = sum([qty * curr_prices[m] for m, qty in guar_recipe.items()])
        total_mass_guar = sum(guar_recipe.values())
        
        # Calculate Savings
        saving = total_cost_guar - total_cost_opt
        is_saving = saving >= 0
        
        # --- ROW 1: METRIC CARDS (3D DESIGN) ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="card-3d">
                <div class="label-text">Optimized Cost (COGS)</div>
                <div class="value-text">Rp {total_cost_opt/1e6:,.2f} Jt</div>
                <div class="sub-text">Per Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="card-3d">
                <div class="label-text">Baseline Cost (Guarantee)</div>
                <div class="value-text">Rp {total_cost_guar/1e6:,.2f} Jt</div>
                <div class="sub-text">Based on BEDP Recipe ({total_mass_guar:.0f} kg)</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            # Profit Logic Visualization
            color_txt = "#ffffff"
            desc_txt = "Optimization Successful" if is_saving else "Review Constraints"
            
            st.markdown(f"""
            <div class="card-profit">
                <div class="profit-label">Potential Savings</div>
                <div class="profit-value">Rp {saving:,.0f}</div>
                <div class="sub-text" style="color:rgba(255,255,255,0.8)">{desc_txt} per Ton</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # --- ROW 2: GRAPHICS & TABLE ---
        col_viz, col_data = st.columns([1, 1])
        
        with col_viz:
            st.markdown("#### Nutrient Validation")
            # Calculate Actuals
            act_n = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
            act_p = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
            act_k = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
            act_s = sum(row["Mass (kg)"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
            
            # Modern Bar Chart
            fig_bar = go.Figure()
            nutrients = ['Nitrogen', 'Phosphate', 'Potash', 'Sulfur']
            targets = [tn, tp, tk, ts]
            actuals = [act_n, act_p, act_k, act_s]
            
            fig_bar.add_trace(go.Bar(
                name='Target Spec', x=nutrients, y=targets,
                marker_color='#cbd5e1', width=0.3
            ))
            fig_bar.add_trace(go.Bar(
                name='Achieved', x=nutrients, y=actuals,
                marker_color='#3b82f6', width=0.3,
                text=[f"{x:.1f}%" for x in actuals], textposition='auto'
            ))
            
            fig_bar.update_layout(
                barmode='group',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                height=350,
                yaxis=dict(showgrid=True, gridcolor='#e2e8f0'),
                legend=dict(orientation="h", y=1.1)
            )
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_data:
            st.markdown("#### Optimized Recipe Structure")
            
            # Donut Chart
            fig_pie = go.Figure(data=[go.Pie(
                labels=df['Material'], 
                values=df['Mass (kg)'], 
                hole=.6,
                textinfo='percent',
                marker=dict(colors=['#3b82f6', '#0ea5e9', '#22c55e', '#f59e0b', '#64748b'])
            )])
            fig_pie.update_layout(
                showlegend=True, 
                height=350, 
                margin=dict(t=0, b=0, l=0, r=0),
                legend=dict(orientation="v", y=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- ROW 3: DATA TABLE ---
        st.markdown("#### Production Batch Sheet (1 Ton)")
        
        # Format DataFrame for Display
        df_display = df.copy()
        df_display["Mix %"] = (df_display["Mass (kg)"] / 1000) * 100
        
        st.dataframe(
            df_display[["Material", "Mass (kg)", "Mix %", "Price", "Cost"]],
            column_config={
                "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                "Mass (kg)": st.column_config.NumberColumn(format="%.2f kg"),
                "Mix %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
                "Price": st.column_config.NumberColumn(format="Rp %.0f"),
                "Cost": st.column_config.NumberColumn("Subtotal", format="Rp %.0f"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Engineering Insight
        if is_saving:
            st.success(f"✅ **Optimization Success:** This recipe saves **Rp {saving:,.0f}** per ton compared to the Design Guarantee basis by minimizing excess nutrients and maximizing filler usage.")
        else:
            st.warning("⚠️ **Notice:** Optimized recipe is more expensive. This might be due to current high market prices of specific raw materials required to meet the grade.")

    else:
        st.error("Optimization Infeasible. Please relax constraints or check material availability.")
else:
    st.info("👈 Ready. Adjust prices/grade in sidebar and click 'RUN OPTIMIZATION'.")
