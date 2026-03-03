import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- 1. SETUP & TIMEZONE ---
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
        # Fetching data - sorting by created_at ensures newest logs are on top
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
    # Filter out placeholders for workers
    all_workers = sorted(df["Worker"].dropna().unique().tolist()) if "Worker" in df.columns else []
    all_jobs = sorted(list(set(get_production_jobs() + df["Job_Code"].dropna().unique().tolist())))
    all_stages = sorted(list(set(base_stages + df["Stage"].dropna().unique().tolist())))
    
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", "", "None"]]
    all_jobs = [j for j in all_jobs if j not in ["N/A", "", "None"]]
    all_workers = [w for w in all_workers if w not in ["N/A", "", "None"]]
    all_stages = [s for s in all_stages if s not in ["N/A", "", "None"]]
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
        
        if st.form_submit_button("🚀 Submit Inspection"):
            if "-- Select --" in [job, ins, stg, wrk]:
                st.warning("⚠️ Please fill all required fields.")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam)
                    img.thumbnail((400, 400))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=40)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                # PRECISE IST TIMESTAMP
                current_time_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                
                payload = {
                    "created_at": current_time_ist,
                    "Inspector": ins, "Worker": wrk, "Job_Code": job, 
                    "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success(f"✅ Inspection Saved at {datetime.now(IST).strftime('%H:%M')} IST")
                st.rerun()

    st.divider()
    
    # --- SUMMARY TABLE (LEDGER) ---
    st.subheader("📋 Quality Inspection History")
    if not df.empty:
        # Hide system entries (SYS)
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            view_df = view_df.rename(columns={'id': 'ID', 'created_at': 'Timestamp'})
            
            # Formatting Date for Table View: 03-03-2026 14:30
            view_df['Timestamp'] = pd.to_datetime(view_df['Timestamp']).dt.strftime('%d-%m-%Y %H:%M')
            
            cols = ['ID', 'Timestamp', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', 'Notes']
            st.dataframe(view_df[cols], use_container_width=True)

            # DELETE LOGIC
            st.markdown("### 🗑️ Remove Entry")
            del_id = st.selectbox("Select ID to delete:", ["-- Select --"] + view_df['ID'].tolist())
            if st.button("Permanently Delete"):
                if del_id != "-- Select --":
                    supabase.table("quality").delete().eq("id", del_id).execute()
                    st.success(f"Entry {del_id} removed.")
                    st.rerun()
        else:
            st.info("No inspection records found.")

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Manage App Dropdowns")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Add Worker")
        new_w = st.text_input("New Worker Name")
        if st.button("Save Worker") and new_w:
            supabase.table("quality").insert({"Worker": new_w, "Notes": "SYS", "Job_Code": "N/A", "Inspector": "N/A", "Stage": "N/A"}).execute()
            st.success("Worker added!")
            st.rerun()
            
        st.subheader("Add Job Code")
        new_j = st.text_input("New Job Code")
        if st.button("Save Job") and new_j:
            supabase.table("quality").insert({"Job_Code": new_j, "Notes": "SYS", "Inspector": "N/A", "Worker": "N/A", "Stage": "N/A"}).execute()
            st.success("Job Code added!")
            st.rerun()
    with c2:
        st.subheader("Add Inspector")
        new_i = st.text_input("New Inspector")
        if st.button("Save Inspector") and new_i:
            supabase.table("quality").insert({"Inspector": new_i, "Notes": "SYS", "Job_Code": "N/A", "Worker": "N/A", "Stage": "N/A"}).execute()
            st.success("Inspector added!")
            st.rerun()

        st.subheader("Add Stage")
        new_st = st.text_input("New Inspection Stage")
        if st.button("Save Stage") and new_st:
            supabase.table("quality").insert({"Stage": new_st, "Notes": "SYS", "Job_Code": "N/A", "Worker": "N/A", "Inspector": "N/A"}).execute()
            st.success("Stage added!")
            st.rerun()

# --- PAGE 3: PHOTO VIEWER ---
elif menu == "View Evidence Photos":
    st.title("🔍 Photo Evidence Gallery")
    # Only show records that have actual photo data
    photo_df = df[df['Photo'].str.len() > 100].copy() if not df.empty else pd.DataFrame()
    if not photo_df.empty:
        # Create a display label with formatted date
        photo_df['DisplayDate'] = pd.to_datetime(photo_df['created_at']).dt.strftime('%d-%m %H:%M')
        photo_df['label'] = photo_df['Job_Code'] + " | " + photo_df['Stage'] + " (" + photo_df['DisplayDate'] + ")"
        
        choice = st.selectbox("Select Record:", photo_df['label'].tolist())
        if choice:
            row = photo_df[photo_df['label'] == choice].iloc[0]
            st.image(base64.b64decode(row['Photo']), use_container_width=True, width=600)
            st.write(f"**Inspector:** {row['Inspector']} | **Status:** {row['Status']}")
            st.info(f"**Notes:** {row['Notes']}")
    else:
        st.info("No photos found in the database.")

# --- PAGE 4: MIGRATION ---
# --- PAGE 1: FIXED ENTRY LOGIC ---
if menu == "Inspection Entry":
    # ... (form code) ...
    if st.form_submit_button("🚀 Submit Inspection"):
        # MANUALLY CREATE IST TIMESTAMP STRING
        # This prevents Supabase from using its own UTC clock
        current_time_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
        
        payload = {
            "created_at": current_time_ist, # Manual IST override
            "Inspector": ins, "Worker": wrk, "Job_Code": job, 
            "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
        }
        supabase.table("quality").insert(payload).execute()
        st.success(f"✅ Saved at {current_time_ist}")

# --- PAGE 4: FIXED MIGRATION (TIME OFFSET) ---
elif menu == "Migration Tool":
    st.title("📂 Migration with IST Correction")
    if st.button("🚀 Run Migration"):
        if os.path.exists("quality_logs.csv"):
            old_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            
            for _, r in old_df.iterrows():
                try:
                    # 1. Parse the CSV time
                    raw_ts = r.get('Timestamp', datetime.now(IST))
                    dt_obj = pd.to_datetime(raw_ts, dayfirst=True)
                    
                    # 2. If the time is in UTC, we add 5.5 hours to move it to IST
                    # This fixes the "yesterday showing as today" issue
                    if dt_obj.tzinfo is None or dt_obj.tzinfo == pytz.UTC:
                        dt_obj = dt_obj + pd.Timedelta(hours=5, minutes=30)
                    
                    clean_ts = dt_obj.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    clean_ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

                records.append({
                    "created_at": clean_ts,
                    "Inspector": str(r.get('Inspector', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')),
                    "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')),
                    "Status": str(r.get('Status', 'N/A')),
                    "Notes": str(r.get('Notes', '')),
                    "Photo": str(r.get('Photo', ''))
                })
            
            # Batching...
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.success("Migration complete with IST Time Correction!")
