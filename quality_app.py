import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import os

# --- 1. SETUP LOCAL STORAGE ---
QUALITY_LOGS = "quality_logs.csv"
INSPECTORS_FILE = "inspectors.txt"
JOBS_FILE = "jobs_quality.txt"

def load_list(file_path, defaults):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return defaults

def save_list(file_path, data_list):
    with open(file_path, "w") as f:
        for item in data_list:
            f.write(f"{item}\n")

# Load existing lists
inspectors = load_list(INSPECTORS_FILE, ["Prasanth", "RamaSai", "Subodth", "Naresh"])
job_list = load_list(JOBS_FILE, ["SSR501", "SSR502"])

st.title("✅ B&G Quality Master")

# --- 2. ADMIN PANEL (Manage Inspectors & Jobs) ---
with st.expander("⚙️ ADMIN: Add/Remove Inspectors & Job Codes"):
    tab1, tab2 = st.tabs(["Inspectors", "Job Codes"])
    
    with tab1:
        new_ins = st.text_input("New Inspector Name")
        if st.button("➕ Add Inspector"):
            if new_ins and new_ins not in inspectors:
                inspectors.append(new_ins)
                save_list(INSPECTORS_FILE, inspectors)
                st.rerun()
        
        ins_to_remove = st.selectbox("Remove Inspector", ["-- Select --"] + inspectors)
        if st.button("🗑️ Delete Inspector"):
            if ins_to_remove != "-- Select --":
                inspectors.remove(ins_to_remove)
                save_list(INSPECTORS_FILE, inspectors)
                st.rerun()

    with tab2:
        new_job = st.text_input("New Quality Job Code")
        if st.button("➕ Add Quality Job"):
            if new_job and new_job not in job_list:
                job_list.append(new_job)
                save_list(JOBS_FILE, job_list)
                st.rerun()
        
        job_to_remove = st.selectbox("Remove Quality Job", ["-- Select --"] + job_list)
        if st.button("🗑️ Delete Quality Job"):
            if job_to_remove != "-- Select --":
                job_list.remove(job_to_remove)
                save_list(JOBS_FILE, job_list)
                st.rerun()

# --- 3. INSPECTION FORM (With Camera & Notes) ---
st.divider()
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        sel_inspector = st.selectbox("Inspector", inspectors)
        sel_job = st.selectbox("Job Code", job_list)
        stage = st.selectbox("Stage", ["Marking", "Fitup", "PMI", "Hydro", "Final"])
    with col2:
        status = st.radio("Status", ["🟢 Passed", "🔴 Rework"])
        notes = st.text_area("📋 Technical Notes / Observations")

    photo = st.camera_input("Take Shopfloor Photo")
    
    if st.form_submit_button("Submit Quality Record"):
        img_str = "No Photo"
        if photo:
            img = Image.open(photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        new_entry = pd.DataFrame([{
            "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "Inspector": sel_inspector,
            "Job_Code": sel_job,
            "Stage": stage,
            "Status": status,
            "Notes": notes,
            "Photo": img_str
        }])
        
        if os.path.exists(QUALITY_LOGS):
            df = pd.read_csv(QUALITY_LOGS)
            df = pd.concat([df, new_entry], ignore_index=True)
        else:
            df = new_entry
        df.to_csv(QUALITY_LOGS, index=False)
        st.success(f"Inspection for {sel_job} saved!")
        st.balloons()

# --- 4. VIEW & EXPORT ---
st.divider()
if os.path.exists(QUALITY_LOGS):
    df_view = pd.read_csv(QUALITY_LOGS)
    st.download_button("📥 DOWNLOAD QUALITY DATA", df_view.to_csv(index=False), "bg_quality_data.csv")
    st.dataframe(df_view.drop(columns=["Photo"]).sort_values(by="Timestamp", ascending=False))
