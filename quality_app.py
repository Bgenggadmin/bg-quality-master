import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- 1. SETUP ---
IST = pytz.timezone('Asia/Kolkata')
st.set_page_config(page_title="B&G Quality Master", layout="wide", page_icon="🛡️")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception:
    st.error("❌ Secrets missing! Add SUPABASE_URL and SUPABASE_KEY to Secrets.")
    st.stop()

# --- 2. DATABASE FUNCTIONS ---
def load_quality_data():
    try:
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_production_jobs():
    try:
        response = supabase.table("production").select("Job_Code").execute()
        if response.data:
            return sorted(list(set([r['Job_Code'] for r in response.data if r['Job_Code'] and r['Job_Code'] != "N/A"])))
        return []
    except:
        return []

df = load_quality_data()

# --- 3. SIDEBAR NAVIGATION ---
st.sidebar.title("🛡️ Quality Menu")
menu = st.sidebar.radio("Go to:", ["Inspection Entry", "Manage Lists (Add New)", "View Evidence Photos", "Migration Tool"])

# --- 4. DYNAMIC DROPDOWNS ---
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

if not df.empty:
    all_inspectors = sorted(list(set(base_inspectors + df["Inspector"].dropna().unique().tolist())))
    all_workers = sorted(df["Worker"].dropna().unique().tolist()) if "Worker" in df.columns else []
    all_jobs = sorted(list(set(get_production_jobs() + df["Job_Code"].dropna().unique().tolist())))
    all_stages = sorted(list(set(base_stages + df["Stage"].dropna().unique().tolist())))
    
    # Clean lists
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", ""]]
    all_jobs = [j for j in all_jobs if j not in ["N/A", ""]]
    all_workers = [w for w in all_workers if w not in ["N/A", ""]]
else:
    all_inspectors = sorted(base_inspectors)
    all_jobs = get_production_jobs()
    all_workers = []
    all_stages = sorted(base_stages)

# --- PAGE 1: INSPECTION ENTRY ---
if menu == "Inspection Entry":
    st.title("📝 Quality Inspection Entry")
    
    with st.form("qc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
        with col2:
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
            sts = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)

        rem = st.text_area("Observations")
        cam = st.camera_input("Capture Photo")
        
        if st.form_submit_button("🚀 Submit"):
            if "-- Select --" in [job, ins, stg, wrk]:
                st.warning("⚠️ Please fill all required fields (Job, Worker, Inspector, Stage).")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam)
                    img.thumbnail((400, 400))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=40)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                payload = {
                    "Inspector": ins, "Worker": wrk, "Job_Code": job, 
                    "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Saved!")
                st.rerun()

# --- PAGE 2: MANAGE LISTS (DYNAMIC ADD) ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Manage Lists")
    c1, c2 = st.columns(2)
    with c1:
        new_j = st.text_input("Add New Job Code")
        if st.button("Save Job"):
            supabase.table("quality").insert({"Job_Code": new_j, "Notes": "SYS", "Inspector": "N/A", "Worker": "N/A"}).execute()
            st.rerun()
            
        new_w = st.text_input("Add New Worker")
        if st.button("Save Worker"):
            supabase.table("quality").insert({"Worker": new_w, "Notes": "SYS", "Job_Code": "N/A", "Inspector": "N/A"}).execute()
            st.rerun()
    with c2:
        new_i = st.text_input("Add New Inspector")
        if st.button("Save Inspector"):
            supabase.table("quality").insert({"Inspector": new_i, "Notes": "SYS", "Job_Code": "N/A", "Worker": "N/A"}).execute()
            st.rerun()

# --- PAGE 4: MIGRATION (STRICT COLUMN MAPPING) ---
elif menu == "Migration Tool":
    st.title("📂 Migration")
    if st.button("🚀 Start Migration"):
        if os.path.exists("quality_logs.csv"):
            try:
                old_df = pd.read_csv("quality_logs.csv").fillna("")
                
                # Manual Mapping to prevent Schema Cache Errors
                records = []
                for _, row in old_df.iterrows():
                    records.append({
                        "Inspector": str(row.get('Inspector', 'N/A')),
                        "Worker": str(row.get('Worker', 'N/A')),
                        "Job_Code": str(row.get('Job_Code', 'N/A')),
                        "Stage": str(row.get('Stage', 'N/A')),
                        "Status": str(row.get('Status', 'N/A')),
                        "Notes": str(row.get('Notes', '')),
                        "Photo": str(row.get('Photo', ''))
                    })
                
                # Small batches for photos
                for i in range(0, len(records), 5):
                    supabase.table("quality").insert(records[i:i+5]).execute()
                
                st.success("✅ Done!")
            except Exception as e:
                st.error(f"Error: {e}")
