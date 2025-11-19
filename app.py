import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit_shadcn_ui as ui
from scipy.optimize import linprog

# --- 1. KONFIGURASI HALAMAN (SHADCN STYLE) ---
st.set_page_config(page_title="NPK Formulator", layout="wide", page_icon="⚫")

# CSS INJECTION: MENIRU GAYA "VERCEL / SHADCN"
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&display=swap');
        
        /* BASE RESET */
        .stApp {
            background-color: #ffffff; /* Pure White */
            font-family: 'Geist', sans-serif; /* Font kekinian */
            color: #09090b; /* Zinc-950 */
        }
        
        /* SIDEBAR - Minimalist Grey */
        section[data-testid="stSidebar"] {
            background-color: #fafafa; /* Zinc-50 */
            border-right: 1px solid #e4e4e7; /* Zinc-200 */
        }
        
        /* CARD SYSTEM (SHADCN) */
        .scn-card {
            background-color: #ffffff;
            border: 1px solid #e4e4e7;
            border-radius: 8px; /* Radius kecil agar tajam */
            padding: 24px;
            margin-bottom: 16px;
            transition: all 0.2s ease;
        }
        .scn-card:hover {
            border-color: #a1a1aa; /* Zinc-400 */
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        }
        
        /* STATS / METRICS */
        .stat-label {
            font-size: 13px;
            font-weight: 500;
            color: #71717a; /* Zinc-500 */
            margin-bottom: 4px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #09090b; /* Zinc-950 */
            letter-spacing: -0.5px;
        }
        .stat-desc {
            font-size: 12px;
            color: #a1a1aa;
            margin-top: 4px;
        }
        
        /* PROFIT HIGHLIGHT (Black Card) */
        .profit-card {
            background-color: #09090b; /* Zinc-950 (Black) */
            color: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .profit-val {
            font-size: 32px;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -1px;
        }
        
        /* TABLE STYLING */
        div[data-testid="stDataFrame"] {
            border: 1px solid #e4e4e7;
            border-radius: 8px;
        }
        
        /* REMOVE STREAMLIT JUNK */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        
        h1, h2, h3 { font-family: 'Geist', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
        
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE (BEDP DATA) ---
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

# --- 3. LOGIC ---
def run_optimization(tn, tp, tk, ts, prices):
    mats = list(RAW_MATS.keys())
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    
    A_ub, b_ub = [], []
    # Nutrients >= Target (-Ax <= -b)
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
        
    # Filler Limit (Engineering Constraint)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0) # Max 300kg
        
    # Equality 1000kg
    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT ---

with st.sidebar:
    st.markdown("### ⚙️ Control Panel")
    
    st.caption("GRADE SPECIFICATION")
    grade = st.selectbox("Target Grade", ["15-15-15", "15-10-12", "16-16-16"], label_visibility="collapsed")
    
    if grade == "15-15-15": defs = (15,15,15,2)
    elif grade == "15-10-12": defs = (15,10,12,2)
    else: defs = (16,16,16,0)
    
    # Input Kecil & Rapi
    c1, c2 = st.columns(2)
    tn = c1.number_input("N", value=float(defs[0]), label_visibility="collapsed")
    c1.caption("Nitrogen %")
    tp = c2.number_input("P", value=float(defs[1]), label_visibility="collapsed")
    c2.caption("Phosphate %")
    tk = c1.number_input("K", value=float(defs[2]), label_visibility="collapsed")
    c1.caption("Potash %")
    ts = c2.number_input("S", value=float(defs[3]), label_visibility="collapsed")
    c2.caption("Sulfur %")
    
    st.markdown("---")
    st.caption("MARKET PRICES (IDR)")
    curr_prices = {}
    for m, p in RAW_MATS.items():
        curr_prices[m] = st.number_input(f"{m}", value=p["Price"], step=100)
        
    st.markdown("---")
    # Shadcn UI Button (Black)
    if ui.button("Start Optimization", key="run_btn", className="bg-black text-white w-full"):
        st.session_state.run = True

# --- MAIN CONTENT ---
st.markdown("### 🏭 NPK Engineering Intelligence")
st.markdown("<div style='color:#71717a; font-size:14px; margin-top:-10px; margin-bottom:30px;'>Process Optimization & Cost Analysis System</div>", unsafe_allow_html=True)

if 'run' in st.session_state:
    res, mat_list = run_optimization(tn, tp, tk, ts, curr_prices)
    
    if res.success:
        # Calculation
        df = pd.DataFrame({"Material": mat_list, "Mass": res.x})
        df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        df = df[df["Mass"] > 0.1].sort_values("Mass", ascending=False)
        
        total_cost_opt = df["Cost"].sum()
        
        # Baseline Logic
        guar_recipe = GUARANTEE_REF[grade]
        total_cost_guar = sum([qty * curr_prices[m] for m, qty in guar_recipe.items()])
        saving = total_cost_guar - total_cost_opt
        
        # --- KPI ROW (SHADCN CARDS) ---
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown(f"""
            <div class="scn-card">
                <div class="stat-label">OPTIMIZED COGS (RM)</div>
                <div class="stat-value">Rp {total_cost_opt/1e6:,.2f} M</div>
                <div class="stat-desc">Per Metric Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
        
        with c2:
            st.markdown(f"""
            <div class="scn-card">
                <div class="stat-label">BASELINE (GUARANTEE)</div>
                <div class="stat-value" style="color:#71717a;">Rp {total_cost_guar/1e6:,.2f} M</div>
                <div class="stat-desc">BEDP Reference Cost</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            # Logic Profit Color
            is_profit = saving >= 0
            profit_txt = f"+ Rp {saving:,.0f}" if is_profit else f"- Rp {abs(saving):,.0f}"
            bg = "#09090b" # Black
            
            st.markdown(f"""
            <div class="profit-card">
                <div class="stat-label" style="color:#a1a1aa;">POTENTIAL MARGIN IMPACT</div>
                <div class="profit-val">{profit_txt}</div>
                <div class="stat-desc" style="color:#52525b;">{'✅ Cost Savings' if is_profit else '⚠️ Cost Increase'} vs Design</div>
            </div>
            """, unsafe_allow_html=True)
            
        # --- DETAILS & CHART ---
        col_l, col_r = st.columns([2, 1])
        
        with col_l:
            st.markdown("##### 📋 Formulation Bill of Materials")
            
            # Clean Table with Progress Bar
            df_show = df.copy()
            df_show["% Mix"] = df_show["Mass"] / 10  # 1000kg basis -> %
            
            st.dataframe(
                df_show[["Material", "Mass", "% Mix", "Price", "Cost"]],
                column_config={
                    "Material": st.column_config.TextColumn("Raw Material", width="medium"),
                    "Mass": st.column_config.NumberColumn("Mass (kg)", format="%.2f"),
                    "% Mix": st.column_config.ProgressColumn("Mix Ratio", format="%.1f%%", min_value=0, max_value=100),
                    "Price": st.column_config.NumberColumn("Unit Price", format="Rp %.0f"),
                    "Cost": st.column_config.NumberColumn("Subtotal", format="Rp %.0f"),
                },
                use_container_width=True,
                hide_index=True
            )
            
        with col_r:
            st.markdown("##### Composition Analysis")
            
            # Minimalist Donut Chart
            fig = go.Figure(data=[go.Pie(
                labels=df['Material'], values=df['Mass'], hole=.7,
                textinfo='none',
                marker=dict(colors=['#18181b', '#3f3f46', '#71717a', '#a1a1aa', '#d4d4d8']) # Monochrome Palette
            )])
            fig.update_layout(
                showlegend=True, 
                margin=dict(t=0, b=0, l=0, r=0), 
                height=250,
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
        # --- VALIDATION BAR (Minimalist) ---
        st.markdown("##### 🛡️ Specification Compliance Check")
        
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        nutrients = ['N', 'P', 'K', 'S']
        targets = [tn, tp, tk, ts]
        actuals = [act_n, act_p, act_k, act_s]
        
        fig_bar = go.Figure()
        # Target Line (Thin Grey)
        fig_bar.add_trace(go.Bar(
            name='Target', x=nutrients, y=targets,
            marker_color='#e4e4e7', # Zinc-200
            text=targets, textposition='auto', textfont=dict(color='black')
        ))
        # Actual Bar (Black)
        fig_bar.add_trace(go.Bar(
            name='Achieved', x=nutrients, y=actuals,
            marker_color='#09090b', # Black
            text=[f"{x:.1f}" for x in actuals], textposition='auto', textfont=dict(color='white')
        ))
        
        fig_bar.update_layout(
            barmode='group',
            plot_bgcolor='white',
            height=250,
            margin=dict(t=10, b=10, l=10, r=10),
            yaxis=dict(showgrid=True, gridcolor='#f4f4f5', zeroline=False),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        ui.metric_card(title="Status", content="Infeasible", description="Cannot meet grade specs with selected materials", key="err")

else:
    # Empty State - Clean
    st.markdown("""
    <div style="text-align:center; padding:50px; border:1px dashed #e4e4e7; border-radius:12px; color:#a1a1aa;">
        Select a Grade in the sidebar and click <b>Start Optimization</b> to begin analysis.
    </div>
    """, unsafe_allow_html=True)
