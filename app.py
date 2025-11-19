import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="NEXUS Estimator",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="expanded"
)

# --- 2. PREMIER LIGHT THEME CSS (Gaya Apple/Stripe) ---
st.markdown("""
    <style>
        /* Import Professional Font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        /* Main Background - Clean White/Light Grey */
        .stApp {
            background-color: #f8fafc; /* Slate-50 */
            font-family: 'Inter', sans-serif;
            color: #0f172a; /* Slate-900 */
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e2e8f0;
        }
        
        /* Card Container Style */
        .premium-card {
            background-color: #ffffff;
            border: 1px solid #e2e8f0; /* Subtle border */
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            margin-bottom: 20px;
            height: 100%;
        }
        
        /* Result Card (Highlighted) */
        .result-card {
            background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); /* Royal Blue Gradient */
            border-radius: 12px;
            padding: 24px;
            color: white;
            box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3);
            margin-bottom: 20px;
            text-align: center;
        }
        
        /* Typography */
        h1, h2, h3, h4 {
            font-weight: 700 !important;
            color: #1e293b !important; /* Slate-800 */
            letter-spacing: -0.5px;
        }
        
        .label-small {
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 1px;
            color: #64748b; /* Slate-500 */
            margin-bottom: 4px;
        }
        
        .value-large {
            font-size: 32px;
            font-weight: 700;
            color: #0f172a;
        }
        
        .value-white {
            font-size: 36px;
            font-weight: 700;
            color: #ffffff;
            margin: 10px 0;
        }
        
        /* Customizing Streamlit Widgets */
        .stSelectbox > div > div {
            background-color: white;
            border-color: #cbd5e1;
            color: #334155;
        }
        .stSlider > div > div > div > div {
            background-color: #2563eb; /* Blue-600 */
        }
        
        /* Remove Default Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
    </style>
""", unsafe_allow_html=True)

# --- 3. ENGINEERING DATA (FIXED TYPES) ---
# Semua angka min/max dipastikan float agar tidak error
EQUIPMENT_DB = {
    "Centrifugal Pump": {
        "icon": "💧", "min": 1.0, "max": 300.0, "unit": "kW", "bm": 3.30,
        "k": [3.3892, 0.0536, 0.1538]
    },
    "Compressor (Centrifugal)": {
        "icon": "💨", "min": 450.0, "max": 3000.0, "unit": "kW", "bm": 2.15,
        "k": [2.2891, 1.3604, -0.1027]
    },
    "Shell & Tube Exchanger": {
        "icon": "🔥", "min": 10.0, "max": 1000.0, "unit": "m²", "bm": 3.17,
        "k": [4.3247, -0.3030, 0.1634]
    },
    "Distillation Column": {
        "icon": "🗼", "min": 4.0, "max": 100.0, "unit": "m (Height)", "bm": 4.16,
        "k": [3.4974, 0.4485, 0.1074]
    },
    "Storage Tank (API)": {
        "icon": "🛢️", "min": 100.0, "max": 20000.0, "unit": "m³", "bm": 1.50,
        "k": [4.8509, -0.3973, 0.1445]
    },
    "Conveyor (Belt)": {
        "icon": "🛤️", "min": 10.0, "max": 2000.0, "unit": "m² (Area)", "bm": 1.60,
        "k": [3.6638, 0.8666, -0.0352]
    }
}

MATERIAL_FACTORS = {
    "Carbon Steel": 1.0,
    "Stainless Steel (304)": 1.3,
    "Stainless Steel (316)": 1.5,
    "Titanium": 4.4,
    "Nickel Alloy": 3.6
}

# --- 4. CALCULATION LOGIC ---
def calculate_capex(equip_key, capacity, material_key, cepci_idx):
    eq = EQUIPMENT_DB[equip_key]
    log_A = np.log10(capacity)
    log_Cp = eq['k'][0] + eq['k'][1]*log_A + eq['k'][2]*(log_A**2)
    base_cost = 10**log_Cp
    total_cost = base_cost * eq['bm'] * MATERIAL_FACTORS[material_key]
    current_cost = total_cost * (cepci_idx / 397) # Base 2001
    return current_cost

# --- 5. DASHBOARD LAYOUT ---

