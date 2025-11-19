import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. SYSTEM CONFIGURATION ---
st.set_page_config(
    page_title="NPK OPTIMIZER",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. "100 BILLION" CSS (BLOOMBERG STYLE) ---
st.markdown("""
    <style>
        /* IMPORT HIGH-END FONTS */
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Inter:wght@400;600&display=swap');
        
        /* GLOBAL THEME */
        .stApp {
            background-color: #0e1117; /* Deepest Charcoal */
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
        }
        
        /* REMOVE STREAMLIT DECORATIONS */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* SIDEBAR STYLING */
        section[data-testid="stSidebar"] {
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }
        
        /* TYPOGRAPHY SYSTEM */
        h1, h2, h3 {
            font-family: 'Inter', sans-serif;
            letter-spacing: -0.5px;
            color: #ffffff !important;
        }
        
        .mono-font { font-family: 'JetBrains Mono', monospace; }
        
        /* KPI CARDS (FINTECH STYLE) */
        .kpi-container {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 4px; /* Sharp corners */
            padding: 20px;
            margin-bottom: 20px;
        }
        .kpi-label {
            font-family: 'JetBrains Mono', monospace;
            font-size: 10px;
            text-transform: uppercase;
            color: #8b949e;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }
        .kpi-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }
        .kpi-delta-pos { color: #3fb950; font-size: 12px; } /* Terminal Green */
        .kpi-delta-neg { color: #f85149; font-size: 12px; } /* Terminal Red */
        
        /* TABLE STYLING (DATA DENSE) */
        div[data-testid="stDataFrame"] {
            background-color: #161b22;
            border: 1px solid #30363d;
        }
        
        /* BUTTONS (TACTILE) */
        .stButton>button {
            background-color: #238636; /* GitHub Green */
            color: white;
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-size: 12px;
            padding: 0.75rem 1rem;
            transition: all 0.2s;
        }
        .stButton>button:hover {
            background-color: #2ea043;
            border-color: #ffffff;
        }
        
        /* INPUT FIELDS */
        .stNumberInput input {
            background-color: #0d1117;
            color: white;
            font-family: 'JetBrains Mono', monospace;
            border: 1px solid #30363d;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE (STANDARDIZED KEYS) ---
# PENTING: Kunci di sini harus sama persis antara RAW_MATS dan GUARANTEE_REF
RAW_MATS = {
    "Urea": {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Source", "Price": 6500},
    "ZA":   {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0, "Type": "Source", "Price": 2500},
    "DAP":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "Type": "Source", "Price": 10500},
    "KCl":  {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "Type": "Source", "Price": 8200},
    "Clay": {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Filler", "Price": 250}
}

GUARANTEE_REF = {
    "15-15-15": {"Urea": 173.1, "DAP": 343.3, "KCl": 257.5, "ZA": 94.9, "Clay": 161.2},
    "15-10-12": {"Urea": 215.3, "DAP": 228.9, "KCl": 206.0, "ZA": 89.8, "Clay": 290.0},
    "16-16-16": {"Urea": 230.9, "DAP": 366.3, "KCl": 274.7, "ZA": 0.0,  "Clay": 158.2}
}

# --- 4. CALCULATION ENGINE ---
def run_optimization(tn, tp, tk, ts, prices):
    mats = list(RAW_MATS.keys())
    n_vars = len(mats)
    total_mass = 1000.0
    
    # Objective: Minimize Cost
    c = [prices[m] for m in mats]
    
    # Constraints
    A_ub, b_ub = [], []
    
    # Nutrient Targets (Min %)
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # Engineering Limit: Filler Max 30% (Process Feasibility)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0)

    # Equality: Total Mass = 1000
    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 5. DASHBOARD LAYOUT ---

# SIDEBAR CONTROLS
with st.sidebar:
    st.markdown("<h3 style='font-size:14px; color:#8b949e; letter-spacing:1px;'>CONFIGURATION</h3>", unsafe_allow_html=True)
    
    grade_sel = st.selectbox("TARGET GRADE", ["15-15-15", "15-10-12", "16-16-16"])
    
    # Logic Preset Values
    if grade_sel == "15-15-15": v = (15,15,15,2)
    elif grade_sel == "15-10-12": v = (15,10,12,2)
    else: v = (16,16,16,0)
    
    st.markdown("<div style='margin-top:20px; margin-bottom:5px; font-size:11px; color:#8b949e;'>NUTRIENT SPECIFICATION (%)</div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    tn = c1.number_input("N", value=float(v[0]))
    tp = c2.number_input("P", value=float(v[1]))
    tk = c1.number_input("K", value=float(v[2]))
    ts = c2.number_input("S", value=float(v[3]))
    
    st.markdown("<div style='margin-top:20px; margin-bottom:5px; font-size:11px; color:#8b949e;'>MARKET PRICES (IDR/KG)</div>", unsafe_allow_html=True)
    curr_prices = {}
    for m, p in RAW_MATS.items():
        curr_prices[m] = st.number_input(f"{m}", value=p["Price"], step=50)
        
    st.markdown("---")
    run_btn = st.button("RUN SIMULATION")

# MAIN CONTENT
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #30363d; padding-bottom:20px; margin-bottom:20px;">
    <div>
        <h2 style="margin:0; font-size:24px;">NPK PRODUCTION INTELLIGENCE</h2>
        <span style="color:#8b949e; font-size:12px; font-family:'JetBrains Mono';">SYSTEM STATUS: ONLINE | MODE: COST OPTIMIZATION</span>
    </div>
    <div style="text-align:right;">
        <span style="background:#238636; color:white; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold;">LIVE</span>
    </div>
</div>
""", unsafe_allow_html=True)

if run_btn:
    res, mat_list = run_optimization(tn, tp, tk, ts, curr_prices)
    
    if res.success:
        # PROCESSING DATA
        masses = res.x
        df = pd.DataFrame({"Material": mat_list, "Mass": masses})
        df = df[df["Mass"] > 0.01].sort_values("Mass", ascending=False) # Filter small values
        df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        df["Mix"] = (df["Mass"] / 1000) * 100
        
        total_cost_opt = df["Cost"].sum()
        
        # BENCHMARK LOGIC (FIXED KEYERROR)
        guar_recipe = GUARANTEE_REF.get(grade_sel, {})
        # Menggunakan .get(m, 0) untuk safety jika nama material beda
        total_cost_guar = sum([qty * curr_prices.get(m, 0) for m, qty in guar_recipe.items()])
        
        saving = total_cost_guar - total_cost_opt
        is_profit = saving >= 0
        
        # --- METRIC ROW ---
        c1, c2, c3 = st.columns(3)
        
        # 1. Cost Metric
        c1.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">OPTIMIZED COGS (RAW MATERIAL)</div>
            <div class="kpi-value">Rp {total_cost_opt:,.0f}</div>
            <div style="font-family:'JetBrains Mono'; font-size:12px; color:#8b949e; margin-top:5px;">PER METRIC TON</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Savings Metric
        delta_color = "kpi-delta-pos" if is_profit else "kpi-delta-neg"
        sign = "+" if is_profit else ""
        
        c2.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">MARGIN IMPACT VS DESIGN</div>
            <div class="kpi-value" style="color:{'#3fb950' if is_profit else '#f85149'};">{sign} Rp {saving:,.0f}</div>
            <div class="{delta_color}">{'PROFITABLE' if is_profit else 'OVERRUN'}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. Unit Cost
        c3.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-label">UNIT COST (50KG BAG)</div>
            <div class="kpi-value">Rp {total_cost_opt/20:,.0f}</div>
            <div style="font-family:'JetBrains Mono'; font-size:12px; color:#8b949e; margin-top:5px;">EXCL. PACKAGING</div>
        </div>
        """, unsafe_allow_html=True)
        
        # --- CHARTS ROW ---
        col_chart, col_table = st.columns([1, 2])
        
        with col_chart:
            st.markdown("<h4 style='font-size:14px; color:#8b949e;'>COMPOSITION BREAKDOWN</h4>", unsafe_allow_html=True)
            
            # Dark Theme Donut Chart
            colors = ['#238636', '#1f6feb', '#a371f7', '#d29922', '#f85149']
            fig = go.Figure(data=[go.Pie(
                labels=df['Material'], 
                values=df['Mass'], 
                hole=.7,
                marker=dict(colors=colors, line=dict(color='#0d1117', width=2)),
                textinfo='percent',
                textfont=dict(family='JetBrains Mono', color='white')
            )])
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                margin=dict(t=0, b=0, l=0, r=0),
                height=250,
                annotations=[dict(text='MIX', x=0.5, y=0.5, font_size=20, showarrow=False, font_color='white')]
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_table:
            st.markdown("<h4 style='font-size:14px; color:#8b949e;'>PRODUCTION RECIPE (1000 KG BASIS)</h4>", unsafe_allow_html=True)
            
            # Table Configuration
            st.dataframe(
                df[["Material", "Mass", "Mix", "Price", "Cost"]],
                column_config={
                    "Material": st.column_config.TextColumn("MATERIAL", width="medium"),
                    "Mass": st.column_config.NumberColumn("MASS (KG)", format="%.2f"),
                    "Mix": st.column_config.ProgressColumn("RATIO", format="%.1f%%", min_value=0, max_value=100),
                    "Price": st.column_config.NumberColumn("PRICE/KG", format="Rp %.0f"),
                    "Cost": st.column_config.NumberColumn("TOTAL", format="Rp %.0f"),
                },
                use_container_width=True,
                hide_index=True
            )
        
        # --- NUTRIENT VALIDATION (WATERFALL) ---
        st.markdown("---")
        st.markdown("<h4 style='font-size:14px; color:#8b949e;'>NUTRIENT COMPLIANCE AUDIT</h4>", unsafe_allow_html=True)
        
        # Calc Actuals
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        # Modern Bar Chart (Dark Mode)
        nutrients = ['Nitrogen (N)', 'Phosphate (P)', 'Potash (K)', 'Sulfur (S)']
        targets = [tn, tp, tk, ts]
        actuals = [act_n, act_p, act_k, act_s]
        
        fig_bar = go.Figure()
        
        # Target Bars (Grey Outline)
        fig_bar.add_trace(go.Bar(
            name='TARGET MINIMUM', x=nutrients, y=targets,
            marker_color='rgba(255,255,255,0.1)', 
            marker_line=dict(color='#8b949e', width=1),
            text=[f"{x}%" for x in targets], textposition='auto'
        ))
        
        # Actual Bars (Solid Color)
        fig_bar.add_trace(go.Bar(
            name='OPTIMIZED ACTUAL', x=nutrients, y=actuals,
            marker_color='#238636', 
            text=[f"{x:.2f}%" for x in actuals], textposition='auto'
        ))
        
        fig_bar.update_layout(
            barmode='group',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='JetBrains Mono', color='#e2e8f0'),
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
            yaxis=dict(showgrid=True, gridcolor='#30363d'),
            legend=dict(orientation="h", y=1.1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    else:
        st.error("INFEASIBLE SOLUTION: The selected constraints cannot be met with current materials.")

else:
    # INITIAL STATE
    st.info("SYSTEM READY. PLEASE INITIATE SIMULATION FROM SIDEBAR.")
