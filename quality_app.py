import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image

# --- 1. CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
QUALITY_DB = "quality_traceability_logs.csv"

# Specialized Quality Inspection Categories
INSPECTION_TYPES = {
    "RM Inspection": "Heat / Plate / Batch No.",
    "Fit-up Inspection": "Joint / Seam No.",
    "Weld Visual": "Welder ID & Stamp",
    "PMI / LPI / UT": "Report Reference No.",
    "Hydro / Pneumatic": "Test Pressure & Gauge ID",
    "Final Dimension": "Drawing Revision No."
}

st.set_page_config(page_title="B&G Quality Master", layout="wide")
st.title("🛡️ B&G Quality & Traceability Control")

# --- 2. DATA UTILITY ---
def get_quality_data():
    if os.path.exists(QUALITY_DB):
        return pd.read_csv(QUALITY_DB)
    return pd.DataFrame()

# --- 3. INSPECTION FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Inspection Context")
        inspector = st.selectbox("QC Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
        job_code = st.text_input("Job Code (e.g., SSR501)", placeholder="Enter Project ID")
        stage = st.selectbox("Inspection Stage", list(INSPECTION_TYPES.keys()))
        traceability_ref = st.text_input(f"Critical Ref: {INSPECTION_TYPES[stage]}")

    with col2:
        st.subheader("✅ Result & Remarks")
        result = st.radio("Inspection Result", ["🟢 Pass", "🟡 Rework Required", "🔴 Fail / Hold"])
        
        # Specific for Quality: Material Grade & Thickness
        mat_grade = st.selectbox("Material Grade", ["SS316L", "SS304", "SS310", "Carbon Steel", "Other"])
        observations = st.text_area("Observations (e.g. Rough edges, Heat No. verified, MTC checked)")

    st.subheader("📸 Evidence Capture")
    st.info("Take a clear photo of the Heat Number Stencil or the specific defect.")
    cam_photo = st.camera_input("Capture Inspection Proof")
    
    if st.form_submit_button("🚀 Secure Quality Record"):
        timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        
        # Process Image
        img_str = ""
        if cam_photo:
            img = Image.open(cam_photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        # Prepare Quality Row
        new_entry = pd.DataFrame([{
            "Timestamp": timestamp,
            "Job_Code": job_code.upper(),
            "Inspector": inspector,
            "Stage": stage,
            "Ref_No": traceability_ref,
            "Material": mat_grade,
            "Result": result,
            "Remarks": observations,
            "Photo_Proof": img_str
        }])
        
        # Save to Local Storage
        df = get_quality_data()
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_csv(QUALITY_DB, index=False)
        
        st.success(f"Quality Record for {job_code} secured at {timestamp}!")
        st.balloons()
        st.rerun()

# --- 4. MATERIAL SUMMARY & TRACEABILITY REPORT ---
st.divider()
df_q = get_quality_data()

if not df_q.empty:
    tab1, tab2 = st.tabs(["📊 Job Traceability Summary", "🔍 Full Audit Log"])
    
    with tab1:
        st.subheader("Material Traceability Map")
        # Filters unique heat numbers and refs per job
        summary = df_q.groupby(['Job_Code', 'Stage']).agg({
            'Ref_No': lambda x: ', '.join(set(x.dropna().astype(str))),
            'Result': 'last',
            'Timestamp': 'max'
        }).rename(columns={'Timestamp': 'Last Inspected'})
        st.table(summary)
        
    with tab2:
        st.dataframe(df_q.drop(columns=['Photo_Proof']).sort_values(by="Timestamp", ascending=False), use_container_width=True)
        
        csv = df_q.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Quality Data for MTC Data Book", csv, f"BG_Quality_{datetime.now(IST).strftime('%Y%m%d')}.csv")
else:
    st.info("No quality inspections recorded yet.")
