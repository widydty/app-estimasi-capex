import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import linprog

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="NPK Profit Optimizer", layout="wide", page_icon="💰")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        .stApp { background-color: #ffffff; font-family: 'Inter', sans-serif; color: #171717; }
        
        /* HEADER */
        h1, h2, h3 { color: #111827; letter-spacing: -0.5px; }
        
        /* METRIC CARDS - THE MONEY SHOT */
        .money-card {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white; padding: 24px; border-radius: 12px;
            box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.2);
            text-align: center;
        }
        .baseline-card {
            background: #f3f4f6; color: #4b5563; padding: 20px;
            border-radius: 12px; border: 1px solid #e5e7eb; text-align: center;
        }
        .metric-val-lg { font-size: 36px; font-weight: 800; }
        .metric-lbl-sm { font-size: 12px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; }
        
        /* SIDEBAR */
        section[data-testid="stSidebar"] { background-color: #fafafa; border-right: 1px solid #e5e7eb; }
        
        /* TABLES */
        div[data-testid="stDataFrame"] { border: 1px solid #e5e7eb; border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE HARGA & SPEK (BISA DIEDIT) ---
# Kita buat harga dinamis agar engineer bisa simulasi harga pasar
if 'prices' not in st.session_state:
    st.session_state.prices = {
        "Urea": 6500, "DAP": 10500, "ZA": 2500, "KCl": 8200, "Clay": 250
    }

# Spesifikasi Nutrisi (BEDP-04)
# Urea(46), DAP(16-45), ZA(21-0-0-24S), KCl(60), Clay(0)
NUTRIENTS = {
    "Urea": {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0},
    "DAP":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0},
    "ZA":   {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0},
    "KCl":  {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0},
    "Clay": {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0}
}

# DATA GUARANTEE (BEDP-02) - Sebagai KOMPARATOR (Baseline Boros)
GUARANTEE_RECIPE = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# --- 3. OPTIMIZATION ENGINE ---
def calculate_lcf(tn, tp, tk, ts, total_mass=1000):
    mats = list(NUTRIENTS.keys())
    n_vars = len(mats)
    
    # Objective: Minimize Cost based on CURRENT prices
    c = [st.session_state.prices[m] for m in mats]
    
    # Constraints
    A_ub = []
    b_ub = []
    
    # Nutrients >= Target
    # Linprog uses <=, so multiply by -1
    A_ub.append([-NUTRIENTS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    
    A_ub.append([-NUTRIENTS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    
    A_ub.append([-NUTRIENTS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-NUTRIENTS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_basis)
    
    # Equality: Total Mass = 1000
    A_eq = [[1.0] * n_vars]
    b_eq = [total_mass]
    
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

# SIDEBAR: MARKET PRICES
with st.sidebar:
    st.title("💲 Market Prices")
    st.caption("Update prices to see savings impact (IDR/kg)")
    
    new_prices = {}
    for mat, price in st.session_state.prices.items():
        new_prices[mat] = st.number_input(f"{mat}", value=price, step=100)
    st.session_state.prices = new_prices
    
    st.markdown("---")
    st.caption("Optimization Engine: Scipy Linear Programming")

# MAIN CONTENT
st.title("NPK Profit Hunter")
st.markdown("### Optimization vs Design Guarantee Comparison")

# 1. SELECT GRADE
c_sel, c_prod = st.columns([1, 2])
with c_sel:
    grade = st.selectbox("Select Production Grade", ["15-15-15", "15-10-12", "16-16-16"])
    
    # Set Targets based on selection
    if grade == "15-15-15": t_n, t_p, t_k, t_s = 15, 15, 15, 2
    elif grade == "15-10-12": t_n, t_p, t_k, t_s = 15, 10, 12, 2
    elif grade == "16-16-16": t_n, t_p, t_k, t_s = 16, 16, 16, 0

with c_prod:
    production_rate = st.number_input("Annual Production Target (Ton/Year)", value=100000, step=10000)

st.markdown("---")

# 2. EXECUTE CALCULATIONS
# A. Hitung Cost Baseline (Guarantee)
guar_recipe = GUARANTEE_RECIPE[grade]
cost_baseline = sum([guar_recipe[m] * st.session_state.prices[m] for m in guar_recipe])
total_mass_guar = sum(guar_recipe.values())

# B. Hitung Cost Optimal (LCF)
res, mat_list = calculate_lcf(t_n, t_p, t_k, t_s)

if res.success:
    opt_masses = res.x
    cost_optimal = res.fun
    
    # Hitung Savings
    saving_per_ton = cost_baseline - cost_optimal
    total_saving_year = saving_per_ton * production_rate
    
    # --- DISPLAY MONEY SHOT ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="baseline-card">
            <div class="metric-lbl-sm">GUARANTEE RECIPE COST</div>
            <div class="metric-val-lg" style="color:#6b7280">Rp {cost_baseline:,.0f}</div>
            <div style="font-size:12px">per Ton Product</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="baseline-card" style="background: #ecfdf5; border-color: #10b981;">
            <div class="metric-lbl-sm" style="color: #047857;">OPTIMIZED LCF COST</div>
            <div class="metric-val-lg" style="color: #059669;">Rp {cost_optimal:,.0f}</div>
            <div style="font-size:12px">per Ton Product</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="money-card">
            <div class="metric-lbl-sm">POTENTIAL PROFIT INCREASE</div>
            <div class="metric-val-lg">Rp {total_saving_year/1e9:,.1f} M</div>
            <div style="font-size:12px">per Year ({production_rate/1000}k Tons)</div>
        </div>
        """, unsafe_allow_html=True)

    # --- DETAILED COMPARISON TABLE ---
    st.subheader("📊 Recipe Breakdown Comparison (kg/ton)")
    
    # Prepare Data
    opt_recipe = dict(zip(mat_list, opt_masses))
    
    comp_data = []
    for mat in NUTRIENTS.keys():
        val_guar = guar_recipe.get(mat, 0)
        val_opt = opt_recipe.get(mat, 0)
        price = st.session_state.prices[mat]
        
        comp_data.append({
            "Raw Material": mat,
            "Guarantee (Design)": val_guar,
            "Optimized (LCF)": val_opt,
            "Delta (kg)": val_opt - val_guar,
            "Cost Impact (Rp)": (val_opt - val_guar) * price
        })
        
    df_comp = pd.DataFrame(comp_data)
    
    # Styling Table
    def color_delta(val):
        color = '#ef4444' if val > 0 else '#10b981' # Merah jika cost naik, Hijau jika hemat
        return f'color: {color}; font-weight: bold;'

    st.dataframe(
        df_comp.style.format("{:.2f}", subset=["Guarantee (Design)", "Optimized (LCF)", "Delta (kg)"])
                 .format("Rp {:,.0f}", subset=["Cost Impact (Rp)"])
                 .applymap(lambda x: "color: red;" if x > 0 else "color: green;", subset=["Cost Impact (Rp)"]),
        use_container_width=True,
        hide_index=True
    )
    
    # --- VISUALIZATION ---
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        # Comparison Bar Chart
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Guarantee', x=df_comp['Raw Material'], y=df_comp['Guarantee (Design)'], marker_color='#9ca3af'))
        fig.add_trace(go.Bar(name='Optimized', x=df_comp['Raw Material'], y=df_comp['Optimized (LCF)'], marker_color='#10b981'))
        fig.update_layout(title="Material Consumption Profile", barmode='group')
        st.plotly_chart(fig, use_container_width=True)
        
    with col_chart2:
        # Waterfall Chart (Savings)
        fig2 = go.Figure(go.Waterfall(
            name = "20", orientation = "v",
            measure = ["relative"] * len(df_comp),
            x = df_comp['Raw Material'],
            textposition = "outside",
            text = [f"{x/1000:.0f}k" for x in df_comp['Cost Impact (Rp)']],
            y = df_comp['Cost Impact (Rp)'],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig2.update_layout(title="Cost Impact per Material (Waterfall)")
        st.plotly_chart(fig2, use_container_width=True)

    # --- ENGINEERING NOTE ---
    st.info(f"""
    💡 **Optimization Insight:**
    Total massa resep optimal adalah **1000 kg** (Basis Teoritis). 
    Sedangkan resep Guarantee totalnya **{total_mass_guar:.1f} kg** (karena ada margin *loss*).
    Penghematan terbesar didapat dari pengurangan *over-formulation* dan pemilihan bahan baku yang tepat sesuai harga pasar saat ini.
    """)

else:
    st.error("Optimization Failed. Check Constraints.")

st.markdown("---")
st.caption("Process Intelligence System | Developed for NPK Granular 3 Project")