# Sidebar: Controls Only
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2504/2504928.png", width=40)
    st.markdown("### Project Controls")
    st.markdown("---")
    
    # Input 1: Equipment
    selected_eq = st.selectbox("Equipment Type", list(EQUIPMENT_DB.keys()))
    eq_data = EQUIPMENT_DB[selected_eq]
    
    # Input 2: Capacity (BUG FIX: Explicit Float Casting)
    st.markdown(f"**Design Capacity ({eq_data['unit']})**")
    min_val = float(eq_data['min'])
    max_val = float(eq_data['max'])
    default_val = float(min_val)
    
    capacity = st.slider("Select Capacity", 
                         min_value=min_val, 
                         max_value=max_val, 
                         value=default_val,
                         label_visibility="collapsed")
    
    # Input 3: Material
    selected_mat = st.selectbox("Material Class", list(MATERIAL_FACTORS.keys()))
    
    st.markdown("---")
    
    # Input 4: Economics
    st.markdown("**Economic Basis**")
    cepci = st.number_input("CEPCI Index", value=815)
    usd_rate = st.number_input("USD/IDR Rate", value=15850, step=50)
    
    st.markdown("---")
    st.caption("v5.1 Stable | Enterprise Edition")


# Main Content Area
st.markdown("### Capital Expenditure Estimator")
st.markdown("Parametric cost estimation based on **Turton et al. (2018)** methodology.")
st.markdown("<br>", unsafe_allow_html=True)

# Perform Calculation
cost_usd = calculate_capex(selected_eq, capacity, selected_mat, cepci)
cost_idr = cost_usd * usd_rate

# --- ROW 1: THE "MONEY SHOT" (Highlight Card) ---
c1, c2 = st.columns([1, 2])

with c1:
    st.markdown(f"""
    <div class="result-card">
        <div style="opacity: 0.8; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Total Estimated Cost</div>
        <div class="value-white">Rp {cost_idr/1000000:,.0f} <span style="font-size:16px">Juta</span></div>
        <div style="background: rgba(255,255,255,0.2); padding: 5px 10px; border-radius: 20px; display: inline-block; font-size: 12px;">
            USD {cost_usd:,.0f}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Detail Card Below Money Shot
    st.markdown(f"""
    <div class="premium-card">
        <div class="label-small">CONFIGURATION</div>
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:#64748b">Equipment</span>
            <span style="font-weight:600; color:#0f172a">{selected_eq}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
            <span style="color:#64748b">Capacity</span>
            <span style="font-weight:600; color:#0f172a">{capacity} {eq_data['unit']}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="color:#64748b">Material</span>
            <span style="font-weight:600; color:#0f172a">{selected_mat}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    # --- CHART (Professional White Theme) ---
    st.markdown(f"""
    <div class="premium-card" style="height: 100%;">
        <div class="label-small">COST SENSITIVITY ANALYSIS</div>
        <h4 style="margin-top:0; margin-bottom:20px;">Impact of Capacity on Price</h4>
    """, unsafe_allow_html=True)
    
    # Generate Data
    x_range = np.linspace(min_val, max_val, 100)
    y_range = [calculate_capex(selected_eq, x, selected_mat, cepci) * usd_rate for x in x_range]
    
    fig = go.Figure()
    
    # Line
    fig.add_trace(go.Scatter(
        x=x_range, y=y_range,
        mode='lines',
        line=dict(color='#2563eb', width=3), # Royal Blue
        name='Cost Curve'
    ))
    
    # Point
    fig.add_trace(go.Scatter(
        x=[capacity], y=[cost_idr],
        mode='markers',
        marker=dict(color='#1e40af', size=14, line=dict(color='white', width=2)),
        name='Current Selection'
    ))
    
    fig.update_layout(
        template="plotly_white", # Theme Putih Bersih
        margin=dict(l=0, r=0, t=0, b=0),
        height=320,
        xaxis=dict(title=f"Capacity ({eq_data['unit']})", showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(title="Cost (IDR)", showgrid=True, gridcolor='#f1f5f9', tickformat=".2s"),
        hovermode="x unified",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True) # End Card

# --- FOOTER ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
    <div style="text-align: center; color: #94a3b8; font-size: 12px;">
        System ID: ENG-EST-2025 • Data Source: Turton et al. (2018) • Currency: Real-time Input
    </div>
""", unsafe_allow_html=True)
