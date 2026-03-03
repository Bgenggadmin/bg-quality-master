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
    st.error("❌ Secrets missing! Check Streamlit Cloud Secrets.")
    st.stop()

# --- 2. DATABASE FUNCTIONS ---
def load_quality_data():
    try:
        # Fetch data sorted by created_at
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"DB Load Error: {e}")
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

# --- 3. DYNAMIC DROPDOWNS ---
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

if not df.empty:
    all_inspectors = sorted(list(set(base_inspectors + df["Inspector"].dropna().unique().tolist())))
    all_workers = sorted(df["Worker"].dropna().unique().tolist()) if "Worker" in df.columns else []
    all_jobs = sorted(list(set(get_production_jobs() + df["Job_Code"].dropna().unique().tolist())))
    all_stages = sorted(list(set(base_stages + df["Stage"].dropna().unique().tolist())))
    
    # Clean system placeholders
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", "", "None"]]
    all_jobs = [j for j in all_jobs if j not in ["N/A", "", "None"]]
    all_workers = [w for w in all_workers if w not in ["N/A", "", "None"]]
    all_stages = [s for s in all_stages if s not in ["N/A", "", "None"]]
else:
    all_inspectors, all_jobs, all_workers, all_stages = sorted(base_inspectors), get_production_jobs(), [], sorted(base_stages)

# --- 4. SIDEBAR NAVIGATION ---
st.sidebar.title("🛡️ Quality Menu")
menu = st.sidebar.radio("Go to:", ["Inspection Entry", "Manage Lists (Add New)", "View Evidence Photos", "Migration Tool"])

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
                st.warning("⚠️ Please fill all fields.")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam)
                    img.thumbnail((400, 400))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=40)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                # Standardized IST timestamp for database
                now_ist = datetime.now(IST).isoformat()
                
                payload = {
                    "created_at": now_ist,
                    "Inspector": ins, "Worker": wrk, "Job_Code": job, 
                    "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Saved!")
                st.rerun()

    st.divider()
    st.subheader("📋 Inspection Ledger")
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            view_df = view_df.rename(columns={'id': 'ID', 'created_at': 'Timestamp'})
            
            # SAFE DATE CONVERSION
            view_df['Timestamp'] = pd.to_datetime(view_df['Timestamp'], errors='coerce', utc=True)
            view_df['Timestamp'] = view_df['Timestamp'].dt.tz_convert('Asia/Kolkata').dt.strftime('%d-%m-%Y %H:%M')
            
            cols = ['ID', 'Timestamp', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', 'Notes']
            st.dataframe(view_df[cols], use_container_width=True)

            with st.expander("🗑️ Delete Entry"):
                del_id = st.selectbox("Select ID:", ["-- Select --"] + view_df['ID'].tolist())
                if st.button("Confirm Delete") and del_id != "-- Select --":
                    supabase.table("quality").delete().eq("id", del_id).execute()
                    st.rerun()

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Manage App Dropdowns")
    c1, c2 = st.columns(2)
    with c1:
        nw = st.text_input("New Worker")
        if st.button("Save Worker") and nw:
            supabase.table("quality").insert({"Worker": nw, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.rerun()
        nj = st.text_input("New Job Code")
        if st.button("Save Job") and nj:
            supabase.table("quality").insert({"Job_Code": nj, "Notes": "SYS", "Worker": "N/A"}).execute()
            st.rerun()
    with c2:
        ni = st.text_input("New Inspector")
        if st.button("Save Inspector") and ni:
            supabase.table("quality").insert({"Inspector": ni, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.rerun()
        ns = st.text_input("New Stage")
        if st.button("Save Stage") and ns:
            supabase.table("quality").insert({"Stage": ns, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.rerun()

# --- PAGE 3: PHOTO GALLERY ---
elif menu == "View Evidence Photos":
    st.title("🔍 Photo Gallery")
    photo_df = df[df['Photo'].str.len() > 100].copy() if not df.empty else pd.DataFrame()
    if not photo_df.empty:
        photo_df['dt'] = pd.to_datetime(photo_df['created_at'], utc=True).dt.tz_convert('Asia/Kolkata').dt.strftime('%d-%m %H:%M')
        photo_df['label'] = photo_df['Job_Code'] + " | " + photo_df['Stage'] + " (" + photo_df['dt'] + ")"
        choice = st.selectbox("Select Record:", photo_df['label'].tolist())
        if choice:
            row = photo_df[photo_df['label'] == choice].iloc[0]
            st.image(base64.b64decode(row['Photo']), width=700)
            st.write(f"**Inspector:** {row['Inspector']} | **Status:** {row['Status']}")
    else:
        st.info("No photos found.")

# --- PAGE 4: MIGRATION (STRICT & SAFE) ---
elif menu == "Migration Tool":
    st.title("📂 Data Migration")
    if st.button("🚀 Start Corrected Migration"):
        if os.path.exists("quality_logs.csv"):
            try:
                old_df = pd.read_csv("quality_logs.csv").fillna("")
                records = []
                for _, r in old_df.iterrows():
                    # Parse and force to IST before saving
                    raw_ts = r.get('Timestamp', datetime.now(IST))
                    dt_obj = pd.to_datetime(raw_ts, dayfirst=True)
                    if dt_obj.tzinfo is None:
                        dt_obj = IST.localize(dt_obj)
                    
                    records.append({
                        "created_at": dt_obj.isoformat(),
                        "Inspector": str(r.get('Inspector', 'N/A')),
                        "Worker": str(r.get('Worker', 'N/A')),
                        "Job_Code": str(r.get('Job_Code', 'N/A')),
                        "Stage": str(r.get('Stage', 'N/A')),
                        "Status": str(r.get('Status', 'N/A')),
                        "Notes": str(r.get('Notes', '')),
                        "Photo": str(r.get('Photo', ''))
                    })
                
                for i in range(0, len(records), 5):
                    supabase.table("quality").insert(records[i:i+5]).execute()
                st.success("Migration Successful!")
                st.rerun()
            except Exception as e:
                st.error(f"Migration Error: {e}")
