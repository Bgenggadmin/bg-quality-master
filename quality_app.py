import streamlit as st
import pandas as pd
from github import Github
import os
from datetime import datetime
import pytz

# --- 1. CONFIGURATION ---
IST = pytz.timezone('Asia/Kolkata')
LOGS_FILE = "quality_logs.csv"
PHOTO_FOLDER = "quality_photos"
# Added Activity and Notes to Headers
HEADERS = ["Timestamp", "Job_Code", "Activity", "Heat_Number", "Inspection_Result", "Supervisor", "Notes", "Photo_URL"]

# GitHub Setup
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    GITHUB_REPO = st.secrets["GITHUB_REPO"]
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
except Exception as e:
    st.error("Missing GitHub Secrets! Please add them in Streamlit Settings.")
    st.stop()

# --- 2. FUNCTIONS ---
def sync_to_github(file_path, commit_message):
    with open(file_path, "rb") as f:
        content = f.read()
    try:
        contents = repo.get_contents(file_path)
        repo.update_file(contents.path, commit_message, content, contents.sha)
    except:
        repo.create_file(file_path, commit_message, content)

def save_photo_to_github(uploaded_file, job_code):
    timestamp = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    folder = PHOTO_FOLDER.strip("/")
    file_name = f"{folder}/{job_code}_{timestamp}.jpg"
    repo.create_file(file_name, f"QC Photo: {job_code}", uploaded_file.getvalue())
    return f"https://github.com/{GITHUB_REPO}/blob/main/{file_name}"

# --- 3. UI & FORM ---
st.title("🛡️ B&G Quality Control")

with st.form("qc_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        job_code = st.text_input("Job Code (e.g. 2KL ANFD_1361)")
        # NEW FIELD: Activity
        activity = st.selectbox("Inspection Activity", ["Material Inward", "Marking", "Cutting", "Fit-up", "Welding", "DP Test", "Hydro Test", "Final Painting"])
        heat_no = st.text_input("Heat Number / Batch No")
    with col2:
        supervisor = st.selectbox("QC Inspector", ["Prasanth", "Sunil", "Ravindra", "Naresh", "RamaSai", "Subodth"])
        result = st.radio("Result", ["✅ Pass", "❌ Fail", "⚠️ Rework"], horizontal=True)
        # NEW FIELD: Notes
        notes = st.text_area("Inspection Notes", placeholder="Mention any defects or observations here...")
    
    st.write("📸 **Inspection Proof**")
    use_camera = st.checkbox("Turn on Camera")
    if use_camera:
        uploaded_file = st.camera_input("Snap a photo")
    else:
        uploaded_file = st.file_uploader("Upload from Gallery", type=['jpg', 'jpeg', 'png'])
    
    if st.form_submit_button("Submit Inspection"):
        photo_url = "No Photo"
        if uploaded_file:
            photo_url = save_photo_to_github(uploaded_file, job_code)
        
        new_row = {
            "Timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "Job_Code": job_code,
            "Activity": activity,
            "Heat_Number": heat_no,
            "Inspection_Result": result,
            "Supervisor": supervisor,
            "Notes": notes,
            "Photo_URL": photo_url
        }
        
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
        else:
            df = pd.DataFrame(columns=HEADERS)
            
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(LOGS_FILE, index=False)
        sync_to_github(LOGS_FILE, f"QC Entry: {job_code} - {activity}")
        st.success(f"✅ {activity} for {job_code} Recorded!")

# --- 4. TODAY'S SUMMARY VIEW (FIXED) ---
st.divider()
st.subheader("📊 Today's Quality Checks")
if os.path.exists(LOGS_FILE):
    df_view = pd.read_csv(LOGS_FILE)
    df_view['Timestamp'] = pd.to_datetime(df_view['Timestamp'], errors='coerce')
    df_view['Date'] = df_view['Timestamp'].dt.date
    today_ist = datetime.now(IST).date()
    
    df_today = df_view[df_view['Date'] == today_ist].drop(columns=['Date'])
    
    if not df_today.empty:
        st.dataframe(df_today.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    else:
        st.info(f"No inspections recorded today.")
