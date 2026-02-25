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

def get_dynamic_list(df, col, defaults):
    if not df.empty and col in df.columns:
        found = df[col].dropna().unique().tolist()
        return sorted(list(set(defaults + [str(x) for x in found if str(x).strip()])))
    return sorted(defaults)

def get_production_jobs():
    try:
        return sorted(pd.read_csv(RAW_PROD_URL)["Job_Code"].dropna().unique().tolist())
    except: return []

df = load_data()
job_list = get_production_jobs()
inspectors = get_dynamic_list(df, "Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
stages = get_dynamic_list(df, "Stage", ["RM Inspection", "Marking", "Fit-up", "Welding", "Final Inspection"])

# --- 3. INPUT FORM ---
# We use st.container to make sure the "Type" box appears outside the form if needed
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # JOB CODE
        j_sel = st.selectbox("Job Code", ["-- Select --", "➕ Add New"] + job_list)
        # If Add New is selected, this box will be processed below
        j_new = st.text_input("New Job Code (if 'Add New' picked)")
        
        # INSPECTOR
        i_sel = st.selectbox("Inspector", ["-- Select --", "➕ Add New"] + inspectors)
        i_new = st.text_input("New Inspector Name (if 'Add New' picked)")
        
    with col2:
        # STAGE
        s_sel = st.selectbox("Stage", ["-- Select --", "➕ Add New"] + stages)
        s_new = st.text_input("New Stage Name (if 'Add New' picked)")
        
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Evidence Photo")
    
    if st.form_submit_button("🚀 Submit & Sync"):
        # LOGIC: Choose between dropdown and typed entry
        final_job = j_new if j_sel == "➕ Add New" else j_sel
        final_ins = i_new if i_sel == "➕ Add New" else i_sel
        final_stg = s_new if s_sel == "➕ Add New" else s_sel
        
        # CHECK FOR BLANKS
        if any(v in ["-- Select --", "", None] for v in [final_job, final_ins, final_stg]):
            st.error("❌ Fill all fields. If you picked 'Add New', you must type in the text box below the dropdown.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Inspector": final_ins, "Job_Code": final_job, "Stage": final_stg,
                "Status": status, "Notes": remarks, "Photo": img_str
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            if save_to_github(updated_df):
                st.success(f"✅ Success! {final_job} recorded.")
                st.rerun()

# --- 4. HISTORY ---
st.divider()
if not df.empty:
    st.subheader("📜 Audit History")
    st.dataframe(df[["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]].sort_values(by="Timestamp", ascending=False), use_container_width=True)
