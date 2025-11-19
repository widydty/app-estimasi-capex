import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import random

# --- 1. CONFIG & BLUEPRINT THEME ---
st.set_page_config(page_title="Eng.Spec Estimator", layout="wide", page_icon="📐")

st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Inter:wght@400;600&display=swap');
        
        .stApp {
            background-color: #ffffff;
            color: #333;
            font-family: 'Inter', sans-serif;
        }
        
        /* HEADER STYLE (Blueprint Look) */
        .header-box {
            background-color: #003366; /* Engineering Blue */
            color: white;
            padding: 15px 20px;
            border-bottom: 4px solid #ffcc00; /* Safety Yellow */
            margin-bottom: 20px;
        }
        
        /* DATASHEET TABLE STYLE */
        .datasheet-container {
            border: 2px solid #333;
            background-color: #f9f9f9;
            padding: 0;
            font-family: 'Roboto Mono', monospace;
            font-size: 14px;
        }
        .datasheet-header {
            background-color: #e0e0e0;
            border-bottom: 1px solid #333;
            padding: 8px;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .datasheet-row {
            display: flex;
            border-bottom: 1px solid #ccc;
        }
        .ds-label {
            width: 40%;
            background-color: #f0f0f0;
            padding: 8px;
            border-right: 1px solid #ccc;
            font-weight: 600;
            color: #444;
        }
        .ds-value {
            width: 60%;
            padding: 8px;
            background-color: white;
            color: #000;
        }
        
        /* COST BOX STYLE */
        .cost-box {
            border: 2px solid #2e7d32;
            background-color: #e8f5e9;
            color: #1b5e20;
            padding: 15px;
            text-align: right;
            font-family: 'Roboto Mono', monospace;
        }
        
        /* SIDEBAR STYLE */
        section[data-testid="stSidebar"] {
            background-color: #f4f4f4;
            border-right: 1px solid #ccc;
        }
        
        h1, h2, h3 { font-family: 'Inter', sans-serif; font-weight: 800; color: #003366; }
        
        /* CUSTOM INPUTS */
        .stNumberInput > div > div > input { font-family: 'Roboto Mono', monospace; }
    </style>
""", unsafe_allow_html=True)

# --- 2. EXPANDED ENGINEERING DATABASE (With Subtypes) ---
# Based on Guthrie / Turton Correlations
DB = {
    "PUMPS": {
        "Centrifugal (ANSI B73.1)": {"k": [3.3892, 0.0536, 0.1538], "unit": "kW", "min": 1, "max": 300, "bm": 3.30},
        "Centrifugal (API 610)":    {"k": [3.8696, 0.3161, 0.1220], "unit": "kW", "min": 10, "max": 1000, "bm": 3.80},
        "Positive Displacement":    {"k": [3.4771, 0.1350, 0.1438], "unit": "kW", "min": 1, "max": 200, "bm": 3.30},
        "Vertical Turbine":         {"k": [3.5565, 0.3776, 0.0905], "unit": "kW", "min": 5, "max": 500, "bm": 3.50},
    },
    "HEAT EXCHANGERS": {
        "Shell & Tube (Fixed Sheet)": {"k": [4.3247, -0.3030, 0.1634], "unit": "m2", "min": 10, "max": 1000, "bm": 3.17},
        "Shell & Tube (Floating)":    {"k": [4.8306, -0.8509, 0.3187], "unit": "m2", "min": 10, "max": 1000, "bm": 3.17},
        "Air Cooler (Fin Fan)":       {"k": [4.0336, 0.2341, 0.0497], "unit": "m2", "min": 10, "max": 1000, "bm": 2.50},
        "Plate & Frame":              {"k": [4.6656, -0.1557, 0.1547], "unit": "m2", "min": 10, "max": 500, "bm": 2.00},
    },
    "VESSELS & TANKS": {
        "Vertical Pressure Vessel":   {"k": [3.4974, 0.4485, 0.1074], "unit": "m3", "min": 0.5, "max": 100, "bm": 4.16},
        "Horizontal Drum":            {"k": [3.5565, 0.3776, 0.0905], "unit": "m3", "min": 0.5, "max": 100, "bm": 4.16},
        "Storage Tank (API 650)":     {"k": [4.8509, -0.3973, 0.1445], "unit": "m3", "min": 100, "max": 20000, "bm": 1.50},
        "Spherical Tank (API 620)":   {"k": [4.0000, 0.4000, 0.1000], "unit": "m3", "min": 500, "max": 5000, "bm": 2.50},
    },
    "COLUMNS (TOWERS)": {
        "Distillation (Sieve Tray)":  {"k": [2.9949, 0.4465, 0.3961], "unit": "m (Height)", "min": 5, "max": 80, "bm": 4.16},
        "Packed Column":              {"k": [3.1000, 0.5000, 0.3500], "unit": "m (Height)", "min": 5, "max": 60, "bm": 4.00},
    }
}

# Faktor Material (Cost Multiplier)
MAT_FACTORS = {
    "CS (A285 Gr.C)": 1.0,
    "SS 304": 1.3,
    "SS 316": 1.5,
    "Duplex SS": 1.9,
    "Monel 400": 3.3,
    "Titanium Gr.2": 4.2,
    "Inconel 625": 5.1
}

# --- 3. CALCULATION CORE ---
def calculate_detailed_cost(cat, sub, cap, pressure, material, cepci):
    data = DB[cat][sub]
    k = data['k']
    
    # 1. Base Equipment Cost (Log Formula)
    log_A = np.log10(cap)
    log_Cp = k[0] + k[1]*log_A + k[2]*(log_A**2)
    base_cost_2001 = 10**log_Cp
    
    # 2. Pressure Factor (Fp) - Rumus pendekatan (1 + 0.005 * P) untuk P > 5 bar
    f_press = 1.0
    if pressure > 10: # Bar
        log_p = np.log10(pressure)
        f_press = 10**(0.125 * log_p + 0.08) # Koreksi umum
    
    # 3. Material Factor (Fm)
    f_mat = MAT_FACTORS[material]
    
    # 4. Total Module Cost
    # Cost = Base * B1 + (Base * B2 * Fm * Fp)
    # Simplifikasi Turton: Cost = Base * Fbm * Fm * Fp (Approximation)
    bare_module_cost = base_cost_2001 * data['bm'] * f_mat * f_press
    
    # 5. Inflasi (2001 Base = 397)
    current_cost_usd = bare_module_cost * (cepci / 397)
    
    return current_cost_usd, f_press, f_mat

# --- 4. UI LAYOUT ---

# HEADER
st.markdown("""
<div class="header-box">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
            <h2 style="color:white; margin:0;">ENGINEERING ESTIMATION SYSTEM</h2>
            <small>CLASS 4 ESTIMATE (±25%) | METHOD: PARAMETRIC (TURTON/GUTHRIE)</small>
        </div>
        <div style="text-align:right; font-family:'Roboto Mono';">
            DOC NO: EST-2025-001<br>
            REV: A
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# MAIN COLUMNS
col_input, col_datasheet = st.columns([1, 2])

with col_input:
    st.subheader("🛠️ TECHNICAL INPUT")
    st.markdown("---")
    
    # 1. Equipment Selection
    category = st.selectbox("Category", list(DB.keys()))
    subtype = st.selectbox("Equipment Type", list(DB[category].keys()))
    
    data = DB[category][subtype]
    
    # 2. Process Data
    st.markdown("##### Process Conditions")
    col_i1, col_i2 = st.columns(2)
    capacity = col_i1.number_input(f"Capacity ({data['unit']})", min_value=float(data['min']), max_value=float(data['max']), value=float(data['min']))
    pressure = col_i2.number_input("Design Press. (barg)", value=5.0, min_value=1.0)
    
    temp = st.number_input("Design Temp. (°C)", value=45.0)
    material = st.selectbox("Material of Construction", list(MAT_FACTORS.keys()))
    
    st.markdown("---")
    st.markdown("##### Project Basis")
    cepci = st.number_input("CEPCI Index (Current)", value=820)
    kurs = st.number_input("Exchange Rate (IDR)", value=15850)
    
    if st.button("CALCULATE COST", type="primary"):
        st.session_state['calc_trigger'] = True

# DEFAULT CALCULATION
if 'calc_trigger' not in st.session_state:
    st.session_state['calc_trigger'] = True

cost_usd, fp, fm = calculate_detailed_cost(category, subtype, capacity, pressure, material, cepci)
cost_idr = cost_usd * kurs

# BREAKDOWN SIMULATION (Typical percentages)
mat_cost = cost_idr * 0.60
lab_cost = cost_idr * 0.25
ind_cost = cost_idr * 0.15

with col_datasheet:
    st.subheader("📄 EQUIPMENT DATASHEET & ESTIMATE")
    
    # UPPER ROW: KEY FIGURES
    c1, c2, c3 = st.columns([1.5, 1, 1])
    with c1:
        st.markdown(f"""
        <div class="cost-box">
            <div style="font-size:12px; color:#1b5e20;">TOTAL ESTIMATED COST (IDR)</div>
            <div style="font-size:28px; font-weight:bold;">Rp {cost_idr:,.0f}</div>
            <div style="font-size:14px; color:#555;">USD {cost_usd:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
         st.info(f"**Correction Factors**\n\nPress. Factor ($F_p$): {fp:.2f}\n\nMat. Factor ($F_m$): {fm:.2f}")

    # DATASHEET TABLE (HTML)
    st.markdown(f"""
    <div class="datasheet-container">
        <div class="datasheet-header">A. GENERAL SPECIFICATION</div>
        <div class="datasheet-row"><div class="ds-label">EQUIPMENT ITEM</div><div class="ds-value">{subtype.upper()}</div></div>
        <div class="datasheet-row"><div class="ds-label">TAG NUMBER</div><div class="ds-value">P-{random.randint(100,999)} (Auto-Generated)</div></div>
        <div class="datasheet-row"><div class="ds-label">CATEGORY</div><div class="ds-value">{category}</div></div>
        
        <div class="datasheet-header">B. OPERATING & DESIGN DATA</div>
        <div class="datasheet-row"><div class="ds-label">RATED CAPACITY</div><div class="ds-value">{capacity} {data['unit']}</div></div>
        <div class="datasheet-row"><div class="ds-label">DESIGN PRESSURE</div><div class="ds-value">{pressure} Barg</div></div>
        <div class="datasheet-row"><div class="ds-label">DESIGN TEMPERATURE</div><div class="ds-value">{temp} °C</div></div>
        
        <div class="datasheet-header">C. MECHANICAL DATA</div>
        <div class="datasheet-row"><div class="ds-label">MATERIAL CLASS</div><div class="ds-value">{material}</div></div>
        <div class="datasheet-row"><div class="ds-label">BARE MODULE FACTOR</div><div class="ds-value">{data['bm']}</div></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # COST BREAKDOWN CHART
    st.markdown("##### 📊 Cost Structure Breakdown")
    
    breakdown_df = pd.DataFrame({
        "Component": ["Equipment Material", "Direct Labor", "Indirects/Overhead"],
        "Value": [mat_cost, lab_cost, ind_cost]
    })
    
    fig = px.bar(breakdown_df, x="Value", y="Component", orientation='h', text="Value",
                 color="Component", color_discrete_sequence=["#003366", "#004d99", "#0066cc"])
    
    fig.update_traces(texttemplate='Rp %{text:,.0f}', textposition='auto')
    fig.update_layout(
        uniformtext_minsize=8, uniformtext_mode='hide',
        height=200,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#eee'),
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style="font-family: 'Roboto Mono'; font-size: 11px; color: #666; text-align: center;">
    ENGINEERING COST INTELLIGENCE SYSTEM | REF: TURTON 2018, GUTHRIE 1974 | INFLATION INDEX: CEPCI 2024
</div>
""", unsafe_allow_html=True)
