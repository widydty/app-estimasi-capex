import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="CAPEX.ai | Smart Estimator",
    layout="wide",
    page_icon="💎",
    initial_sidebar_state="expanded"
)

# --- 2. ADVANCED CSS (GLASSMORPHISM UI) ---
st.markdown("""
    <style>
        /* Import Modern Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        /* Global Style */
        .stApp {
            background: radial-gradient(circle at 10% 20%, rgb(16, 20, 28) 0%, rgb(5, 5, 10) 90%);
            font-family: 'Inter', sans-serif;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: rgba(16, 20, 28, 0.95);
            border-right: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* Card Style (Glass Effect) */
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-5px);
            border-color: rgba(0, 212, 255, 0.3);
            box-shadow: 0 10px 40px rgba(0, 212, 255, 0.1);
        }
        
        /* Typography */
        h1, h2, h3 {
            color: #ffffff !important;
            font-weight: 800 !important;
            letter-spacing: -0.5px;
        }
        p, label {
            color: #8b949e !important;
        }
        
        /* Metrics Value */
        .big-number {
            font-size: 32px;
            font-weight: 800;
            background: -webkit-linear-gradient(45deg, #00d4ff, #00ff9d);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .sub-text {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #6e7681;
            margin-bottom: 5px;
        }
        
        /* Custom Streamlit Components Overrides */
        .stSlider > div > div > div > div {
            background-color: #00d4ff;
        }
        .stSelectbox > div > div {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. COMPREHENSIVE DATA ENGINE (Based on Turton 2018 Appendix A) ---
# Format: [K1, K2, K3] for log10(Cp) formula
EQUIPMENT_DB = {
    "--- FLUID MOVING ---": {"k": [0,0,0], "min": 0, "max": 0, "unit": "-", "bm": 0}, # Separator
    "Centrifugal Pump (Process)": {"k": [3.3892, 0.0536, 0.1538], "min": 1, "max": 300, "unit": "Power (kW)", "bm": 3.30},
    "Reciprocating Pump": {"k": [3.8696, 0.3161, 0.1220], "min": 1, "max": 300, "unit": "Power (kW)", "bm": 3.30},
    "Positive Displacement Pump": {"k": [3.4771, 0.1350, 0.1438], "min": 1, "max": 100, "unit": "Power (kW)", "bm": 3.30},
    "Centrifugal Compressor": {"k": [2.2891, 1.3604, -0.1027], "min": 450, "max": 3000, "unit": "Power (kW)", "bm": 2.15},
    "Screw Compressor": {"k": [2.4493, 0.9765, -0.0263], "min": 10, "max": 800, "unit": "Power (kW)", "bm": 2.15},
    "Fan / Blower": {"k": [3.1761, 0.6312, 0.0598], "min": 10, "max": 500, "unit": "Air Flow (m3/s)", "bm": 2.15},
    
    "--- HEAT TRANSFER ---": {"k": [0,0,0], "min": 0, "max": 0, "unit": "-", "bm": 0},
    "Shell & Tube Exchanger (Floating Head)": {"k": [4.8306, -0.8509, 0.3187], "min": 10, "max": 1000, "unit": "Area (m2)", "bm": 3.17},
    "Shell & Tube Exchanger (Fixed Sheet)": {"k": [4.3247, -0.3030, 0.1634], "min": 10, "max": 1000, "unit": "Area (m2)", "bm": 3.17},
    "U-Tube Heat Exchanger": {"k": [4.1884, -0.2503, 0.1974], "min": 10, "max": 1000, "unit": "Area (m2)", "bm": 3.17},
    "Kettle Reboiler": {"k": [4.4646, -0.5277, 0.3955], "min": 10, "max": 100, "unit": "Area (m2)", "bm": 3.17},
    "Air Cooler (Fin Fan)": {"k": [4.0336, 0.2341, 0.0497], "min": 10, "max": 1000, "unit": "Area (m2)", "bm": 2.50},
    
    "--- VESSELS & TANKS ---": {"k": [0,0,0], "min": 0, "max": 0, "unit": "-", "bm": 0},
    "Process Vessel (Vertical)": {"k": [3.4974, 0.4485, 0.1074], "min": 0.3, "max": 100, "unit": "Volume (m3)", "bm": 4.16},
    "Process Vessel (Horizontal)": {"k": [3.5565, 0.3776, 0.0905], "min": 0.3, "max": 100, "unit": "Volume (m3)", "bm": 4.16},
    "Storage Tank (API Flat Bottom)": {"k": [4.8509, -0.3973, 0.1445], "min": 100, "max": 40000, "unit": "Volume (m3)", "bm": 1.5},
    
    "--- SEPARATION & SOLIDS ---": {"k": [0,0,0], "min": 0, "max": 0, "unit": "-", "bm": 0},
    "Distillation Tower (Tray)": {"k": [2.9949, 0.4465, 0.3961], "min": 2, "max": 100, "unit": "Height (m)", "bm": 4.16},
    "Cyclone Separator": {"k": [2.9886, 0.6457, 0.0923], "min": 1, "max": 100, "unit": "Area (m2)", "bm": 2.60},
    "Filter Press": {"k": [3.7733, 0.6343, -0.0478], "min": 1, "max": 100, "unit": "Area (m2)", "bm": 2.30},
    "Conveyor (Belt)": {"k": [3.6638, 0.8666, -0.0352], "min": 10, "max": 2000, "unit": "Area (m2)", "bm": 1.60},
    "Conveyor (Screw)": {"k": [3.1974, 0.7435, 0.0346], "min": 2, "max": 200, "unit": "Area (m2)", "bm": 1.60},
    "Crusher": {"k": [3.2362, 0.1559, 0.2449], "min": 10, "max": 1000, "unit": "Power (kW)", "bm": 2.00},
}

# Material Factors (Simplifikasi)
MATERIAL_FACTORS = {
    "Carbon Steel": 1.0,
    "Stainless Steel (304)": 1.3,
    "Stainless Steel (316)": 1.45,
    "Monel": 3.6,
    "Titanium": 4.4,
    "Inconel": 3.9
}

# --- 4. CALCULATION ENGINE ---
def get_cost(equipment, capacity, material, cepci):
    data = EQUIPMENT_DB[equipment]
    k = data['k']
    f_bm = data['bm']
    
    # Turton Formula: Log10(Cp0) = K1 + K2*log(A) + K3*log(A)^2
    log_a = np.log10(capacity)
    log_cp = k[0] + k[1]*log_a + k[2]*(log_a**2)
    base_cost_2001 = 10**log_cp
    
    # Adjustments
    f_mat = MATERIAL_FACTORS[material]
    final_cost_2001 = base_cost_2001 * f_bm * f_mat
    
    # Inflation Adjustment (Base 2001 CEPCI = 397)
    present_cost = final_cost_2001 * (cepci / 397)
    
    return present_cost

# --- 5. UI LAYOUT ---

# Sidebar Navigation
with st.sidebar:
    st.markdown("## ⚙️ CONFIGURATION")
    st.markdown("---")
    
    # Filter Equipment List (Remove headers)
    valid_equipments = [k for k, v in EQUIPMENT_DB.items() if v['unit'] != "-"]
    
    selected_equip = st.selectbox("Select Equipment", valid_equipments)
    
    # Dynamic Controls
    eq_data = EQUIPMENT_DB[selected_equip]
    
    st.markdown(f"**Design Capacity ({eq_data['unit']})**")
    capacity = st.slider("Capacity", 
                         min_value=float(eq_data['min']), 
                         max_value=float(eq_data['max']), 
                         value=float(eq_data['min']))
    
    material = st.selectbox("Material Class", list(MATERIAL_FACTORS.keys()))
    
    st.markdown("---")
    st.markdown("## 💰 ECONOMICS")
    cepci = st.number_input("CEPCI Index (2025)", value=850, step=10)
    usd_idr = st.number_input("Exchange Rate (IDR/USD)", value=15850, step=50)
    
    st.markdown("---")
    st.caption("Powered by CAPEX.ai Engine v3.0")

# Main Content
col_header, col_logo = st.columns([3,1])
with col_header:
    st.title("CAPEX INTELLIGENCE")
    st.markdown("Real-time parametric estimation system for process equipment.")

# --- 6. CALCULATION & DISPLAY ---
try:
    cost_usd = get_cost(selected_equip, capacity, material, cepci)
    cost_idr = cost_usd * usd_idr
    
    # --- ROW 1: EXECUTIVE SUMMARY (GLASS CARDS) ---
    st.markdown("### 📊 Executive Summary")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="sub-text">Total Estimated Cost</div>
            <div class="big-number">Rp {cost_idr/1000000:,.0f} Juta</div>
            <div style="color:#8b949e; font-size:12px; margin-top:5px;">Based on current forex rates</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="sub-text">USD Valuation</div>
            <div class="big-number">${cost_usd:,.0f}</div>
            <div style="color:#8b949e; font-size:12px; margin-top:5px;">CEPCI Index: {cepci}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="sub-text">Equipment Spec</div>
            <div class="big-number">{capacity} {eq_data['unit']}</div>
            <div style="color:#8b949e; font-size:12px; margin-top:5px;">Material: {material}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- ROW 2: DEEP DIVE ANALYTICS ---
    col_chart, col_details = st.columns([2, 1])
    
    with col_chart:
        st.markdown("### 📈 Cost Sensitivity Curve")
        
        # Generate Curve Data
        x_range = np.linspace(eq_data['min'], eq_data['max'], 100)
        y_range = [get_cost(selected_equip, x, material, cepci) * usd_idr for x in x_range]
        
        # Plotly Chart (Dark Neon Theme)
        fig = go.Figure()
        
        # The Line
        fig.add_trace(go.Scatter(
            x=x_range, y=y_range,
            mode='lines',
            name='Cost Trend',
            line=dict(color='#00d4ff', width=4, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(0, 212, 255, 0.1)'
        ))
        
        # The Current Point
        fig.add_trace(go.Scatter(
            x=[capacity], y=[cost_idr],
            mode='markers',
            name='Your Design',
            marker=dict(color='#ffffff', size=15, line=dict(color='#00d4ff', width=3))
        ))
        
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            xaxis=dict(title=eq_data['unit'], showgrid=False),
            yaxis=dict(title="Cost (IDR)", showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, use_container_width=True)

    with col_details:
        st.markdown("### 📋 Specification")
        
        # Table Data
        breakdown_data = {
            "Parameter": ["Equipment Type", "Capacity", "Material Factor", "Bare Module Factor", "Base Year"],
            "Value": [selected_equip, f"{capacity} {eq_data['unit']}", MATERIAL_FACTORS[material], eq_data['bm'], "2001 (Turton)"]
        }
        df_spec = pd.DataFrame(breakdown_data)
        
        st.dataframe(
            df_spec, 
            hide_index=True, 
            use_container_width=True,
            column_config={"Parameter": st.column_config.TextColumn("Parameter", width="medium")}
        )
        
        st.info("💡 **Pro Tip:** Double-check material availability for Titanium/Alloy specifications as lead time affects project schedule.")

except Exception as e:
    st.error(f"Calculation Error: {e}")

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #4b5563; font-size: 12px;'>
    <b>ENGINEERING COST ESTIMATOR V3.1</b> <br>
    Based on <i>Analysis, Synthesis and Design of Chemical Processes</i> (Turton et al., 2018) <br>
    CONFIDENTIAL - INTERNAL USE ONLY
</div>
""", unsafe_allow_html=True)
