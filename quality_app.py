import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from github import Github
from io import BytesIO
from PIL import Image

# --- 1. SETUP & SECRETS ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "quality_logs.csv"
# RAW URL for Production Logs from your monitor repository
RAW_PROD_URL = "https://raw.githubusercontent.com/Bgenggadmin/shopfloor-monitor/main/production_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("❌ Streamlit Secrets (GITHUB_REPO or GITHUB_TOKEN) are missing!")
    st.stop()

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

st.set_page_config(page_title="B&G Quality Master", layout="wide", page_icon="🛡️")
st.title("🛡️ B&G Quality Master")

# --- 2. GITHUB & DATA UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"QC Update {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except Exception as e:
        st.warning(f"⚠️ GitHub Sync Error: {e}")
        return False

# CRITICAL FIX: Ensure 'df' is always defined
def load_data():
    if os.path.exists(DB_FILE):
        try:
            return pd.read_csv(DB_FILE)
        except: pass
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

# FETCH PRODUCTION JOB CODES
def get_production_jobs():
    try:
        prod_df = pd.read_csv(RAW_PROD_URL)
        if "Job_Code" in prod_df.columns:
            jobs = prod_df["Job_Code"].dropna().unique().tolist()
            return sorted([str(j) for j in jobs])
    except:
        return []

# Define 'df' at the start to avoid NameError
df = load_data()
job_list = get_production_jobs()

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
        save_to_github(df)
        st.sidebar.success("Entry Deleted!")
        st.rerun()

# --- 4. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        # SEARCHABLE DROPDOWN
        if job_list:
            selected_job = st.selectbox("Job Code", ["-- Select Job --", "➕ Type New Job Code"] + job_list)
            if selected_job == "➕ Type New Job Code":
                job_code = st.text_input("Enter New Job Code").upper()
            else:
                job_code = selected_job
        else:
            job_code = st.text_input("Job Code (Manual Entry)").upper()
        
        inspector = st.selectbox("Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
        stage = st.selectbox("Inspection Stage", list(STAGE_REFS.keys()))
        
    with col2:
        ref_data = st.text_input(f"Ref: {STAGE_REFS[stage]}")
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
        remarks = st.text_area("Remarks")

    cam_photo = st.camera_input("Capture Evidence")
    
    if st.form_submit_button("🚀 Submit & Sync to GitHub"):
        if job_code in ["-- Select Job --", ""]:
            st.error("❌ Please provide a valid Job Code.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            full_notes = f"{ref_data} | {remarks}"
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Inspector": inspector, "Job_Code": job_code, "Stage": stage,
                "Status": status, "Notes": full_notes, "Photo": img_str
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            if save_to_github(updated_df):
                st.success(f"✅ Secured: {job_code} at {stage}")
                st.rerun()

# --- 5. AUDIT HISTORY & PHOTOS ---
st.divider()
df_view = load_data()
if not df_view.empty:
    tab1, tab2 = st.tabs(["📜 History", "🖼️ Photo Gallery"])
    with tab1:
        desired_cols = ["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]
        available_cols = [c for c in desired_cols if c in df_view.columns]
        st.dataframe(df_view[available_cols].sort_values(by="Timestamp", ascending=False), use_container_width=True)
    
    with tab2:
        unique_q_jobs = [j for j in df_view['Job_Code'].unique() if str(j) != 'nan']
        view_job = st.selectbox("View Photos", ["-- Select --"] + unique_q_jobs)
        if view_job != "-- Select --":
            job_data = df_view[df_view['Job_Code'] == view_job]
            for _, row in job_data.iterrows():
                photo_data = row.get('Photo')
                if isinstance(photo_data, str) and len(photo_data) > 100:
                    st.write(f"**{row['Stage']}** | {row['Status']} | {row['Timestamp']}")
                    st.image(base64.b64decode(photo_data), use_container_width=True)
                    st.divider()
