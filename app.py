import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="ProCAPEX Estimator", layout="wide", page_icon="🏗️")

# CSS for Enterprise Look (Clean, Shadow, Radius)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        
        .stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }
        
        /* Container Cards */
        .css-1r6slb0 {
            background-color: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            border: 1px solid #e9ecef;
        }
        
        /* Metric Style */
        div[data-testid="stMetricValue"] {
            font-size: 28px;
            color: #0056b3;
            font-weight: 800;
        }
        
        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e9ecef;
        }
        
        /* Headers */
        h1, h2, h3 { color: #1a1a1a !important; letter-spacing: -0.5px; }
        
        /* Custom Success Box */
        .success-box {
            padding: 15px;
            background-color: #d4edda;
            color: #155724;
            border-radius: 8px;
            border: 1px solid #c3e6cb;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

# --- 2. COMPREHENSIVE EQUIPMENT DATABASE (TURTON & GUTHRIE PARAMETERS) ---
# K values for log10(Cp) = K1 + K2*log(A) + K3*log(A)^2
# Min/Max in specific units
DB = {
    "FLUID DRIVERS": {
        "Centrifugal Pump (ANSI)": {"k": [3.3892, 0.0536, 0.1538], "unit": "kW", "min": 1, "max": 300, "bm": 3.30},
        "Centrifugal Pump (API 610)": {"k": [3.8696, 0.3161, 0.1220], "unit": "kW", "min": 10, "max": 1000, "bm": 3.80},
        "Positive Displacement Pump": {"k": [3.4771, 0.1350, 0.1438], "unit": "kW", "min": 1, "max": 200, "bm": 3.30},
        "Compressor (Centrifugal)": {"k": [2.2891, 1.3604, -0.1027], "unit": "kW", "min": 450, "max": 3000, "bm": 2.15},
        "Compressor (Screw)": {"k": [2.4493, 0.9765, -0.0263], "unit": "kW", "min": 10, "max": 800, "bm": 2.15},
        "Fan / Blower": {"k": [3.1761, 0.6312, 0.0598], "unit": "m3/s", "min": 1, "max": 100, "bm": 2.15},
    },
    "HEAT TRANSFER": {
        "Shell & Tube (Floating Head)": {"k": [4.8306, -0.8509, 0.3187], "unit": "m2", "min": 10, "max": 1000, "bm": 3.17},
        "Shell & Tube (Fixed Sheet)": {"k": [4.3247, -0.3030, 0.1634], "unit": "m2", "min": 10, "max": 1000, "bm": 3.17},
        "Reboiler (Kettle)": {"k": [4.4646, -0.5277, 0.3955], "unit": "m2", "min": 10, "max": 100, "bm": 3.17},
        "Air Cooler (Fin Fan)": {"k": [4.0336, 0.2341, 0.0497], "unit": "m2", "min": 10, "max": 1000, "bm": 2.50},
        "Plate & Frame HE": {"k": [4.6656, -0.1557, 0.1547], "unit": "m2", "min": 10, "max": 500, "bm": 2.00},
    },
    "VESSELS & STORAGE": {
        "Pressure Vessel (Vertical)": {"k": [3.4974, 0.4485, 0.1074], "unit": "m3", "min": 0.3, "max": 100, "bm": 4.16},
        "Pressure Vessel (Horizontal)": {"k": [3.5565, 0.3776, 0.0905], "unit": "m3", "min": 0.3, "max": 100, "bm": 4.16},
        "Storage Tank (API 650 Flat)": {"k": [4.8509, -0.3973, 0.1445], "unit": "m3", "min": 100, "max": 40000, "bm": 1.50},
        "Spherical Tank (API 620)": {"k": [4.0000, 0.4000, 0.1000], "unit": "m3", "min": 500, "max": 5000, "bm": 2.50},
        "Hopper / Silo": {"k": [3.2000, 0.4500, 0.1100], "unit": "m3", "min": 10, "max": 1000, "bm": 1.80},
    },
    "SOLIDS HANDLING": {
        "Belt Conveyor": {"k": [3.6638, 0.8666, -0.0352], "unit": "m2 (Area)", "min": 10, "max": 2000, "bm": 1.60},
        "Screw Conveyor": {"k": [3.1974, 0.7435, 0.0346], "unit": "m2 (Area)", "min": 2, "max": 200, "bm": 1.60},
        "Bucket Elevator": {"k": [3.4000, 0.6000, 0.0500], "unit": "m (Height)", "min": 5, "max": 50, "bm": 2.00},
        "Crusher / Grinder": {"k": [3.2362, 0.1559, 0.2449], "unit": "kW", "min": 10, "max": 1000, "bm": 2.00},
        "Dust Collector (Cyclone)": {"k": [2.9886, 0.6457, 0.0923], "unit": "m2", "min": 1, "max": 100, "bm": 2.60},
    },
    "COLUMNS & REACTORS": {
        "Distillation Column (Tray)": {"k": [2.9949, 0.4465, 0.3961], "unit": "m (Height)", "min": 2, "max": 100, "bm": 4.16},
        "Distillation Column (Packed)": {"k": [3.1000, 0.5000, 0.3500], "unit": "m (Height)", "min": 2, "max": 100, "bm": 4.16},
        "Reactor (CSTR - Jacketed)": {"k": [3.6000, 0.4000, 0.1200], "unit": "m3", "min": 0.5, "max": 50, "bm": 4.00},
    }
}

MATERIAL_FACTORS = {
    "Carbon Steel (A285/A516)": 1.0,
    "Stainless Steel 304": 1.3,
    "Stainless Steel 316": 1.5,
    "Duplex Stainless Steel": 1.8,
    "Nickel Alloy (Monel/Inconel)": 3.6,
    "Titanium": 4.4
}

# --- 3. CALCULATION LOGIC (ROBUST) ---
def calculate_cost(cat, subtype, capacity, pressure, mat_key, cepci_idx):
    try:
        eq_data = DB[cat][subtype]
        k = eq_data['k']
        
        # Base Cost (2001)
        log_a = np.log10(capacity)
        log_cp = k[0] + k[1]*log_a + k[2]*(log_a**2)
        base_cost_2001 = 10**log_cp
        
        # Pressure Factor (Simplified correlation for estimation)
        # Fp = 1 for P < 5 bar. Fp increases with log P.
        fp = 1.0
        if pressure > 5:
            fp = 10**(0.125 * np.log10(pressure/5) + 0.08)
        
        # Material Factor
        fm = MATERIAL_FACTORS[mat_key]
        
        # Bare Module Factor (Installation)
        fbm = eq_data['bm']
        
        # Final Calculation
        # C_module = C_base * Fbm * Fm * Fp * (CEPCI_now / CEPCI_base)
        total_usd = base_cost_2001 * fbm * fm * fp * (cepci_idx / 397)
        
        return total_usd, fp, fm
    except Exception as e:
        return 0, 1, 1

# --- 4. UI LAYOUT ---

# Sidebar Controls
with st.sidebar:
    st.title("🎛️ Control Panel")
    
    category = st.selectbox("1. Equipment Category", list(DB.keys()))
    subtype = st.selectbox("2. Specific Equipment", list(DB[category].keys()))
    
    # Dynamic Limits based on DB
    limits = DB[category][subtype]
    st.markdown(f"**3. Capacity ({limits['unit']})**")
    capacity = st.number_input(
        "Enter Value", 
        min_value=float(limits['min']), 
        max_value=float(limits['max']), 
        value=float(limits['min'])
    )
    
    st.markdown("**4. Design Parameters**")
    pressure = st.number_input("Pressure (barg)", value=1.0, min_value=0.0)
    material = st.selectbox("Material", list(MATERIAL_FACTORS.keys()))
    
    st.markdown("---")
    st.markdown("**5. Economics**")
    cepci = st.number_input("CEPCI Index", value=820)
    kurs = st.number_input("USD/IDR Rate", value=15900)

# Main Content
st.title("ENGINEERING CAPEX ESTIMATOR")
st.markdown("### Class 5 Parametric Estimation System")
st.markdown("---")

# Perform Calculation
cost_usd, fp, fm = calculate_cost(category, subtype, capacity, pressure, material, cepci)
cost_idr = cost_usd * kurs

if cost_usd > 0:
    # --- RESULT CARDS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Estimated Cost (IDR)", f"Rp {cost_idr:,.0f}")
    with c2:
        st.metric("Valuation (USD)", f"${cost_usd:,.0f}")
    with c3:
        st.metric("Bare Module Factor", f"{DB[category][subtype]['bm']}x")

    # --- DETAIL TABS ---
    tab1, tab2 = st.tabs(["📄 Datasheet Specification", "📊 Cost Breakdown"])

    with tab1:
        # Create a clean DataFrame for the Datasheet
        ds_data = {
            "Parameter": [
                "Equipment Item", "Category", "Design Capacity", "Design Pressure", 
                "Material of Construction", "Pressure Factor (Fp)", "Material Factor (Fm)", 
                "Inflation Index (CEPCI)"
            ],
            "Value": [
                subtype, category, f"{capacity} {limits['unit']}", f"{pressure} barg",
                material, f"{fp:.2f}", f"{fm:.2f}", cepci
            ]
        }
        df_ds = pd.DataFrame(ds_data)
        
        # Use Streamlit Dataframe for clean look (No HTML hacking)
        st.dataframe(
            df_ds, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Parameter": st.column_config.TextColumn("Parameter", width="medium"),
                "Value": st.column_config.TextColumn("Specification", width="large")
            }
        )
        
        st.info("ℹ️ **Note:** Estimated cost includes Equipment (FOB), Piping, Concrete, Steel, Inst. & Elec, Insulation, Paint, and Direct Labor.")

    with tab2:
        # Visualizing the Cost Components (Simulation)
        # Typically: Material ~55%, Labor ~30%, Indirects ~15%
        labels = ['Equipment Material', 'Direct Labor', 'Construction Indirects', 'Contingency']
        values = [cost_idr * 0.55, cost_idr * 0.30, cost_idr * 0.10, cost_idr * 0.05]
        
        fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
        fig.update_layout(
            title_text="Estimated Project Cost Structure",
            annotations=[dict(text='CAPEX', x=0.5, y=0.5, font_size=20, showarrow=False)]
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.error("Calculation Error. Please check input limits.")

# --- FOOTER ---
st.markdown("---")
st.caption("System Version 5.0 | Reference: Turton, Bailie, Whiting, Shaeiwitz (2018) & Matches Engineering.")
