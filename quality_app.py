import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- 1. CORE SETUP & TIMEZONE ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Quality Master", layout="wide", page_icon="🛡️")

# Database Connection
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Database Secrets missing! Please check Streamlit Cloud Settings.")
    st.stop()

# --- 2. DATA UTILITY FUNCTIONS ---

def load_all_data():
    """Fetches all records, newest first."""
    try:
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def save_list_item(column_name, value):
    """Helper to add new Workers/Stages/Inspectors to the database safely."""
    payload = {
        "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
        "Job_Code": "N/A", "Worker": "N/A", "Inspector": "N/A", 
        "Stage": "N/A", "Status": "N/A", "Notes": "SYS", "Photo": ""
    }
    payload[column_name] = value  # Update specific column with new name
    try:
        supabase.table("quality").insert(payload).execute()
        st.success(f"✅ Added '{value}' successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Error saving: {e}")

# Load data at the start
df = load_all_data()

# --- 3. DYNAMIC LIST LOGIC (For Dropdowns) ---

# Default lists
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

if not df.empty:
    # Extract unique values from DB and merge with defaults
    all_workers = sorted([w for w in df["Worker"].unique() if w not in ["N/A", "", "None"]])
    all_inspectors = sorted(list(set(base_inspectors + [i for i in df["Inspector"].unique() if i not in ["N/A", ""]])))
    all_stages = sorted(list(set(base_stages + [s for s in df["Stage"].unique() if s not in ["N/A", ""]])))
    all_jobs = sorted([j for j in df["Job_Code"].unique() if j not in ["N/A", ""]])
else:
    all_workers, all_inspectors, all_stages, all_jobs = [], base_inspectors, base_stages, []

# --- 4. NAVIGATION SIDEBAR ---
st.sidebar.title("🛡️ B&G Quality Control")
menu = st.sidebar.radio("Navigate to:", ["📝 Inspection Entry", "🗂️ Manage Lists", "📂 Migration Tool"])

# --- PAGE 1: INSPECTION ENTRY & LEDGER ---
if menu == "📝 Inspection Entry":
    st.title("Quality Inspection Entry")
    
    # A. ENTRY FORM
    with st.form("main_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
        with col2:
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
            sts = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
            rem = st.text_area("Notes/Observations")
        
        cam = st.camera_input("📸 Capture Evidence")
        
        if st.form_submit_button("🚀 Submit Inspection"):
            if "-- Select --" in [job, wrk, ins, stg]:
                st.warning("⚠️ Please select all fields before submitting.")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam).convert('RGB')
                    img.thumbnail((500, 500))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=50)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                payload = {
                    "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                    "Job_Code": job, "Worker": wrk, "Inspector": ins,
                    "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("Inspection saved to cloud!")
                st.rerun()

    st.divider()

    # B. SUMMARY LEDGER
    st.subheader("📋 Inspection History (Newest First)")
    if not df.empty:
        # Hide system entries used for names
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            # Format Date/Time columns for readability
            view_df['Date'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y')
            view_df['Time'] = pd.to_datetime(view_df['created_at']).dt.strftime('%H:%M')
            view_df['📸 Photo'] = view_df['Photo'].apply(lambda x: "✅" if len(str(x)) > 100 else "❌")
            
            cols = ['id', 'Date', 'Time', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo', 'Notes']
            st.dataframe(view_df[cols], use_container_width=True)

            # C. PHOTO PREVIEW AT THE BOTTOM
            st.divider()
            st.subheader("🔍 Selected Photo Preview")
            photo_only = view_df[view_df['Photo'].astype(str).str.len() > 100].copy()
            if not photo_only.empty:
                pick = st.selectbox("Select ID from table to see photo:", ["-- Select ID --"] + photo_only['id'].astype(str).tolist())
                if pick != "-- Select ID --":
                    row = photo_only[photo_only['id'].astype(int) == int(pick)].iloc[0]
                    img_data = str(row['Photo'])
                    if "," in img_data: img_data = img_data.split(",")[1]
                    st.image(base64.b64decode(img_data), width=600, caption=f"Evidence for ID: {pick}")
            else:
                st.info("No photos available in the current records.")

# --- PAGE 2: MANAGE LISTS ---
elif menu == "🗂️ Manage Lists":
    st.title("Manage Dropdown Lists")
    st.info("Add new names or stages here. They will immediately appear in the entry form.")
    
    colA, colB = st.columns(2)
    with colA:
        st.subheader("Workers & Jobs")
        new_worker = st.text_input("New Worker Name")
        if st.button("Add Worker") and new_worker:
            save_list_item("Worker", new_worker)
            
        new_job = st.text_input("New Job Code")
        if st.button("Add Job Code") and new_job:
            save_list_item("Job_Code", new_job)
            
    with colB:
        st.subheader("Inspectors & Stages")
        new_ins = st.text_input("New Inspector")
        if st.button("Add Inspector") and new_ins:
            save_list_item("Inspector", new_ins)
            
        new_stg = st.text_input("New Stage")
        if st.button("Add Stage") and new_stg:
            save_list_item("Stage", new_stg)

# --- PAGE 3: MIGRATION ---
elif menu == "📂 Migration Tool":
    st.title("Data Migration")
    st.warning("Ensure 'quality_logs.csv' is in your GitHub folder.")
    
    if st.button("🗑️ Clear Cloud Database"):
        supabase.table("quality").delete().neq("id", 0).execute()
        st.success("Database wiped clean.")
        st.rerun()

    if st.button("🚀 Run CSV Migration"):
        if os.path.exists("quality_logs.csv"):
            csv_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in csv_df.iterrows():
                # Force DD-MM format for Indian records
                try:
                    ts = pd.to_datetime(r.get('Timestamp', ''), dayfirst=True).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                
                records.append({
                    "created_at": ts, "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')), "Inspector": str(r.get('Inspector', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')), "Status": str(r.get('Status', 'N/A')),
                    "Notes": str(r.get('Notes', '')), "Photo": str(r.get('Photo', ''))
                })
            # Batch upload
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.success(f"Migrated {len(records)} records!")
            st.rerun()
