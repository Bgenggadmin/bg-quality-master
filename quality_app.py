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

# CRITICAL FIX: Always load the freshest data from GitHub for the dropdowns
@st.cache_data(ttl=10) # Refreshes every 10 seconds
def load_data_fresh():
    RAW_QC_URL = f"https://raw.githubusercontent.com/{REPO_NAME}/main/{DB_FILE}"
    try:
        return pd.read_csv(RAW_QC_URL)
    except:
        if os.path.exists(DB_FILE):
            return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

def get_dynamic_list(df, col, defaults):
    if not df.empty and col in df.columns:
        # Get all unique values, clean them, and merge with defaults
        found = [str(x).strip() for x in df[col].dropna().unique() if str(x).strip() != ""]
        return sorted(list(set(defaults + found)))
    return sorted(defaults)

def get_production_jobs():
    try:
        return sorted(pd.read_csv(RAW_PROD_URL)["Job_Code"].dropna().unique().tolist())
    except: return []

# --- 3. REFRESH LISTS ---
df_main = load_data_fresh()
job_list = get_production_jobs()
inspectors = get_dynamic_list(df_main, "Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
stages = get_dynamic_list(df_main, "Stage", ["RM Inspection", "Marking", "Fit-up", "Welding", "Final Inspection"])

# --- 4. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        j_sel = st.selectbox("Job Code", ["-- Select --", "➕ Add New"] + job_list)
        j_new = st.text_input("Type New Job Code (if 'Add New' picked)")
        
        i_sel = st.selectbox("Inspector", ["-- Select --", "➕ Add New"] + inspectors)
        i_new = st.text_input("Type New Inspector Name (if 'Add New' picked)")
        
    with col2:
        s_sel = st.selectbox("Stage", ["-- Select --", "➕ Add New"] + stages)
        s_new = st.text_input("Type New Stage Name (if 'Add New' picked)")
        
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Evidence Photo")
    
    if st.form_submit_button("🚀 Submit & Sync"):
        final_job = j_new if j_sel == "➕ Add New" else j_sel
        final_ins = i_new if i_sel == "➕ Add New" else i_sel
        final_stg = s_new if s_sel == "➕ Add New" else s_sel
        
        if any(v in ["-- Select --", "", None] for v in [final_job, final_ins, final_stg]):
            st.error("❌ Fill all fields. If you picked 'Add New', you MUST type in the text box.")
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
            
            # Combine current GitHub data with the new entry
            updated_df = pd.concat([df_main, new_row], ignore_index=True)
            updated_df.to_csv(DB_FILE, index=False)
            if save_to_github(updated_df):
                st.success(f"✅ Saved {final_ins} for {final_job}!")
                st.cache_data.clear() # Force app to see new data immediately
                st.rerun()

# --- 5. HISTORY ---
st.divider()
if not df_main.empty:
    st.subheader("📜 Recent History")
    st.dataframe(df_main[["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]].sort_values(by="Timestamp", ascending=False), use_container_width=True)
