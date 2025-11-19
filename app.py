import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.optimize import linprog

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="NPK Pro Calculator", layout="wide", page_icon="✨")

# --- 2. "PAJAKKU" STYLE CSS (THE MAGIC) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        /* GLOBAL THEME */
        .stApp {
            background: linear-gradient(135deg, #eff6ff 0%, #f5f3ff 100%); /* Soft Blue-Purple Gradient */
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }
        
        /* HIDE DEFAULT ELEMENTS */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* INPUT CARD (LEFT SIDE) */
        .input-container {
            background-color: white;
            border-radius: 24px; /* Rounded like screenshot */
            padding: 40px;
            box-shadow: 0 10px 40px -10px rgba(0,0,0,0.05);
            height: 100%;
        }
        
        /* OUTPUT CARD (RIGHT SIDE - DARK THEME) */
        .output-container {
            background-color: #0f172a; /* Dark Navy (Slate 900) */
            color: white;
            border-radius: 24px;
            padding: 40px;
            box-shadow: 0 20px 50px -12px rgba(15, 23, 42, 0.25);
            height: 100%;
            position: relative;
        }
        
        /* TYPOGRAPHY */
        h1 { font-weight: 800; letter-spacing: -0.5px; color: #111827; font-size: 28px; margin-bottom: 10px; }
        h3 { font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; color: #6b7280; margin-top: 20px;}
        
        /* CUSTOM METRIC IN DARK CARD */
        .result-label {
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 1.5px;
            text-transform: uppercase;
            color: #94a3b8; /* Slate 400 */
            margin-bottom: 8px;
        }
        .result-value-big {
            font-size: 48px;
            font-weight: 800;
            color: #2dd4bf; /* Teal Accent like screenshot */
            margin-bottom: 5px;
            line-height: 1;
        }
        .result-sub {
            font-size: 14px;
            color: #cbd5e1;
            margin-bottom: 30px;
        }
        
        /* MINI RESULT BOX */
        .mini-box {
            background-color: #1e293b; /* Lighter Navy */
            border-radius: 12px;
            padding: 20px;
            margin-top: 15px;
            border: 1px solid #334155;
        }
        
        /* INPUT STYLING OVERRIDE */
        .stNumberInput > label { font-weight: 600; color: #374151; }
        .stSelectbox > label { font-weight: 600; color: #374151; }
        
        /* BUTTON */
        .stButton>button {
            background: linear-gradient(90deg, #4f46e5 0%, #6366f1 100%); /* Indigo Gradient */
            color: white;
            border: none;
            padding: 0.8rem 0;
            border-radius: 50px; /* Pill shape */
            font-weight: 600;
            width: 100%;
            box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            transition: transform 0.1s;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
        }
        
        /* REMOVE PADDING TOP */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE & LOGIC ---
RAW_MATS = {
    "Urea": {"N": 46.0, "P": 0.0, "K": 0.0, "S": 0.0, "Type": "Urea", "Price": 6500},
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

def solve_opt(tn, tp, tk, ts, prices):
    mats = list(RAW_MATS.keys())
    n_vars = len(mats)
    total_mass = 1000.0
    c = [prices[m] for m in mats]
    A_ub, b_ub = [], []
    
    A_ub.append([-RAW_MATS[m]["N"]/100 for m in mats]); b_ub.append(-tn/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["P"]/100 for m in mats]); b_ub.append(-tp/100 * total_mass)
    A_ub.append([-RAW_MATS[m]["K"]/100 for m in mats]); b_ub.append(-tk/100 * total_mass)
    if ts > 0:
        A_ub.append([-RAW_MATS[m]["S"]/100 for m in mats]); b_ub.append(-ts/100 * total_mass)
        
    filler_row = [1.0 if RAW_MATS[m]["Type"] == "Filler" else 0.0 for m in mats]
    if sum(filler_row) > 0: A_ub.append(filler_row); b_ub.append(300.0)

    A_eq, b_eq = [[1.0] * n_vars], [total_mass]
    bounds = [(0, total_mass) for _ in range(n_vars)]
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    return res, mats

# --- 4. UI LAYOUT (SPLIT CARD) ---

# TITLE SECTION
st.markdown("<div style='text-align:center; margin-bottom:30px;'><h1>NPK Pro Formulator</h1><p style='color:#6b7280;'>Optimalisasi Biaya Produksi Pupuk Majemuk (Basis 1 Ton)</p></div>", unsafe_allow_html=True)

# CONTAINER SPLIT
col_input, col_output = st.columns([1.2, 1], gap="large")

# --- LEFT COLUMN: INPUT (LIGHT THEME) ---
with col_input:
    st.markdown('<div class="input-container">', unsafe_allow_html=True)
    
    st.markdown("### 1. Target Grade")
    grade_sel = st.selectbox("Pilih Grade", ["15-15-15", "15-10-12", "16-16-16", "Custom"], label_visibility="collapsed")
    
    # Presets
    if grade_sel == "15-15-15": d = (15,15,15,2)
    elif grade_sel == "15-10-12": d = (15,10,12,2)
    elif grade_sel == "16-16-16": d = (16,16,16,0)
    else: d = (15,15,15,0)
    
    c1, c2, c3, c4 = st.columns(4)
    tn = c1.number_input("N %", value=float(d[0]))
    tp = c2.number_input("P %", value=float(d[1]))
    tk = c3.number_input("K %", value=float(d[2]))
    ts = c4.number_input("S %", value=float(d[3]))
    
    st.markdown("### 2. Market Prices (IDR)")
    curr_prices = {}
    for m, p in RAW_MATS.items():
        curr_prices[m] = p["Price"] # Default hidden, add expander if needed
    
    # Simulasi Harga Utama (Slider/Input agar interaktif seperti kalkulator)
    urea_p = st.slider("Harga Urea (Rp/kg)", 4000, 10000, 6500, step=100)
    curr_prices["Urea"] = urea_p
    
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("HITUNG ESTIMASI BIAYA")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- RIGHT COLUMN: OUTPUT (DARK THEME) ---
with col_output:
    
    # Default State
    total_cost = 0
    savings = 0
    is_profit = True
    df_show = pd.DataFrame()
    
    if run_btn:
        res, mat_list = solve_opt(tn, tp, tk, ts, curr_prices)
        if res.success:
            masses = res.x
            df = pd.DataFrame({"Material": mat_list, "Mass": masses})
            df["Price"] = df["Material"].apply(lambda x: curr_prices[x])
            df["Cost"] = df["Mass"] * df["Price"]
            df = df[df["Mass"] > 0.01].sort_values("Mass", ascending=False)
            
            total_cost = df["Cost"].sum()
            
            # Baseline
            guar_recipe = GUARANTEE_REF.get(grade_sel, {})
            base_cost = sum([qty * curr_prices.get(m, 0) for m, qty in guar_recipe.items()])
            savings = base_cost - total_cost
            is_profit = savings >= 0
            df_show = df.copy()

    # RENDER DARK CARD
    st.markdown(f'<div class="output-container">', unsafe_allow_html=True)
    
    # HEADER RESULT
    st.markdown('<div class="result-label">ESTIMASI BIAYA PRODUKSI (COGS)</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-value-big">Rp {total_cost/1e6:,.2f} Jt</div>', unsafe_allow_html=True)
    st.markdown('<div class="result-sub">Per Metrik Ton Produk</div>', unsafe_allow_html=True)
    
    # MINI BOX: PROFIT
    color_txt = "#4ade80" if is_profit else "#f87171" # Green vs Red
    sign = "+" if is_profit else ""
    
    st.markdown(f"""
    <div class="mini-box">
        <div class="result-label">POTENSI PENGHEMATAN VS DESAIN</div>
        <div style="font-size: 24px; font-weight: 700; color: {color_txt};">
            {sign} Rp {savings:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # MINI BOX: UNIT COST
    st.markdown(f"""
    <div class="mini-box">
        <div class="result-label">HARGA POKOK PER ZAK (50KG)</div>
        <div style="font-size: 24px; font-weight: 700; color: white;">
            Rp {total_cost/20:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # COMPOSITION PREVIEW
    if not df_show.empty:
        st.markdown("<br><div class="result-label">KOMPOSISI UTAMA</div>", unsafe_allow_html=True)
        # Simple manual chart using HTML bars for cleaner look in dark mode
        for _, row in df_show.head(3).iterrows():
            width = (row['Mass'] / 1000) * 100
            st.markdown(f"""
            <div style="margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; font-size:13px; color:#e2e8f0;">
                    <span>{row['Material']}</span>
                    <span>{row['Mass']:.1f} kg</span>
                </div>
                <div style="background:#334155; height:6px; border-radius:3px; margin-top:4px;">
                    <div style="background:#6366f1; width:{width}%; height:100%; border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown('</div>', unsafe_allow_html=True) # End Output Container

# --- BOTTOM SECTION: TABLE ---
if not df_show.empty:
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("Lihat Detail Resep Lengkap", expanded=True):
        st.dataframe(
            df_show[["Material", "Mass", "Price", "Cost"]],
            column_config={
                "Material": st.column_config.TextColumn("Bahan Baku"),
                "Mass": st.column_config.NumberColumn("Massa (kg)", format="%.2f"),
                "Price": st.column_config.NumberColumn("Harga Satuan", format="Rp %.0f"),
                "Cost": st.column_config.NumberColumn("Total Biaya", format="Rp %.0f"),
            },
            use_container_width=True
        )
