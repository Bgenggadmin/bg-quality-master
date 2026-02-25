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
    st.error("❌ Streamlit Secrets (GITHUB_REPO or GITHUB_TOKEN) are missing!")
    st.stop()

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

def load_data():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE)
        except: pass
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

# --- 3. DYNAMIC LIST LOGIC ---
def get_dynamic_list(df, column_name, default_list):
    if not df.empty and column_name in df.columns:
        found_items = df[column_name].dropna().unique().tolist()
        return sorted(list(set(default_list + [str(x) for x in found_items if str(x).strip() != ""])))
    return sorted(default_list)

def get_production_jobs():
    try:
        prod_df = pd.read_csv(RAW_PROD_URL)
        if "Job_Code" in prod_df.columns:
            jobs = prod_df["Job_Code"].dropna().unique().tolist()
            return sorted([str(j) for j in jobs])
    except: return []

df = load_data()
job_list = get_production_jobs()

# Load current lists for Inspector and Stage
inspectors = get_dynamic_list(df, "Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
stages = get_dynamic_list(df, "Stage", ["RM Inspection", "Marking", "Dimensional Inspection", "Fit-up", "Welding", "Final Inspection"])

# --- 4. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        # JOB CODE (from Production)
        if job_list:
            j_sel = st.selectbox("Job Code", ["-- Select Job --", "➕ Add New"] + job_list)
            job_code = st.text_input("New Job Code").upper() if j_sel == "➕ Add New" else j_sel
        else:
            job_code = st.text_input("Job Code (Manual Entry)").upper()
        
        # INSPECTOR (Dynamic)
        i_sel = st.selectbox("Inspector", ["-- Select Inspector --", "➕ Add New Inspector"] + inspectors)
        inspector = st.text_input("New Inspector Name") if i_sel == "➕ Add New Inspector" else i_sel
        
        # STAGE (Dynamic)
        s_sel = st.selectbox("Stage", ["-- Select Stage --", "➕ Add New Stage"] + stages)
        stage = st.text_input("New Stage Name") if s_sel == "➕ Add New Stage" else s_sel
        
    with col2:
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
        remarks = st.text_area("Observations / Remarks")
        cam_photo = st.camera_input("Capture Evidence")
    
    if st.form_submit_button("🚀 Submit & Sync to GitHub"):
        invalid = ["-- Select Job --", "-- Select Inspector --", "-- Select Stage --", "", None]
        if any(v in invalid for v in [job_code, inspector, stage]):
            st.error("❌ Please fill in Job Code, Inspector, and Stage.")
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
                st.success(f"✅ Record for {job_code} Secured!")
                st.rerun()

# --- 5. HISTORY & PHOTOS ---
st.divider()
df_view = load_data()
if not df_view.empty:
    tab1, tab2 = st.tabs(["📜 Audit History", "🖼️ Photo Gallery"])
    with tab1:
        desired_cols = ["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]
        st.dataframe(df_view[desired_cols].sort_values(by="Timestamp", ascending=False), use_container_width=True)
    
    with tab2:
        unique_q_jobs = [j for j in df_view['Job_Code'].unique() if str(j) != 'nan']
        view_job = st.selectbox("Filter Photos", ["-- Select --"] + unique_q_jobs)
        if view_job != "-- Select --":
            job_data = df_view[df_view['Job_Code'] == view_job]
            for _, row in job_data.iterrows():
                photo_data = row.get('Photo')
                if isinstance(photo_data, str) and len(photo_data) > 100:
                    st.write(f"**{row['Stage']}** | {row['Status']} | {row['Timestamp']}")
                    st.image(base64.b64decode(photo_data), width=500)
                    st.divider()
