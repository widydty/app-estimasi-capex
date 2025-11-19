import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from scipy.optimize import linprog

# --- 1. CONFIG & HIGH-END CSS ---
st.set_page_config(page_title="OPTIMUS | NPK System", layout="wide", page_icon="💠")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        /* GLOBAL RESET */
        .stApp {
            background-color: #f8fafc; /* Premium Grey */
            font-family: 'Inter', sans-serif;
        }
        
        /* SIDEBAR STYLING (Dark Theme) */
        section[data-testid="stSidebar"] {
            background-color: #0f172a; /* Slate 900 */
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] h2, 
        section[data-testid="stSidebar"] h3, 
        section[data-testid="stSidebar"] label, 
        section[data-testid="stSidebar"] .stMarkdown {
            color: #e2e8f0 !important;
        }
        
        /* MAIN HEADER */
        .main-header {
            font-size: 32px;
            font-weight: 800;
            color: #1e293b;
            letter-spacing: -1px;
            margin-bottom: 0px;
        }
        .sub-header {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 30px;
            font-weight: 500;
        }

        /* CUSTOM METRIC CARDS */
        .metric-container {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }
        .metric-container:hover {
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            transform: translateY(-2px);
        }
        .metric-title {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 28px;
            font-weight: 700;
            color: #0f172a;
        }
        .metric-delta-pos { color: #10b981; font-size: 13px; font-weight: 600; }
        .metric-delta-neg { color: #ef4444; font-size: 13px; font-weight: 600; }

        /* CUSTOM HTML TABLE (The "100 Billion" Look) */
        .styled-table {
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 14px;
            width: 100%;
            background-color: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }
        .styled-table thead tr {
            background-color: #f1f5f9;
            color: #475569;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }
        .styled-table th, .styled-table td {
            padding: 16px 20px;
        }
        .styled-table tbody tr {
            border-bottom: 1px solid #f1f5f9;
            transition: background 0.2s;
        }
        .styled-table tbody tr:hover {
            background-color: #f8fafc;
        }
        .styled-table tbody tr:last-of-type {
            border-bottom: none;
        }
        .badge-mix {
            background-color: #eff6ff;
            color: #2563eb;
            padding: 4px 8px;
            border-radius: 6px;
            font-weight: 600;
            font-size: 12px;
        }
        .cost-text {
            font-family: 'Roboto Mono', monospace;
            color: #0f172a;
            font-weight: 600;
        }

        /* BUTTONS */
        .stButton>button {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-weight: 600;
            width: 100%;
            box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.5);
        }
        .stButton>button:hover {
            background-color: #2563eb;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & LOGIC ---
RAW_MATS = {
    "Urea":         {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 0.5, "Type": "Urea",   "Price": 6500},
    "ZA (AmSulf)":  {"N": 21.0, "P": 0.0, "K": 0.0, "S": 24.0,"H2O": 1.0, "Type": "Salt",   "Price": 2500},
    "DAP (16-45)":  {"N": 16.0, "P": 45.0,"K": 0.0, "S": 0.0, "H2O": 1.5, "Type": "Salt",   "Price": 10500},
    "KCl (MOP)":    {"N": 0.0,  "P": 0.0, "K": 60.0,"S": 0.0, "H2O": 0.5, "Type": "Salt",   "Price": 8200},
    "Clay":         {"N": 0.0,  "P": 0.0, "K": 0.0, "S": 0.0, "H2O": 2.0, "Type": "Filler", "Price": 250}
}

def calculate_optimization(tn, tp, tk, ts, selected_mats, prices):
    mats = list(selected_mats)
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    A_ub = []
    b_ub = []
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats])
    b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats])
    b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats])
    b_ub.append(-tk/100 * total_mass)
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats])
        b_ub.append(-ts/100 * total_mass)
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0:
        A_ub.append(filler_row)
        b_ub.append(300.0)
    A_eq = [[1.0] * n_vars]
    b_eq = [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 3. UI LAYOUT (THE ENTERPRISE LOOK) ---

# SIDEBAR (DARK & CLEAN)
with st.sidebar:
    st.markdown("### 💠 OPTIMUS PRIME")
    st.markdown("<div style='color:#94a3b8; font-size:12px; margin-bottom:20px;'>NPK ENGINEERING SUITE v5.0</div>", unsafe_allow_html=True)
    
    st.markdown("#### 1. GRADE TARGET")
    grade_sel = st.selectbox("Select Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"], label_visibility="collapsed")
    
    if grade_sel == "15-15-15": def_n, def_p, def_k, def_s = 15.0, 15.0, 15.0, 2.0
    elif grade_sel == "15-10-12": def_n, def_p, def_k, def_s = 15.0, 10.0, 12.0, 2.0
    elif grade_sel == "16-16-16": def_n, def_p, def_k, def_s = 16.0, 16.0, 16.0, 0.0
    else: def_n, def_p, def_k, def_s = 15.0, 15.0, 15.0, 0.0
    
    col1, col2 = st.columns(2)
    tn = col1.number_input("N %", value=def_n)
    tp = col2.number_input("P %", value=def_p)
    tk = col1.number_input("K %", value=def_k)
    ts = col2.number_input("S %", value=def_s)
    
    st.markdown("#### 2. MARKET PRICES (IDR)")
    current_prices = {}
    for m, data in RAW_MATS.items():
        current_prices[m] = st.number_input(f"{m}", value=data["Price"], step=100)
        
    st.markdown("#### 3. ACTION")
    run_calc = st.button("RUN SIMULATION")

