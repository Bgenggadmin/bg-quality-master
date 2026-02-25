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
RAW_PROD_URL = "https://raw.githubusercontent.com/Bgenggadmin/shopfloor-monitor/main/production_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except Exception:
    st.error("❌ Secrets missing in Streamlit Cloud!")
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
    except:
        return False

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

def get_production_jobs():
    try:
        prod_df = pd.read_csv(RAW_PROD_URL)
        return sorted(prod_df["Job_Code"].dropna().unique().tolist())
    except:
        return []

# Prepare data for dropdowns
df = load_data()
job_list = get_production_jobs()
inspectors = sorted(df["Inspector"].dropna().unique().tolist()) if not df.empty else ["Subodth", "Prasanth", "RamaSai", "Naresh"]
stages = sorted(df["Stage"].dropna().unique().tolist()) if not df.empty else ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

# --- 3. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # JOB CODE SELECTION
        j_sel = st.selectbox("Job Code", ["-- Select --", "➕ Add New"] + job_list)
        # Only shows row to enter if 'Add New' is picked
        j_new = st.text_input("New Job Code Name") if j_sel == "➕ Add New" else ""
        
        # INSPECTOR SELECTION
        i_sel = st.selectbox("Inspector", ["-- Select --", "➕ Add New"] + inspectors)
        # Only shows row to enter if 'Add New' is picked
        i_new = st.text_input("New Inspector Name") if i_sel == "➕ Add New" else ""
        
    with col2:
        # STAGE SELECTION
        s_sel = st.selectbox("Stage", ["-- Select --", "➕ Add New"] + stages)
        # Only shows row to enter if 'Add New' is picked
        s_new = st.text_input("New Stage Name") if s_sel == "➕ Add New" else ""
        
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Evidence Photo")
    
    # THE MAIN SUBMIT BUTTON
    submit_btn = st.form_submit_button("🚀 Submit & Sync to GitHub")

    if submit_btn:
        # Determine final values based on Add New logic
        final_job = j_new if j_sel == "➕ Add New" else j_sel
        final_ins = i_new if i_sel == "➕ Add New" else i_sel
        final_stg = s_new if s_sel == "➕ Add New" else s_sel
        
        # Check for empty data
        if any(v in ["-- Select --", "", None] for v in [final_job, final_ins, final_stg]):
            st.error("❌ Please fill all fields. If you picked 'Add New', type the name in the box.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Inspector": final_ins,
                "Job_Code": final_job,
                "Stage": final_stg,
                "Status": status,
                "Notes": remarks,
                "Photo": img_str
            }])
            
            updated_df = pd.concat([df, new_row], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            if save_to_github(updated_df):
                st.success("✅ Record Successfully Saved!")
                st.rerun()

# --- 4. HISTORY ---
st.divider()
if not df.empty:
    st.subheader("📜 Recent Records")
    st.dataframe(df[["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]].sort_values(by="Timestamp", ascending=False), use_container_width=True)
