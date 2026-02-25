import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from github import Github
from io import BytesIO
from PIL import Image

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "quality_logs.csv"
RAW_PROD_URL = "https://raw.githubusercontent.com/Bgenggadmin/shopfloor-monitor/main/production_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("❌ Secrets missing!")
    st.stop()

st.set_page_config(page_title="B&G Quality Master", layout="wide")
st.title("🛡️ B&G Quality Master")

# --- 2. DATA UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"QC Sync {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except: return False

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

def get_production_jobs():
    try:
        return sorted(pd.read_csv(RAW_PROD_URL)["Job_Code"].dropna().unique().tolist())
    except: return []

df = load_data()
job_list = get_production_jobs()
existing_inspectors = sorted(df["Inspector"].dropna().unique().tolist()) if not df.empty else ["Subodth", "Prasanth", "RamaSai", "Naresh"]
existing_stages = sorted(df["Stage"].dropna().unique().tolist()) if not df.empty else ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

# --- 3. INPUT FORM ---
# Toggle for "New Entry Mode" to keep the UI clean
new_mode = st.toggle("✨ Add New Inspector/Stage/Job (Manual Typing Mode)")

with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        if new_mode:
            job_code = st.text_input("Type New Job Code").upper()
            inspector = st.text_input("Type New Inspector Name")
        else:
            job_code = st.selectbox("Select Job Code", ["-- Select --"] + job_list)
            inspector = st.selectbox("Select Inspector", ["-- Select --"] + existing_inspectors)
        
    with col2:
        if new_mode:
            stage = st.text_input("Type New Inspection Stage")
        else:
            stage = st.selectbox("Select Stage", ["-- Select --"] + existing_stages)
            
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Evidence Photo")
    
    if st.form_submit_button("🚀 Submit & Sync"):
        if any(v in ["-- Select --", "", None] for v in [job_code, inspector, stage]):
            st.error("❌ Please fill all fields before submitting.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d