# MAIN CONTENT
st.markdown('<div class="main-header">Production Optimization Dashboard</div>', unsafe_allow_html=True)
st.markdown(f'<div class="sub-header">Optimization Basis: 1.000 kg • Target: NPK {tn}-{tp}-{tk}-{ts}S • Currency: IDR</div>', unsafe_allow_html=True)

if run_calc:
    res, mat_order = calculate_optimization(tn, tp, tk, ts, list(RAW_MATS.keys()), current_prices)
    
    if res.success:
        # DATA PROCESSING
        masses = res.x
        df = pd.DataFrame({"Material": mat_order, "Mass": masses})
        df = df[df["Mass"] > 0.1].sort_values("Mass", ascending=False)
        df["Price"] = df["Material"].apply(lambda x: current_prices[x])
        df["Cost"] = df["Mass"] * df["Price"]
        df["Mix"] = (df["Mass"] / 1000) * 100
        
        total_cost = df["Cost"].sum()
        total_mass = df["Mass"].sum()
        
        # --- ROW 1: METRIC CARDS ---
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Cost of Goods (RM)</div>
                <div class="metric-value">Rp {total_cost/1e6:.2f} M</div>
                <div class="metric-delta-pos">Per Ton Product</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Unit Cost (50kg)</div>
                <div class="metric-value">Rp {total_cost/20:,.0f}</div>
                <div class="metric-delta-pos">Per Bag</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c3:
            urea_p = df[df['Material']=='Urea']['Mix'].sum()
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Urea Composition</div>
                <div class="metric-value">{urea_p:.1f}%</div>
                <div class="{'metric-delta-pos' if urea_p < 50 else 'metric-delta-neg'}">Safe Limit: 50%</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c4:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Batch Mass Check</div>
                <div class="metric-value">{total_mass:.0f} kg</div>
                <div class="metric-delta-pos">Target: 1000 kg</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- ROW 2: TABLE & CHART SPLIT ---
        col_table, col_chart = st.columns([2, 1])
        
        with col_table:
            # GENERATE HTML TABLE (CUSTOM DESIGN)
            table_html = """
            <table class="styled-table">
                <thead>
                    <tr>
                        <th>Raw Material</th>
                        <th>Mass (kg)</th>
                        <th>Composition</th>
                        <th>Unit Price (IDR)</th>
                        <th>Total Cost (IDR)</th>
                    </tr>
                </thead>
                <tbody>
            """
            
            for _, row in df.iterrows():
                table_html += f"""
                <tr>
                    <td style="font-weight:500; color:#1e293b;">{row['Material']}</td>
                    <td>{row['Mass']:.2f}</td>
                    <td><span class="badge-mix">{row['Mix']:.1f}%</span></td>
                    <td class="cost-text">{row['Price']:,.0f}</td>
                    <td class="cost-text">{row['Cost']:,.0f}</td>
                </tr>
                """
            
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
            
        with col_chart:
            # HIGH END DONUT CHART
            # Use custom colors like Bloomberg/Financial Times
            colors = ['#3b82f6', '#0ea5e9', '#22c55e', '#eab308', '#64748b']
            
            fig = go.Figure(data=[go.Pie(
                labels=df['Material'], 
                values=df['Mass'], 
                hole=.6,
                marker=dict(colors=colors),
                textinfo='percent',
                hoverinfo='label+value'
            )])
            
            fig.update_layout(
                title_text="Formulation Mix",
                title_font_size=14,
                title_font_family="Inter",
                showlegend=True,
                legend=dict(orientation="h", y=-0.2),
                margin=dict(t=40, b=0, l=0, r=0),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)

        # --- ROW 3: ENGINEERING VALIDATION (STACKED BAR) ---
        st.markdown("### Nutrient Validation Profile")
        act_n = sum(row["Mass"] * RAW_MATS[row["Material"]]["N"]/100 for _, row in df.iterrows()) / 10
        act_p = sum(row["Mass"] * RAW_MATS[row["Material"]]["P"]/100 for _, row in df.iterrows()) / 10
        act_k = sum(row["Mass"] * RAW_MATS[row["Material"]]["K"]/100 for _, row in df.iterrows()) / 10
        act_s = sum(row["Mass"] * RAW_MATS[row["Material"]]["S"]/100 for _, row in df.iterrows()) / 10
        
        # Create clean comparison chart
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            name='Target', x=['N','P','K','S'], y=[tn, tp, tk, ts],
            marker_color='#e2e8f0', text=[tn, tp, tk, ts], textposition='auto'
        ))
        fig_bar.add_trace(go.Bar(
            name='Achieved', x=['N','P','K','S'], y=[act_n, act_p, act_k, act_s],
            marker_color='#0f172a', text=[f"{x:.1f}" for x in [act_n, act_p, act_k, act_s]], textposition='auto'
        ))
        
        fig_bar.update_layout(
            barmode='group',
            plot_bgcolor='white',
            height=300,
            margin=dict(t=20, b=20, l=20, r=20),
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
            font=dict(family="Inter")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.error("Solution Infeasible: Please adjust constraints or available materials.")
        
else:
    # EMPTY STATE (CLEAN)
    st.info("Ready to optimize. Adjust parameters on the left sidebar and click 'RUN SIMULATION'.")
