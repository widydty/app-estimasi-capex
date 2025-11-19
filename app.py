import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. SETTING HALAMAN & TEMA MODERN ---
st.set_page_config(page_title="Pro-Estimator", layout="wide", page_icon="🏗️")

# CSS untuk Tampilan "Direktur"
st.markdown("""
    <style>
        .stApp { background-color: #0e1117; }
        h1, h2, h3 { color: #00d4ff !important; font-family: 'Roboto Mono', monospace; }
        .metric-card {
            background-color: #1f2937; border: 1px solid #374151;
            border-radius: 10px; padding: 20px; text-align: center;
        }
        .metric-value { font-size: 2em; font-weight: bold; color: #34d399; }
        .metric-label { color: #9ca3af; font-size: 0.9em; }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE RUMUS (HARDCODED DATA) ---
# Sumber: Turton et al. (Analysis, Synthesis and Design of Chemical Processes)
# Rumus: log10(Cp) = K1 + K2*log10(A) + K3*[log10(A)]^2
EQUIPMENT_DB = {
    "Centrifugal Pump": {
        "unit": "Power (kW)", "min": 1, "max": 300,
        "k": [3.3892, 0.0536, 0.1538], # K1, K2, K3
        "bare_module_factor": 3.30
    },
    "Shell & Tube Heat Exchanger": {
        "unit": "Area (m2)", "min": 10, "max": 1000,
        "k": [4.3247, -0.3030, 0.1634],
        "bare_module_factor": 3.17
    },
    "Storage Tank (Vertical)": {
        "unit": "Volume (m3)", "min": 50, "max": 10000,
        "k": [3.4974, 0.4485, 0.1074],
        "bare_module_factor": 4.16
    },
    "Distillation Column (Tower)": {
        "unit": "Height (m)", "min": 4, "max": 100,
        "k": [3.4974, 0.4485, 0.1074], # Simplified approximation
        "bare_module_factor": 4.16
    }
}

MATERIAL_FACTORS = {
    "Carbon Steel": 1.0,
    "Stainless Steel (304)": 1.3,
    "Stainless Steel (316)": 1.3,
    "Titanium": 4.4,
    "Nickel Alloy": 3.6
}

# --- 3. FUNGSI KALKULASI ---
def calculate_cost(equip_type, capacity, material, inflation_index):
    params = EQUIPMENT_DB[equip_type]
    k = params['k']
    
    # 1. Hitung Base Cost (Tahun Basis 2001, CEPCI ~397)
    # Rumus Logaritmik Turton
    log_a = np.log10(capacity)
    log_cp = k[0] + k[1]*log_a + k[2]*(log_a**2)
    base_cost_2001 = 10**log_cp
    
    # 2. Material Factor
    f_mat = MATERIAL_FACTORS[material]
    
    # 3. Bare Module Factor (Biaya Install, Piping, Listrik standar)
    f_bm = params['bare_module_factor']
    
    # 4. Eskalasi Inflasi (Misal Basis 2001=397, Sekarang=800)
    cost_2001_final = base_cost_2001 * f_bm * f_mat
    
    # Menghitung ke Harga Sekarang
    # Rumus: Cost_Present = Cost_Past * (Index_Present / Index_Past)
    present_cost_usd = cost_2001_final * (inflation_index / 397)
    
    return present_cost_usd

# --- 4. UI APLIKASI ---
st.title("🚀 QUICK CAPEX ESTIMATOR")
st.markdown("Standardized Engineering Costing (Based on Turton Models)")

# Layout 2 Kolom
col_input, col_result = st.columns([1, 2])

with col_input:
    st.markdown("### 🛠️ Design Parameters")
    
    # Input User
    equip_type = st.selectbox("Select Equipment", list(EQUIPMENT_DB.keys()))
    
    # Dynamic Slider based on Equipment
    params = EQUIPMENT_DB[equip_type]
    capacity = st.slider(f"Capacity - {params['unit']}", 
                         min_value=params['min'], 
                         max_value=params['max'], 
                         value=params['min'])
    
    material = st.selectbox("Material of Construction", list(MATERIAL_FACTORS.keys()))
    
    st.markdown("---")
    st.markdown("### 💰 Economic Factors")
    # Chemical Engineering Plant Cost Index (CEPCI). 2024 approx 800-850
    cepci = st.number_input("Current CEPCI Index (Inflation)", value=815) 
    usd_idr = st.number_input("Exchange Rate (USD to IDR)", value=15800)

with col_result:
    # Kalkulasi Real-time
    cost_usd = calculate_cost(equip_type, capacity, material, cepci)
    cost_idr = cost_usd * usd_idr
    
    st.markdown("### 📊 Estimation Result")
    
    # Tampilan Kartu Harga
    c1, c2 = st.columns(2)
    c1.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Estimated Cost (USD)</div>
            <div class="metric-value">${cost_usd:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
    
    c2.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Estimated Cost (IDR)</div>
            <div class="metric-value">Rp {cost_idr/1000000:,.0f} Juta</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # GRAFIK SENSITIVITAS (Agar terlihat canggih)
    # "Bagaimana harga berubah jika kapasitas naik?"
    
    # Generate data untuk grafik
    x_values = np.linspace(params['min'], params['max'], 50)
    y_values = []
    for x in x_values:
        c = calculate_cost(equip_type, x, material, cepci) * usd_idr
        y_values.append(c)
        
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x_values, y=y_values,
        mode='lines',
        name='Cost Curve',
        line=dict(color='#00d4ff', width=4)
    ))
    
    # Titik posisi user saat ini
    fig.add_trace(go.Scatter(
        x=[capacity], y=[cost_idr],
        mode='markers',
        name='Current Design',
        marker=dict(color='#ffeb3b', size=15, line=dict(width=2, color='white'))
    ))
    
    fig.update_layout(
        title=f"Cost Curve: {equip_type} ({material})",
        xaxis_title=params['unit'],
        yaxis_title="Estimated Price (IDR)",
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.warning("""
    ⚠️ **Disclaimer:** Estimasi ini adalah **Class 5 Estimate (+/- 30-50% accuracy)** 
    berdasarkan korelasi Turton et al. Digunakan untuk studi kelayakan awal, bukan penawaran final.
    """)
