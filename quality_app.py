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
    st.error("❌ Secrets missing in Streamlit Cloud!")
    st.stop()

st.set_page_config(page_title="B&G Quality Master", layout="wide")

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
        pdf = pd.read_csv(RAW_PROD_URL)
        return sorted(pdf["Job_Code"].dropna().unique().tolist())
    except: return []

df = load_data()
job_list = get_production_jobs()
inspectors = sorted(df["Inspector"].dropna().unique().tolist()) if not df.empty else ["Subodth", "Prasanth", "RamaSai", "Naresh"]
stages = sorted(df["Stage"].dropna().unique().tolist()) if not df.empty else ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

# --- 3. UI LAYOUT ---
st.title("🛡️ B&G Quality Master")

# SEPARATE SECTION FOR ADDING NEW DATA
with st.expander("➕ ADD NEW (Inspector / Stage / Job)"):
    new_col1, new_col2, new_col3 = st.columns(3)
    new_job = new_col1.text_input("New Job Code")
    new_ins = new_col2.text_input("New Inspector")
    new_stg = new_col3.text_input("New Stage")
    st.info("Once you submit a log below using these typed names, they will appear in the dropdowns permanently.")

st.divider()

# MAIN ENTRY FORM (Dropdowns are now CLEAN)
with st.form("main_form", clear_on_submit=True):
    st.subheader("📝 Log Inspection")
    c1, c2 = st.columns(2)
    
    with c1:
        # If user typed in the 'Add New' section, use that. Otherwise, use dropdown.
        job_code = st.selectbox("Select Job", ["-- Select --"] + job_list) if not new_job else new_job
        if new_job: st.caption(f"Using New Job: {new_job}")
            
        inspector = st.selectbox("Select Inspector", ["-- Select --"] + inspectors) if not new_ins else new_ins
        if new_ins: st.caption(f"Using New Inspector: {new_ins}")

    with c2:
        stage = st.selectbox("Select Stage", ["-- Select --"] + stages) if not new_stg else new_stg
        if new_stg: st.caption(f"Using New Stage: {new_stg}")
        
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Photo")
    
    submit = st.form_submit_button("🚀 SUBMIT RECORD")

    if submit:
        if any(v in ["-- Select --", "", None] for v in [job_code, inspector, stage]):
            st.error("❌ Missing Data! Please select from dropdowns or use the 'Add New' section above.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Inspector": inspector, "Job_Code": job_code, "Stage": stage,
                "Status": status, "Notes": remarks, "Photo": img_str
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            if save_to_github(updated_df):
                st.success(f"✅ Saved!")
                st.rerun()

# --- 4. HISTORY ---
st.divider()
if not df.empty:
    st.subheader("📜 Recent Records")
    st.dataframe(df[["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]].sort_values(by="Timestamp", ascending=False), use_container_width=True)
