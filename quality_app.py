import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
from github import Github
from PIL import Image

# --- 1. SETUP & TIMEZONE (IST) ---
IST = pytz.timezone('Asia/Kolkata')
QUALITY_LOG = "quality_records.csv"
PHOTO_DIR = "quality_photos"

# Headers aligned with your shopfloor requirements
HEADERS = ["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo_Path"]

# --- 2. GITHUB SYNC ---
def sync_to_github(file_path, is_image=False):
    try:
        if "GITHUB_TOKEN" in st.secrets:
            g = Github(st.secrets["GITHUB_TOKEN"])
            repo = g.get_repo(st.secrets["GITHUB_REPO"])
            
            if is_image:
                with open(file_path, "rb") as f:
                    content = f.read()
            else:
                with open(file_path, "r") as f:
                    content = f.read()
            
            try:
                contents = repo.get_contents(file_path)
                repo.update_file(contents.path, f"Quality Sync {datetime.now(IST)}", content, contents.sha)
            except:
                repo.create_file(file_path, "Initial Quality Create", content)
    except Exception as e:
        st.error(f"Sync Error: {e}")

st.set_page_config(page_title="B&G Quality Master", layout="wide")
st.title("🛡️ B&G Quality & Traceability")

# --- 3. ENTRY FORM ---
col1, col2 = st.columns(2)
with col1:
    inspector = st.selectbox("Inspector", ["Subodth", "Prasanth", "RamaSai"])
    job_code = st.text_input("Job Code (e.g., SSR501)")
    stage = st.selectbox("Inspection Stage", ["Marking", "Fitup", "Welding", "Hydro-Test", "Final"])
    status = st.radio("Status", ["🟢 Passed", "🔴 Rejected", "🟡 Hold"], horizontal=True)

with col2:
    img_file = st.camera_input("📸 Take Photo of Heat No / Job Progress")
    notes = st.text_area("Quality Notes / Technical Observations")

if st.button("🛡️ Submit Quality Record"):
    if not job_code:
        st.warning("Please enter a Job Code.")
    else:
        ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M')
        photo_path = "None"
        
        if img_file:
            if not os.path.exists(PHOTO_DIR): os.makedirs(PHOTO_DIR)
            photo_path = f"{PHOTO_DIR}/IMG_{datetime.now(IST).strftime('%d%m%Y_%H%M%S')}.png"
            Image.open(img_file).save(photo_path)
            sync_to_github(photo_path, is_image=True)
        
        new_row = [ts, inspector, job_code, stage, status, notes, photo_path]
        
        if os.path.exists(QUALITY_LOG):
            df = pd.read_csv(QUALITY_LOG)
            # Standardize and cleanup columns
            df = df.loc[:, ~df.columns.duplicated()]
            df = pd.concat([df, pd.DataFrame([new_row], columns=HEADERS)], ignore_index=True)
        else:
            df = pd.DataFrame([new_row], columns=HEADERS)
            
        df.to_csv(QUALITY_LOG, index=False)
        sync_to_github(QUALITY_LOG)
        st.success(f"✅ Record & Photo Synced at {ts}")
        st.rerun()

# --- 4. DISPLAY ---
st.divider()
if os.path.exists(QUALITY_LOG):
    df_view = pd.read_csv(QUALITY_LOG).reindex(columns=HEADERS)
    st.subheader("📊 Recent Inspection Records")
    st.dataframe(df_view.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    # --- 5. PHOTO GALLERY ---
st.divider()
if os.path.exists(QUALITY_LOG):
    st.subheader("🖼️ Quality Photo Gallery")
    # Filter only records that actually have a photo path saved
    photo_df = df_view[df_view['Photo_Path'].notna() & (df_view['Photo_Path'] != "None")]
    
    if not photo_df.empty:
        # Create a dropdown to select a specific inspection record
        gallery_list = photo_df['Timestamp'] + " - " + photo_df['Job_Code']
        selected_log = st.selectbox("Select Record to View Photo", gallery_list)
        
        # Extract the correct path for the selected record
        path_to_show = photo_df[photo_df['Timestamp'] + " - " + photo_df['Job_Code'] == selected_log]['Photo_Path'].values[0]
        
        # Verify the file exists on the server before trying to open it
        if isinstance(path_to_show, str) and os.path.exists(path_to_show):
            st.image(path_to_show, caption=f"Inspection Photo for {selected_log}", use_container_width=True)
        else:
            st.info("💡 Photo is saved on GitHub but not yet synced to this local session. You can view it in your 'quality_photos' folder on GitHub.")
    else:
        st.info("No photos captured yet. Use the camera above to add a photo to a record.")
