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
    st.error("❌ Secrets missing! Please check Streamlit Cloud Secrets.")
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
    except: 
        return False

def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

def get_production_jobs():
    try:
        return sorted(pd.read_csv(RAW_PROD_URL)["Job_Code"].dropna().unique().tolist())
    except: 
        return []

# --- 3. SESSION STATE ---
df = load_data()
if 'jobs' not in st.session_state:
    st.session_state.jobs = get_production_jobs()
if 'inspectors' not in st.session_state:
    st.session_state.inspectors = sorted(df["Inspector"].dropna().unique().tolist()) if not df.empty else ["Subodth", "Prasanth", "RamaSai", "Naresh"]
if 'stages' not in st.session_state:
    st.session_state.stages = sorted(df["Stage"].dropna().unique().tolist()) if not df.empty else ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

st.title("🛡️ B&G Quality Master")

# --- 4. THE "ADD NEW" SECTION ---
with st.expander("➕ ADD NEW OPTIONS TO LISTS"):
    c1, c2, c3 = st.columns(3)
    nj = c1.text_input("New Job Code")
    if c1.button("Add Job"):
        if nj and nj not in st.session_state.jobs:
            st.session_state.jobs.append(nj.upper())
            st.session_state.jobs.sort()
            st.success(f"Added {nj}")
    
    ni = c2.text_input("New Inspector")
    if c2.button("Add Inspector"):
        if ni and ni not in st.session_state.inspectors:
            st.session_state.inspectors.append(ni)
            st.session_state.inspectors.sort()
            st.success(f"Added {ni}")
            
    ns = c3.text_input("New Stage")
    if c3.button("Add Stage"):
        if ns and ns not in st.session_state.stages:
            st.session_state.stages.append(ns)
            st.session_state.stages.sort()
            st.success(f"Added {ns}")

st.divider()

# --- 5. MAIN LOGGING FORM ---
with st.form("main_form", clear_on_submit=True):
    st.subheader("📝 Log Inspection")
    col1, col2 = st.columns(2)
    with col1:
        job_code = st.selectbox("Select Job Code", ["-- Select --"] + st.session_state.jobs)
        inspector = st.selectbox("Select Inspector", ["-- Select --"] + st.session_state.inspectors)
    with col2:
        stage = st.selectbox("Select Stage", ["-- Select --"] + st.session_state.stages)
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Capture Photo")
    
    if st.form_submit_button("🚀 SUBMIT RECORD"):
        if any(v == "-- Select --" for v in [job_code, inspector, stage]):
            st.error("❌ Please select valid options from the dropdowns.")
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
                st.success("✅ Log Saved!")
                st.rerun()

# --- 6. HISTORY & PHOTO VIEW (Perfect Aligned Grid) ---
st.divider()
if not df.empty:
    st.subheader("📜 Quality Inspection Ledger")
    
    # 1. CSS for Grid Lines and Table Styling
    st.markdown("""
        <style>
            .grid-container {
                display: grid;
                grid-template-columns: 1.5fr 2fr 1.5fr 3fr 1fr;
                border: 1px solid #ddd;
                background-color: #fff;
            }
            .grid-header {
                background-color: #f2f2f2;
                font-weight: bold;
                border-bottom: 2px solid #ccc;
            }
            .grid-cell {
                padding: 10px;
                border-right: 1px solid #ddd;
                border-bottom: 1px solid #ddd;
                font-size: 14px;
                overflow: hidden;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. Sort Data (Newest First)
    display_df = df.sort_values(by="Timestamp", ascending=False).reset_index(drop=True)

    # 3. Headers
    h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.5, 2, 1.5, 3, 1])
    h_col1.markdown("**Time (IST)**")
    h_col2.markdown("**Job Code**")
    h_col3.markdown("**Stage**")
    h_col4.markdown("**Observations**")
    h_col5.markdown("**Photo**")
    st.markdown("<hr style='margin:2px; border:1px solid #000'>", unsafe_allow_html=True)

    # 4. Data Rows with Grid Logic
    for i, row in display_df.iterrows():
        r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([1.5, 2, 1.5, 3, 1])
        
        r_col1.write(row["Timestamp"])
        r_col2.write(f"**{row['Job_Code']}**")
        r_col3.write(row["Stage"])
        r_col4.write(row["Notes"] if pd.notna(row["Notes"]) else "-")
        
        # Action Button for Photo
        if isinstance(row["Photo"], str) and row["Photo"] != "":
            if r_col5.button("👁️ View", key=f"grid_btn_{i}"):
                st.image(base64.b64decode(row["Photo"]), 
                         caption=f"B&G Evidence: {row['Job_Code']}", 
                         use_container_width=True)
        else:
            r_col5.write("None")
            
        # This creates the "Grid Line" between rows
        st.markdown("<hr style='margin:2px; border:0.5px solid #eee'>", unsafe_allow_html=True)

else:
    st.info("No records found in the database.")
