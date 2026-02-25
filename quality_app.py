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

# Comprehensive engineering stages for B&G
STAGE_REFS = {
    "RM Inspection": "Heat No / Plate No",
    "Marking": "Drawing Rev No",
    "Dimensional Inspection": "Report No / Drawing Ref",
    "Fit-up": "Joint No / Seam No",
    "Welding": "Welder Stamp / ID",
    "Grinding": "Wheel Type used",
    "DP / LPI": "Report No / Batch No",
    "Hydro Test": "Test Pressure (kg/cm2)",
    "Pneumatic Test": "Test Pressure (kg/cm2)",
    "Final Inspection": "QC Release Note No"
}

st.set_page_config(page_title="B&G Quality Master", layout="wide")
st.title("🛡️ B&G Quality Master")

# --- 2. DATA LOAD ---
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    # Uses exact headers from your GitHub CSV: Timestamp, Inspector, Job_Code, Stage, Status, Notes, Photo
    df = pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

# --- 3. ADMIN: DELETE ENTRY ---
st.sidebar.header("⚙️ Admin Controls")
if not df.empty:
    st.sidebar.subheader("🗑️ Delete Entry")
    delete_options = [f"{i}: {df.at[i, 'Job_Code']} - {df.at[i, 'Stage']}" for i in df.index[::-1]]
    target = st.sidebar.selectbox("Select entry to remove", delete_options)
    if st.sidebar.button("Confirm Delete"):
        idx = int(target.split(":")[0])
        df = df.drop(idx)
        df.to_csv(DB_FILE, index=False)
        st.sidebar.success("Entry Deleted!")
        st.rerun()

# --- 4. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        job_code = st.text_input("Job Code").upper()
        inspector = st.selectbox("Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
        stage = st.selectbox("Stage", list(STAGE_REFS.keys()))
    with col2:
        ref_data = st.text_input(f"Reference: {STAGE_REFS[stage]}")
        status = st.radio("Result", ["🟢 Passed", "🟡 Rework", "🔴 Failed"])
        remarks = st.text_area("Remarks")

    cam_photo = st.camera_input("Take Photo")
    
    if st.form_submit_button("Submit Quality Record"):
        img_str = ""
        if cam_photo:
            img = Image.open(cam_photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Combine Reference and Remarks into the 'Notes' column for the CSV
        full_notes = f"{ref_data} | {remarks}"
        
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
            "Inspector": inspector,
            "Job_Code": job_code,
            "Stage": stage,
            "Status": status,
            "Notes": full_notes,
            "Photo": img_str
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success("Record Saved!")
        st.rerun()

# --- 5. CLEAN AUDIT HISTORY & PHOTOS ---
st.divider()
if not df.empty:
    st.subheader("📋 Quality Audit History")
    
    # 1. We force the app to only look at these specific columns
    valid_columns = ["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]
    
    # 2. Filter the dataframe to only include these columns (avoids 'None' columns)
    # We use 'errors="ignore"' just in case one of these is missing in the file
    display_df = df.reindex(columns=valid_columns)
    
    # 3. Show the clean table
    st.dataframe(display_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    
    st.subheader("🖼️ Photo Gallery")
    view_job = st.selectbox("Filter Photos by Job", ["-- Select --"] + list(df['Job_Code'].unique()))
    if view_job != "-- Select --":
        # Filter data for the selected job
        job_data = df[df['Job_Code'] == view_job]
        for _, row in job_data.iterrows():
            # Check if photo exists and is not "No Photo" or empty
            if pd.notnull(row.get('Photo')) and len(str(row['Photo'])) > 100:
                st.write(f"**Stage:** {row['Stage']} | **Status:** {row['Status']}")
                try:
                    st.image(base64.b64decode(row['Photo']), width=450)
                except:
                    st.warning("Could not display this image.")
                st.divider()
