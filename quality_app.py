import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image

# --- 1. CONFIGURATION & TIMEZONE ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "bg_master_logs.csv"

# Industrial Units & Consumables Mapping
ACTIVITY_DATA = {
    "Welding": {"unit": "Meters (Mts)", "consumable": "Electrode Batch No."},
    "Grinding": {"unit": "Mts / Nos", "consumable": "Wheel Type (SS/MS)"},
    "Buffing": {"unit": "Sq Ft", "consumable": "Grit Size (60-400)"},
    "Drilling": {"unit": "Quantity (Nos)", "consumable": "Bit Size"},
    "Cutting (CNC/Plasma)": {"unit": "Meters (Mts)", "consumable": "Nozzle/Gas Type"},
    "RM Inspection": {"unit": "Qty (Nos)", "consumable": "Heat / Plate No."}
}

st.set_page_config(page_title="B&G Master Pro", layout="wide")
st.title("🏗️ B&G Engineering Master Monitor")

# --- 2. DATA LOADING HELPER ---
def get_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame()

# --- 3. ENTRY FORM ---
with st.form("master_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Primary Details")
        supervisor = st.selectbox("Supervisor / Inspector", ["Prasanth", "RamaSai", "Subodth", "Naresh"])
        worker_cat = st.selectbox("Category", ["Welder (IBR)", "Fitter", "Grinder", "Quality Inspector"])
        job_code = st.text_input("Job Code (e.g., SSR501)", placeholder="Enter Project ID")
        activity = st.selectbox("Activity Type", list(ACTIVITY_DATA.keys()))

    with col2:
        st.subheader("🛠️ Technical Specs")
        unit = ACTIVITY_DATA[activity]["unit"]
        cons_label = ACTIVITY_DATA[activity]["consumable"]
        
        output_val = st.number_input(f"Output ({unit})", min_value=0.0)
        traceability = st.text_input(f"Traceability: {cons_label}")
        notes = st.text_area("Technical Remarks (Material, Batch, Soap type etc.)")

    # Photo Capture (Optimized for iPhone/Browser)
    st.subheader("📸 Evidence Capture")
    cam_photo = st.camera_input("Take Photo of Heat No. / Work Progress")
    
    if st.form_submit_button("🚀 Submit Secure Record"):
        # Time Management
        timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        
        # Image Processing
        img_str = ""
        if cam_photo:
            img = Image.open(cam_photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        # Prepare Row
        new_row = pd.DataFrame([{
            "Timestamp": timestamp,
            "Job": job_code.upper(),
            "Activity": activity,
            "Supervisor": supervisor,
            "Category": worker_cat,
            "Output": output_val,
            "Unit": unit,
            "Traceability": traceability,
            "Remarks": notes,
            "Photo": img_str
        }])
        
        # Save Logic
        df = get_data()
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        
        st.success(f"✅ Record Secured for {job_code} at {timestamp}")
        st.balloons()
        st.rerun()

# --- 4. PROJECT SUMMARY & ANALYTICS ---
st.divider()
df_main = get_data()

if not df_main.empty:
    tab1, tab2 = st.tabs(["📊 Project Summary", "🔍 Detailed Logs"])
    
    with tab1:
        st.subheader("Material & Progress Summary")
        summary = df_main.groupby(['Job', 'Activity']).agg({
            'Output': 'sum',
            'Traceability': lambda x: ', '.join(set(x.dropna().astype(str))),
            'Timestamp': 'count'
        }).rename(columns={'Timestamp': 'Entries'})
        st.table(summary)
        
    with tab2:
        # Hide photo string from table for clarity
        st.dataframe(df_main.drop(columns=['Photo']).sort_values(by="Timestamp", ascending=False), use_container_width=True)
        
        # Export Option
        csv = df_main.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Master Data (Excel)", csv, f"BG_Master_{datetime.now(IST).strftime('%Y%m%d')}.csv")
else:
    st.info("No records found in shopfloor memory.")
