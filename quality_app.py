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

# --- 6. HISTORY & PHOTO VIEW (Mobile-Locked Grid) ---
st.divider()
if not df.empty:
    st.subheader("📜 Quality Inspection Ledger")
    
    # Sort data
    display_df = df.sort_values(by="Timestamp", ascending=False).reset_index(drop=True)

    # 1. Custom CSS for Horizontal Scrolling & Grid Lines
    st.markdown("""
        <style>
            .scroll-container {
                width: 100%;
                overflow-x: auto;
                white-space: nowrap;
                border: 1px solid #ddd;
            }
            .ledger-table {
                width: 100%;
                border-collapse: collapse;
                min-width: 800px; /* Forces the grid to stay wide */
            }
            .ledger-table th, .ledger-table td {
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
                font-size: 14px;
            }
            .ledger-table th {
                background-color: #f8f9fa;
                position: sticky;
                top: 0;
            }
            .ledger-table tr:nth-child(even) { background-color: #fdfdfd; }
        </style>
    """, unsafe_allow_html=True)

    # 2. Build the HTML Table
    table_html = '<div class="scroll-container"><table class="ledger-table"><tr>'
    table_html += '<th>Time (IST)</th><th>Job Code</th><th>Stage</th><th>Observations</th><th>Action</th></tr>'

    for i, row in display_df.iterrows():
        notes = row["Notes"] if pd.notna(row["Notes"]) else "-"
        action_text = "📸 Photo Logged" if (isinstance(row["Photo"], str) and row["Photo"] != "") else "No Photo"
        
        table_html += f"""
        <tr>
            <td>{row['Timestamp']}</td>
            <td><b>{row['Job_Code']}</b></td>
            <td>{row['Stage']}</td>
            <td>{notes}</td>
            <td>{action_text}</td>
        </tr>
        """
    table_html += "</table></div>"
    
    # Render the Table
    st.markdown(table_html, unsafe_allow_html=True)

    # 3. Interactive Photo Viewer (Outside the scroll for better view)
    st.write("---")
    st.write("### 🔍 Select Job to View Photo")
    photo_select = st.selectbox("Pick a record to see evidence:", 
                                 [f"{r['Timestamp']} | {r['Job_Code']}" for _, r in display_df.iterrows() if isinstance(r["Photo"], str) and r["Photo"] != ""])
    
    if photo_select:
        # Extract timestamp to find the right row
        selected_ts = photo_select.split(" | ")[0]
        selected_row = display_df[display_df["Timestamp"] == selected_ts].iloc[0]
        st.image(base64.b64decode(selected_row["Photo"]), 
                 caption=f"Evidence: {selected_row['Job_Code']} - {selected_row['Stage']}", 
                 use_container_width=True)

else:
    st.info("No records found in the database.")

