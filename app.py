import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="NEXUS | Engineering Estimator",
    layout="wide",
    page_icon="💠",
    initial_sidebar_state="collapsed" # Sidebar sembunyi agar layar penuh (Cinematic)
)

# --- 2. ENTERPRISE CSS INJECTION ---
st.markdown("""
    <style>
        /* IMPORT PREMIUM FONT */
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@300;400;600;800&display=swap');
        
        /* RESET & BASE STYLE */
        .stApp {
            background-color: #09090b; /* Ultra Dark Grey */
            font-family: 'Manrope', sans-serif;
        }
        
        /* REMOVE STREAMLIT BRANDING */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* CARD SYSTEM (Technical Look) */
        .tech-card {
            background-color: #121217;
            border: 1px solid #27272a;
            border-radius: 8px;
            padding: 24px;
            height: 100%;
            transition: all 0.3s ease;
        }
        .tech-card:hover {
            border-color: #3f3f46;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        
        /* TYPOGRAPHY */
        h1, h2, h3 {
            color: #ffffff !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }
        .label-text {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: #71717a; /* Muted text */
            margin-bottom: 8px;
        }
        .value-text {
            font-size: 36px;
            font-weight: 800;
            color: #fafafa;
            line-height: 1.1;
        }
        .unit-text {
            font-size: 14px;
            color: #a1a1aa;
            font-weight: 400;
        }
        
        /* CUSTOM INPUT WIDGETS */
        .stSelectbox > div > div {
            background-color: #18181b;
            border: 1px solid #27272a;
            color: white;
            border-radius: 6px;
        }
        .stSlider > div > div > div > div {
            background-color: #2dd4bf; /* Teal Accent */
        }
        
        /* STATUS INDICATOR */
        .status-pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 100px;
            font-size: 11px;
            font-weight: 700;
            background-color: rgba(45, 212, 191, 0.1);
            color: #2dd4bf;
            border: 1px solid rgba(45, 212, 191, 0.2);
        }
        
        /* DIVIDER */
        hr {
            border-color: #27272a;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE (TURTON 2018 EXPANDED) ---
# Database Equipment lengkap dengan parameter visual
EQUIPMENT_DB = {
    "Centrifugal Pump": {
        "icon": "💧", "min": 1, "max": 300, "unit": "kW", "bm": 3.30,
        "k": [3.3892, 0.0536, 0.1538]
    },
    "Compressor (Centrifugal)": {
        "icon": "💨", "min": 450, "max": 3000, "unit": "kW", "bm": 2.15,
        "k": [2.2891, 1.3604, -0.1027]
    },
    "Shell & Tube Exchanger": {
        "icon": "🔥", "min": 10, "max": 1000, "unit": "m²", "bm": 3.17,
        "k": [4.3247, -0.3030, 0.1634]
    },
    "Distillation Column": {
        "icon": "tower", "min": 4, "max": 100, "unit": "m (Height)", "bm": 4.16,
        "k": [3.4974, 0.4485, 0.1074]
    },
    "Storage Tank (API)": {
        "icon": "🛢️", "min": 100, "max": 20000, "unit": "m³", "bm": 1.50,
        "k": [4.8509, -0.3973, 0.1445]
    },
    "Reactor (CSTR)": {
        "icon": "⚗️", "min": 0.5, "max": 100, "unit": "m³", "bm": 4.00,
        "k": [3.4974, 0.4485, 0.1074] # Approx vessel
    },
    "Conveyor (Belt)": {
        "icon": "🛤️", "min": 10, "max": 2000, "unit": "m² (Area)", "bm": 1.60,
        "k": [3.6638, 0.8666, -0.0352]
    },
    "Crusher": {
        "icon": "🔨", "min": 10, "max": 1000, "unit": "kW", "bm": 2.00,
        "k": [3.2362, 0.1559, 0.2449]
    }
}

MATERIAL_FACTORS = {
    "Carbon Steel": 1.0,
    "Stainless Steel (304)": 1.3,
    "Stainless Steel (316)": 1.5,
    "Titanium": 4.4,
    "Nickel Alloy": 3.6
}

# --- 4. CALCULATION ENGINE ---
def calculate_capex(equip_key, capacity, material_key, cepci_idx):
    eq = EQUIPMENT_DB[equip_key]
    
    # 1. Base Cost (Turton Log Formula)
    log_A = np.log10(capacity)
    log_Cp = eq['k'][0] + eq['k'][1]*log_A + eq['k'][2]*(log_A**2)
    base_cost = 10**log_Cp
    
    # 2. Factors
    total_cost = base_cost * eq['bm'] * MATERIAL_FACTORS[material_key]
    
    # 3. Inflation (Base 2001 = 397)
    current_cost = total_cost * (cepci_idx / 397)
    return current_cost

# --- 5. HEADER SECTION ---
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("#### <span style='color:#2dd4bf'>NEXUS</span> INTELLIGENCE SYSTEM", unsafe_allow_html=True)
    st.markdown("# Capital Expenditure Estimator")
with c2:
    st.markdown("<div style='text-align:right; padding-top:10px;'><span class='status-pill'>● SYSTEM ONLINE</span></div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- 6. MAIN CONTROL PANEL (The Cockpit) ---
# Kita bagi layar jadi: Kiri (Input) dan Kanan (Output) dengan rasio 1:2
left_panel, right_panel = st.columns([1, 2], gap="large")

with left_panel:
    st.markdown("""
    <div class="tech-card">
        <div class="label-text">CONFIGURATION</div>
    """, unsafe_allow_html=True)
    
    # Inputs
    selected_eq = st.selectbox("Equipment Type", list(EQUIPMENT_DB.keys()))
    
    eq_data = EQUIPMENT_DB[selected_eq]
    st.markdown(f"<div style='margin-top:20px; margin-bottom:5px; color:#a1a1aa; font-size:13px;'>Capacity ({eq_data['unit']})</div>", unsafe_allow_html=True)
    capacity = st.slider("Capacity", eq_data['min'], eq_data['max'], float(eq_data['min']), label_visibility="collapsed")
    
    selected_mat = st.selectbox("Material Grade", list(MATERIAL_FACTORS.keys()))
    
    st.markdown("<hr>", unsafe_allow_html=True)
    
    st.markdown("<div class='label-text'>MARKET PARAMETERS</div>", unsafe_allow_html=True)
    cepci = st.number_input("CEPCI Index", value=815)
    usd_rate = st.number_input("USD/IDR Rate", value=15850, step=50)
    
    st.markdown("</div>", unsafe_allow_html=True) # End Card

with right_panel:
    # REAL-TIME CALCULATION
    cost_usd = calculate_capex(selected_eq, capacity, selected_mat, cepci)
    cost_idr = cost_usd * usd_rate
    
    # --- ROW 1: BIG METRICS ---
    m1, m2, m3 = st.columns(3)
    
    with m1:
        st.markdown(f"""
        <div class="tech-card">
            <div class="label-text">ESTIMATED COST (IDR)</div>
            <div class="value-text">Rp {cost_idr/1000000:,.0f}</div>
            <div class="unit-text">Juta Rupiah</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m2:
        st.markdown(f"""
        <div class="tech-card">
            <div class="label-text">USD VALUATION</div>
            <div class="value-text">${cost_usd:,.0f}</div>
            <div class="unit-text">Global Market Price</div>
        </div>
        """, unsafe_allow_html=True)
        
    with m3:
        st.markdown(f"""
        <div class="tech-card">
            <div class="label-text">ACCURACY CLASS</div>
            <div class="value-text">Cl. 5</div>
            <div class="unit-text">±30% Preliminary</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)

    # --- ROW 2: ADVANCED CHART ---
    # Chart harus terlihat premium (Minimalis, tanpa grid kotor)
    x_range = np.linspace(eq_data['min'], eq_data['max'], 100)
    y_range = [calculate_capex(selected_eq, x, selected_mat, cepci) * usd_rate for x in x_range]
    
    fig = go.Figure()
    
    # Gradient Fill Area
    fig.add_trace(go.Scatter(
        x=x_range, y=y_range,
        fill='tozeroy',
        mode='lines',
        line=dict(width=3, color='#2dd4bf'), # Teal Line
        fillcolor='rgba(45, 212, 191, 0.1)', # Teal Transparent
        name='Cost Curve'
    ))
    
    # Current Point Marker
    fig.add_trace(go.Scatter(
        x=[capacity], y=[cost_idr],
        mode='markers',
        marker=dict(size=18, color='#ffffff', line=dict(width=3, color='#2dd4bf')),
        name='Current Selection'
    ))
    
    fig.update_layout(
        title=dict(text="CAPEX SENSITIVITY CURVE", font=dict(family="Manrope", size=14, color="#71717a")),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=350,
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis=dict(
            title=f"Capacity ({eq_data['unit']})", 
            showgrid=False, 
            color="#71717a"
        ),
        yaxis=dict(
            title="Cost (IDR)", 
            showgrid=True, 
            gridcolor="#27272a", # Subtle grid
            color="#71717a",
            tickformat=".2s"
        ),
        hovermode="x unified",
        showlegend=False
    )
    
    st.markdown("""
    <div class="tech-card">
    """, unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="border-top: 1px solid #27272a; padding-top: 20px; color: #52525b; font-size: 12px; display: flex; justify-content: space-between;">
    <div>NEXUS ENGINEERING SYSTEM v4.0.2 (Stable)</div>
    <div>SECURE CONNECTION | INTERNAL USE ONLY</div>
</div>
""", unsafe_allow_html=True)
