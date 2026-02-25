import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "quality_logs.csv"

# Comprehensive List of Stages with their specific data requirements
STAGE_REFS = {
    "RM Inspection": "Heat No / Plate No",
    "Marking": "Drawing Rev No",
    "Dimensional Inspection": "Report No / Drawing Ref",
    "Fit-up": "Joint No / Seam No",
    "Welding": "Welder Stamp / ID",
    "Grinding": "Wheel Type used",
    "Buffing": "Grit Size / Surface RA",
    "DP / LPI": "Report No / Batch No",
    "Hydro Test": "Test Pressure (kg/cm2)",
    "Pneumatic Test": "Test Pressure (kg/cm2)",
    "Drive Trail Run": "Motor ID / RPM / Observations",
    "PMI (Material Check)": "Report No / Heat No",
    "PDIR (Pre-Dispatch)": "Packing List Ref",
    "Final Inspection": "QC Release Note No"
}

st.set_page_config(page_title="B&G Quality Master", layout="wide")
st.title("🛡️ B&G Quality Control")

# --- 2. DATA LOAD ---
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Job_Code", "Inspector", "Stage", "Reference_Data", "Result", "Remarks", "Photo"])

# --- 3. QUALITY INSPECTION FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        job_code = st.text_input("Job Code (e.g. SSR501)").upper()
        inspector = st.selectbox("Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
        # New Expanded Stages
        stage = st.selectbox("Inspection Stage", list(STAGE_REFS.keys()))
        
    with col2:
        # This field changes its label based on the Stage selected above
        ref_label = STAGE_REFS[stage]
        ref_data = st.text_input(f"Reference: {ref_label}")
        result = st.radio("Status", ["✅ PASSED", "⚠️ REWORK", "❌ FAILED"])
        remarks = st.text_area("Observations / Technical Remarks")

    cam_photo = st.camera_input("Take Photo (Heat No / Test Gauge / Work Status)")
    
    if st.form_submit_button("Submit Quality Record"):
        img_str = ""
        if cam_photo:
            img = Image.open(cam_photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
        
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
            "Job_Code": job_code,
            "Inspector": inspector,
            "Stage": stage,
            "Reference_Data": ref_data,
            "Result": result,
            "Remarks": remarks,
            "Photo": img_str
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success(f"Quality record for {stage} saved for Job {job_code}")
        st.rerun()

# --- 4. VIEW LOGS & PHOTOS ---
st.divider()
st.subheader("📋 Quality Audit History")

if not df.empty:
    # Main Table
    st.dataframe(df.drop(columns=["Photo"]).sort_values(by="Timestamp", ascending=False), use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Official Excel Report", csv, "bg_quality_audit.csv", "text/csv")

    # Photo Gallery
    st.divider()
    st.subheader("🖼️ Visual Traceability (Photos)")
    view_job = st.selectbox("Filter Photos by Job Code", ["-- Select Job --"] + list(df['Job_Code'].unique()))
    
    if view_job != "-- Select Job --":
        job_photos = df[df['Job_Code'] == view_job]
        for _, row in job_photos.iterrows():
            if isinstance(row['Photo'], str) and len(row['Photo']) > 0:
                with st.container():
                    c_txt, c_img = st.columns([1, 2])
                    with c_txt:
                        st.write(f"**Stage:** {row['Stage']}")
                        st.write(f"**Ref:** {row['Reference_Data']}")
                        st.write(f"**Result:** {row['Result']}")
                        st.write(f"**Time:** {row['Timestamp']}")
                    with c_img:
                        img_bytes = base64.b64decode(row['Photo'])
                        st.image(img_bytes, width=450)
                st.divider()
else:
    st.info("No records found yet.")
