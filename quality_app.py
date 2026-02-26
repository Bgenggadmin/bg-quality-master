import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from github import Github
from io import BytesIO
from PIL import Image
import streamlit.components.v1 as components

# --- 1. SETUP & AUTHENTICATION ---
IST = pytz.timezone('Asia/Kolkata')
DB_FILE = "quality_logs.csv"

try:
    REPO_NAME = st.secrets["GITHUB_REPO"]
    TOKEN = st.secrets["GITHUB_TOKEN"]
except:
    st.error("❌ Secrets missing in Streamlit Cloud!")
    st.stop()

st.set_page_config(page_title="B&G Quality Master", layout="wide")

# --- 2. CORE FUNCTIONS ---
def load_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Heat_No", "Stage", "Status", "Notes", "Photo"])

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

# --- 3. STATE MANAGEMENT ---
df = load_data()
if 'inspectors' not in st.session_state:
    st.session_state.inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
if 'stages' not in st.session_state:
    st.session_state.stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final", "Hydrotest"]

st.title("🛡️ B&G Quality Master")

# --- 4. INPUT FORM ---
with st.form("main_form", clear_on_submit=True):
    st.subheader("📝 New Inspection Entry")
    c1, c2 = st.columns(2)
    with c1:
        job_code = st.text_input("Job Code (e.g. SSR501)")
        inspector = st.selectbox("Inspector", st.session_state.inspectors)
        heat_no = st.text_input("Heat Number / Batch No")
    with c2:
        stage = st.selectbox("Stage", st.session_state.stages)
        status = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
    
    remarks = st.text_area("Observations / Remarks")
    cam_photo = st.camera_input("Take Inspection Photo")

    if st.form_submit_button("🚀 SUBMIT RECORD"):
        if not job_code or not heat_no:
            st.error("❌ Job Code and Heat Number are mandatory.")
        else:
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG", quality=50) # Compression for speed
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            new_row = pd.DataFrame([{
                "Timestamp": datetime.now(IST).strftime('%Y-%m-%d %H:%M'),
                "Inspector": inspector, "Job_Code": job_code.upper(), 
                "Heat_No": heat_no.upper(), "Stage": stage,
                "Status": status, "Notes": remarks, "Photo": img_str
            }])
            
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(DB_FILE, index=False)
            save_to_github(df)
            st.success("✅ Logged & Synced to GitHub!")
            st.rerun()

# --- 5. THE PERFECT LEDGER GRID ---
st.divider()
if not df.empty:
    st.subheader("📋 Quality Inspection Ledger")
    view_df = df.sort_values(by="Timestamp", ascending=False).head(20)
    
    table_html = """
    <div style="overflow-x: auto; border: 1px solid #000;">
        <table style="width:100%; border-collapse: collapse; font-family: sans-serif; min-width: 850px;">
            <tr style="background-color: #f2f2f2;">
                <th style="border:1px solid #000; padding:8px;">Time (IST)</th>
                <th style="border:1px solid #000; padding:8px;">Job Code</th>
                <th style="border:1px solid #000; padding:8px;">Heat No</th>
                <th style="border:1px solid #000; padding:8px;">Stage</th>
                <th style="border:1px solid #000; padding:8px;">Observations</th>
                <th style="border:1px solid #000; padding:8px;">Photo Status</th>
            </tr>
    """
    for _, r in view_df.iterrows():
        p_stat = "✅ Photo" if len(str(r['Photo'])) > 50 else "❌ None"
        table_html += f"<tr><td style='border:1px solid #000; padding:8px;'>{r['Timestamp']}</td>"
        table_html += f"<td style='border:1px solid #000; padding:8px;'><b>{r['Job_Code']}</b></td>"
        table_html += f"<td style='border:1px solid #000; padding:8px;'>{r['Heat_No']}</td>"
        table_html += f"<td style='border:1px solid #000; padding:8px;'>{r['Stage']}</td>"
        table_html += f"<td style='border:1px solid #000; padding:8px;'>{r['Notes']}</td>"
        table_html += f"<td style='border:1px solid #000; padding:8px;'>{p_stat}</td></tr>"
    table_html += "</table></div>"
    components.html(table_html, height=400, scrolling=True)

    # --- 6. FIXED PHOTO VIEWER ---
    st.write("---")
    st.subheader("🔍 View Inspection Evidence")
    photo_rows = df[df["Photo"].astype(str).str.len() > 50].copy()
    if not photo_rows.empty:
        photo_rows = photo_rows.sort_values(by="Timestamp", ascending=False)
        options = {i: f"{r['Timestamp']} | {r['Job_Code']} | {r['Stage']}" for i, r in photo_rows.iterrows()}
        selection = st.selectbox("Select record to see photo:", options.keys(), format_func=lambda x: options[x])
        if selection is not None:
            st.image(base64.b64decode(photo_rows.loc[selection, "Photo"]), use_container_width=True)
else:
    st.info("No records found.")
