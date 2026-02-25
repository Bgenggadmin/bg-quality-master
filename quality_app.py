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
    st.error("❌ Streamlit Secrets missing!")
    st.stop()

st.set_page_config(page_title="B&G Quality Master", layout="wide", page_icon="🛡️")
st.title("🛡️ B&G Quality Master")

# --- 2. UTILITIES ---
def save_to_github(dataframe):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = dataframe.to_csv(index=False)
        contents = repo.get_contents(DB_FILE)
        repo.update_file(contents.path, f"QC Sync {datetime.now(IST)}", csv_content, contents.sha)
        return True
    except Exception as e:
        st.error(f"⚠️ Sync Error: {e}")
        return False

def load_data():
    if os.path.exists(DB_FILE):
        try: return pd.read_csv(DB_FILE)
        except: pass
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

def get_dynamic_list(df, column_name, default_list):
    if not df.empty and column_name in df.columns:
        found = df[column_name].dropna().unique().tolist()
        return sorted(list(set(default_list + [str(x) for x in found if str(x).strip() != ""])))
    return sorted(default_list)

def get_production_jobs():
    try:
        prod_df = pd.read_csv(RAW_PROD_URL)
        return sorted(prod_df["Job_Code"].dropna().unique().tolist())
    except: return []

df = load_data()
job_list = get_production_jobs()
inspectors = get_dynamic_list(df, "Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
stages = get_dynamic_list(df, "Stage", ["RM Inspection", "Marking", "Dimensional Inspection", "Fit-up", "Welding", "Final Inspection"])

# --- 3. INPUT FORM ---
with st.form("quality_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        # JOB CODE
        j_sel = st.selectbox("Job Code", ["-- Select Job --", "➕ Add New"] + job_list)
        j_manual = st.text_input("New Job Code (if Add New selected)").upper()
        
        # INSPECTOR
        i_sel = st.selectbox("Inspector", ["-- Select Inspector --", "➕ Add New Inspector"] + inspectors)
        i_manual = st.text_input("New Inspector Name (if Add New selected)")
        
    with col2:
        # STAGE
        s_sel = st.selectbox("Stage", ["-- Select Stage --", "➕ Add New Stage"] + stages)
        s_manual = st.text_input("New Stage Name (if Add New selected)")
        
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Evidence")
    
    if st.form_submit_button("🚀 Submit & Sync to GitHub"):
        # LOGIC TO PICK MANUAL VS DROPDOWN
        final_job = j_manual if j_sel == "➕ Add New" else j_sel
        final_ins = i_manual if i_sel == "➕ Add New Inspector" else i_sel
        final_stg = s_manual if s_sel == "➕ Add New Stage" else s_sel
        
        # VALIDATION
        if any(v in ["-- Select Job --", "-- Select Inspector --", "-- Select Stage --", ""] for v in [final_job, final_ins, final_stg]):
            st.error("❌ Please ensure all fields are filled. If you selected 'Add New', you must type the name in the text box.")
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
                st.success(f"✅ Record for {final_job} Secured!")
                st.rerun()

# --- 4. HISTORY ---
st.divider()
df_view = load_data()
if not df_view.empty:
    tab1, tab2 = st.tabs(["📜 History", "🖼️ Photos"])
    with tab1:
        st.dataframe(df_view[["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes"]].sort_values(by="Timestamp", ascending=False), use_container_width=True)
    with tab2:
        unique_jobs = [j for j in df_view['Job_Code'].unique() if str(j) != 'nan']
        v_job = st.selectbox("Filter Photos", ["-- Select --"] + unique_jobs)
        if v_job != "-- Select --":
            job_data = df_view[df_view['Job_Code'] == v_job]
            for _, row in job_data.iterrows():
                if isinstance(row['Photo'], str) and len(row['Photo']) > 100:
                    st.write(f"**{row['Stage']}** | {row['Status']} | {row['Timestamp']}")
                    st.image(base64.b64decode(row['Photo']), use_container_width=True)
