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
    st.error("❌ Secrets missing!")
    st.stop()

# --- 2. DATABASE FUNCTIONS ---
def load_quality_data():
    try:
        # 'desc=True' puts the NEWEST entries at the top (ID or Timestamp)
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def get_production_jobs():
    try:
        response = supabase.table("production").select("Job_Code").execute()
        return sorted(list(set([r['Job_Code'] for r in response.data if r['Job_Code']]))) if response.data else []
    except:
        return []

df = load_quality_data()

# --- 3. DYNAMIC DROPDOWNS ---
if not df.empty:
    all_workers = sorted([w for w in df["Worker"].dropna().unique().tolist() if w not in ["N/A", ""]])
    all_inspectors = sorted(list(set(["Subodth", "Prasanth", "RamaSai", "Naresh"] + df["Inspector"].dropna().unique().tolist())))
    all_stages = sorted(list(set(["RM Inspection", "Marking", "Fit-up", "Welding", "Final"] + df["Stage"].dropna().unique().tolist())))
    all_jobs = sorted(list(set(get_production_jobs() + df["Job_Code"].dropna().unique().tolist())))
else:
    all_workers, all_inspectors, all_stages, all_jobs = [], ["Subodth", "Prasanth", "RamaSai", "Naresh"], ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"], get_production_jobs()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Inspection Entry", "Manage Lists", "View Photos", "Migration Tool"])

# --- PAGE 1: ENTRY & LEDGER ---
if menu == "Inspection Entry":
    st.title("📝 New Inspection")
    with st.form("qc_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
        with c2:
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
        
        sts = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
        rem = st.text_area("Notes")
        cam = st.camera_input("Photo")
        
        if st.form_submit_button("Submit"):
            if "-- Select --" in [job, wrk, ins, stg]:
                st.warning("Please select all fields.")
            else:
                # Capture current IST time for new entries
                now_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                img_str = ""
                if cam:
                    img = Image.open(cam).convert('RGB')
                    img.thumbnail((400, 400))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=50)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                payload = {"created_at": now_ist, "Job_Code": job, "Worker": wrk, "Inspector": ins, "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str}
                supabase.table("quality").insert(payload).execute()
                st.success("Saved!")
                st.rerun()

    st.divider()
    st.subheader("📋 Ledger (Newest First)")
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        view_df['Timestamp'] = pd.to_datetime(view_df['created_at']).dt.tz_localize(None).dt.strftime('%d-%m-%Y %H:%M')
        st.dataframe(view_df[['id', 'Timestamp', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', 'Notes']], use_container_width=True)

# --- PAGE 4: MIGRATION (ACTUAL DATE PRESERVATION) ---
elif menu == "Migration Tool":
    st.title("📂 Migration")
    if st.button("🚀 Run Actual Time Migration"):
        if os.path.exists("quality_logs.csv"):
            old_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in old_df.iterrows():
                # Extract actual time from CSV
                raw_ts = str(r.get('Timestamp', ''))
                try:
                    # dayfirst=True ensures 02-03 is March 2nd, not Feb 3rd
                    clean_ts = pd.to_datetime(raw_ts, dayfirst=True).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    clean_ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

                records.append({
                    "created_at": clean_ts, 
                    "Inspector": str(r.get('Inspector', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')),
                    "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')),
                    "Status": str(r.get('Status', 'Passed')),
                    "Notes": str(r.get('Notes', '')),
                    "Photo": str(r.get('Photo', ''))
                })
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.success("Migration Done!")
