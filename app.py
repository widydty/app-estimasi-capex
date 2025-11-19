import streamlit as st
import pandas as pd
import numpy as np
import fluids
from fluids.units import *
import plotly.express as px

# --- CONFIG ---
st.set_page_config(page_title="HydroGuard | Hydraulic Auditor", layout="wide", page_icon="💧")

# --- CSS UNTUK TABEL WARNA-WARNI ---
st.markdown("""
    <style>
        .stApp { background-color: #f4f4f4; }
        h1 { color: #003366; }
        div[data-testid="stMetricValue"] { font-size: 24px; }
        .status-ok { color: green; font-weight: bold; }
        .status-fail { color: red; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- ENGINE PERHITUNGAN (FLUIDS LIBRARY) ---
def calculate_hydraulics(df):
    results = []
    
    for index, row in df.iterrows():
        try:
            # Ambil data dari row
            flow_kg_h = row['Flowrate (kg/h)']
            dens = row['Density (kg/m3)']
            visc_cp = row['Viscosity (cP)']
            press_bar = row['Pressure (bar)']
            size_nps = row['Line Size (NPS)']
            length = row['Length (m)']
            phase = row['Phase'] # Liquid / Gas
            
            # 1. Convert NPS to Inner Diameter (Schedule 40 Standard)
            # Menggunakan pendekatan sederhana untuk ID jika library detail tidak load
            # Di production grade, gunakan fluids.piping.nearest_pipe
            di_map = {2: 0.0525, 3: 0.0779, 4: 0.1023, 6: 0.1541, 8: 0.2027, 10: 0.2545, 12: 0.3048}
            ID = di_map.get(size_nps, size_nps * 0.0254) # Fallback inch to meter
            
            # 2. Flow Calculation
            area = np.pi * (ID/2)**2
            flow_kg_s = flow_kg_h / 3600
            vol_flow = flow_kg_s / dens
            velocity = vol_flow / area
            
            # 3. Reynolds Number
            visc_pa_s = visc_cp / 1000
            Re = fluids.core.Reynolds(V=velocity, D=ID, rho=dens, mu=visc_pa_s)
            
            # 4. Friction Factor (Darcy)
            roughness = 4.57e-5 # Commercial Steel
            fd = fluids.friction.friction_factor(Re=Re, eD=roughness/ID)
            
            # 5. Pressure Drop (Darcy-Weisbach)
            dP_pa = fluids.core.P_Darcy(D=ID, L=length, f=fd, rho=dens, V=velocity)
            dP_bar = dP_pa / 1e5
            dP_per_100m = (dP_bar / length) * 100
            
            # 6. Rho-v2 Calculation (Momentum)
            rhov2 = dens * (velocity**2)
            
            # 7. SAFETY CHECK (CRITERIA)
            status = "PASS"
            notes = []
            
            # Cek Liquid Velocity
            if phase == "Liquid" and velocity > 3.0:
                status = "FAIL"
                notes.append("High Vel (>3 m/s)")
            
            # Cek Gas Velocity
            if phase == "Gas" and velocity > 20.0:
                status = "FAIL"
                notes.append("High Vel (>20 m/s)")
                
            # Cek Rho-v2 (Vibration Risk API 14E)
            if rhov2 > 200000: # Limit umum piping
                status = "FAIL"
                notes.append("High Vib (Rho-v2)")
                
            # Cek Pressure Drop
            limit_dp = 0.5 if phase == "Liquid" else 0.1 # bar/100m
            if dP_per_100m > limit_dp:
                status = "FAIL"
                notes.append(f"High dP (>{limit_dp} bar/100m)")

            results.append({
                "Stream Name": row['Stream Name'],
                "Velocity (m/s)": round(velocity, 2),
                "dP (bar/100m)": round(dP_per_100m, 3),
                "Rho-v2": round(rhov2, 0),
                "Re": int(Re),
                "Status": status,
                "Notes": ", ".join(notes) if notes else "OK"
            })
            
        except Exception as e:
            results.append({"Stream Name": row['Stream Name'], "Status": "ERROR", "Notes": str(e)})
            
    return pd.DataFrame(results)

# --- UI LAYOUT ---
st.title("🛡️ HydroGuard Engineering Auditor")
st.markdown("### Automated Piping Hydraulics & Safety Check System")
st.info("Upload data pipa Anda, sistem akan melakukan audit velocity, pressure drop, dan risiko vibrasi (API 14E) secara otomatis.")

# --- 1. INPUT SECTION ---
col_ctrl, col_template = st.columns([1, 2])

with col_ctrl:
    st.subheader("1. Input Data")
    st.write("Silakan isi parameter di tabel sebelah kanan atau paste dari Excel.")
    
    # Template Data Generator
    default_data = pd.DataFrame([
        {"Stream Name": "Feed Pump Suction", "Flowrate (kg/h)": 50000, "Density (kg/m3)": 980, "Viscosity (cP)": 1.2, "Pressure (bar)": 2, "Line Size (NPS)": 6, "Length (m)": 50, "Phase": "Liquid"},
        {"Stream Name": "Feed Pump Discharge", "Flowrate (kg/h)": 50000, "Density (kg/m3)": 980, "Viscosity (cP)": 1.2, "Pressure (bar)": 25, "Line Size (NPS)": 4, "Length (m)": 120, "Phase": "Liquid"},
        {"Stream Name": "Gas Outlet", "Flowrate (kg/h)": 15000, "Density (kg/m3)": 12, "Viscosity (cP)": 0.02, "Pressure (bar)": 10, "Line Size (NPS)": 8, "Length (m)": 200, "Phase": "Gas"},
        {"Stream Name": "High Velocity Case", "Flowrate (kg/h)": 80000, "Density (kg/m3)": 950, "Viscosity (cP)": 1.0, "Pressure (bar)": 5, "Line Size (NPS)": 3, "Length (m)": 20, "Phase": "Liquid"},
    ])

with col_template:
    # Editable Dataframe (Fitur Mewah Streamlit)
    input_df = st.data_editor(default_data, num_rows="dynamic", use_container_width=True)

# --- 2. EXECUTION ---
if st.button("🚀 RUN HYDRAULIC SIMULATION", type="primary"):
    
    result_df = calculate_hydraulics(input_df)
    
    # Gabungkan Input + Output
    final_df = pd.concat([input_df.reset_index(drop=True), result_df.reset_index(drop=True)], axis=1)
    # Hapus kolom stream name duplikat
    final_df = final_df.loc[:,~final_df.columns.duplicated()]

    # --- 3. DASHBOARD HASIL ---
    st.divider()
    st.subheader("📊 Audit Report")
    
    # Summary Metrics
    total_lines = len(final_df)
    failed_lines = len(final_df[final_df['Status'] == "FAIL"])
    pass_lines = total_lines - failed_lines
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Lines Checked", total_lines)
    m2.metric("Lines Passed ✅", pass_lines)
    m3.metric("Lines Failed ❌", failed_lines, delta_color="inverse")
    
    # Visualisasi Gagal vs Berhasil
    if failed_lines > 0:
        st.warning(f"⚠️ Perhatian: Ditemukan {failed_lines} line pipa yang melanggar kriteria desain!")
    else:
        st.success("✅ Semua desain aman dan memenuhi standar.")

    # --- TABEL DETAIL DENGAN WARNA ---
    # Menggunakan Styler Pandas untuk mewarnai baris
    def highlight_status(val):
        color = '#ffcdd2' if val == 'FAIL' else '#c8e6c9'
        return f'background-color: {color}'

    st.dataframe(
        final_df.style.applymap(highlight_status, subset=['Status']),
        use_container_width=True
    )
    
    # --- GRAFIK ANALISA ---
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Scatter Plot Velocity vs Line Size
        fig = px.scatter(final_df, x="Line Size (NPS)", y="Velocity (m/s)", 
                         color="Status", size="Flowrate (kg/h)",
                         hover_data=["Stream Name"], title="Velocity Profile Audit")
        # Tambah garis batas
        fig.add_hline(y=3, line_dash="dot", annotation_text="Max Liquid Limit (3 m/s)", annotation_position="top right")
        st.plotly_chart(fig, use_container_width=True)
        
    with col_g2:
        # Bar Chart Failure Reasons
        if failed_lines > 0:
            fail_data = final_df[final_df['Status'] == 'FAIL']
            # Pecah notes jika ada multiple error
            all_notes = []
            for note in fail_data['Notes']:
                all_notes.extend(note.split(", "))
            
            counts = pd.Series(all_notes).value_counts().reset_index()
            counts.columns = ['Issue', 'Count']
            
            fig2 = px.bar(counts, x='Count', y='Issue', orientation='h', title="Top Design Violations", color='Count')
            st.plotly_chart(fig2, use_container_width=True)

    # Download Button
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Excel Report",
        data=csv,
        file_name='Hydraulic_Audit_Report.csv',
        mime='text/csv',
    )
