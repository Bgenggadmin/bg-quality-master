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

st.set_page_config(page_title="B&G Quality Master")
st.title("🛡️ B&G Quality Control")

# --- 2. DATA LOAD ---
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Job_Code", "Inspector", "Stage", "Ref_No", "Result", "Remarks", "Photo"])

# --- 3. SIMPLE INSPECTION FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        job_code = st.text_input("Job Code (e.g. SSR501)").upper()
        ref_no = st.text_input("Heat No / Joint No / Report No")
        inspector = st.selectbox("Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
    with col2:
        stage = st.selectbox("Stage", ["RM Inspection", "Fit-up", "Welding", "Final Inspection"])
        result = st.radio("Result", ["✅ Pass", "⚠️ Rework", "❌ Fail"])
        remarks = st.text_area("Observations / Remarks")

    cam_photo = st.camera_input("Take Photo (Heat No / Markings)")
    
    if st.form_submit_button("Submit Quality Record"):
        # Image to String
        img_str = ""
        if cam_photo:
            img = Image.open(cam_photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # New Entry
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
            "Job_Code": job_code,
            "Inspector": inspector,
            "Stage": stage,
            "Ref_No": ref_no,
            "Result": result,
            "Remarks": remarks,
            "Photo": img_str
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success(f"Saved successfully for {job_code}!")
        st.rerun()

# --- 4. VIEW LOGS & PHOTOS ---
st.divider()
st.subheader("📋 Recent Quality Logs")

if not df.empty:
    # Display the table (Hide the long Photo code for neatness)
    st.dataframe(df.drop(columns=["Photo"]).sort_values(by="Timestamp", ascending=False), use_container_width=True)
    
    # Download Button
    csv = df
