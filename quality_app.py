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

# --- 3. SESSION STATE FOR DYNAMIC UPDATES ---
df = load_data()
if 'jobs' not in st.session_state:
    st.session_state.jobs = get_production_jobs()
if 'inspectors' not in st.session_state:
    st.session_state.inspectors = sorted(df["Inspector"].dropna().unique().tolist()) if not df.empty else ["Subodth", "Prasanth", "RamaSai", "Naresh"]
if 'stages' not in st.session_state:
    st.session_state.stages = sorted(df["Stage"].dropna().unique().tolist()) if not df.empty else ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

# --- 4. THE "ADD NEW" SECTION (With Buttons) ---
st.title("🛡️ B&G Quality Master")

with st.expander("➕ ADD NEW OPTIONS TO LISTS"):
    c1, c2, c3 = st.columns(3)
    
    # ADD NEW JOB
    nj = c1.text_input("New Job Code")
    if c1.button("Add Job"):
        if nj and nj not in st.session_state.jobs:
            st.session_state.jobs.append(nj.upper())
            st.session_state.jobs.sort()
            st.success(f"Added {nj}")
    
    # ADD NEW INSPECTOR
    ni = c2.text_input("New Inspector")
    if c2.button("Add Inspector"):
        if ni and ni not in st.session_state.inspectors:
            st.session_state.inspectors.append(ni)
            st.session_state.inspectors.sort()
            st.success(f"Added {ni}")
            
    # ADD NEW STAGE
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

# --- 6. HISTORY & PHOTO SELECTION ---
st.divider()
if not df.empty:
    st.subheader("📜 Quality Inspection Ledger")
    
    # Sort data: Newest first for the ledger
    display_df = df.sort_values(by="Timestamp", ascending=False).reset_index(drop=True)

    # 1. Professional Grid Table (Desktop & Mobile Swipe)
    table_html = """
    <style>
        .ledger-wrapper { overflow-x: auto; border: 1px solid #000; }
        .ledger-table { width: 100%; border-collapse: collapse; min-width: 800px; font-family: sans-serif; }
        .ledger-table th, .ledger-table td { border: 1px solid #000; padding: 10px; text-align: left; font-size: 14px; }
        .ledger-table th { background-color: #f2f2f2; font-weight: bold; }
    </style>
    <div class="ledger-wrapper">
        <table class="ledger-table">
            <tr>
                <th>Time (IST)</th>
                <th>Inspector</th>
                <th>Job Code</th>
                <th>Stage</th>
                <th>Status</th>
                <th>Evidence</th>
            </tr>
    """
    for i, row in display_df.iterrows():
        # Check if photo exists in the hidden data column
        has_photo = "✅ Photo" if (isinstance(row["Photo"], str) and len(row["Photo"]) > 50) else "❌ None"
        table_html += f"""
            <tr>
                <td>{row['Timestamp']}</td>
                <td>{row['Inspector']}</td>
                <td><b>{row['Job_Code']}</b></td>
                <td>{row['Stage']}</td>
                <td>{row['Status']}</td>
                <td>{has_photo}</td>
            </tr>
        """
    table_html += "</table></div>"
    
    # Render the table grid
    st.components.v1.html(table_html, height=400, scrolling=True)

    # 2. Interactive Photo Viewer (The separate selection you liked)
    st.write("---")
    st.subheader("🔍 View Inspection Photo")
    
    # Filter only rows that actually contain image data
    photo_only_df = display_df[display_df["Photo"].astype(str).str.len() > 50].copy()
    
    if not photo_only_df.empty:
        # Create a clean dropdown list for the iPhone
        photo_options = {i: f"{r['Timestamp']} | {r['Job_Code']} | {r['Stage']}" for i, r in photo_only_df.iterrows()}
        photo_selection = st.selectbox("Select a record to view its photo:", 
                                         options=photo_options.keys(), 
                                         format_func=lambda x: photo_options[x])
        
        if photo_selection is not None:
            # Decode the base64 string back into a visible image
            st.image(base64.b64decode(photo_only_df.loc[photo_selection, "Photo"]), 
                     caption=f"B&G Evidence: {photo_only_df.loc[photo_selection, 'Job_Code']}", 
                     use_container_width=True)
    else:
        st.info("No inspection photos found in the current logs.")
else:
    st.info("No history records found.")
