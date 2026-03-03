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
        # We fetch from DB (YYYY-MM-DD) but we will format it in Python
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

df = load_quality_data()

# --- 3. DYNAMIC DROPDOWNS ---
if not df.empty:
    all_workers = sorted([w for w in df["Worker"].dropna().unique().tolist() if w not in ["N/A", ""]])
    all_inspectors = sorted(list(set(["Subodth", "Prasanth", "RamaSai", "Naresh"] + df["Inspector"].dropna().unique().tolist())))
    all_stages = sorted(list(set(["RM Inspection", "Marking", "Fit-up", "Welding", "Final"] + df["Stage"].dropna().unique().tolist())))
    all_jobs = sorted(list(set(df["Job_Code"].dropna().unique().tolist())))
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", ""]]
else:
    all_workers, all_inspectors, all_stages, all_jobs = [], ["Subodth", "Prasanth", "RamaSai", "Naresh"], ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"], []

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Inspection Entry", "Manage Lists", "Migration Tool"])

# --- PAGE 1: ENTRY & LEDGER ---
if menu == "Inspection Entry":
    st.title("📝 Quality Inspection & History")
    
    # Entry Form 
    with st.form("qc_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
        with c2:
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
            sts = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
            rem = st.text_area("Notes")
        
        cam = st.camera_input("Capture Photo")
        
        if st.form_submit_button("Submit Inspection"):
            if "-- Select --" in [job, wrk, ins, stg]:
                st.warning("Please fill all fields.")
            else:
                # SAVE to DB in YYYY-MM-DD (ISO Format)
                now_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                img_str = ""
                if cam:
                    img = Image.open(cam).convert('RGB')
                    img.thumbnail((500, 500))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=50)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                payload = {"created_at": now_ist, "Job_Code": job, "Worker": wrk, "Inspector": ins, "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str}
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Saved Successfully!")
                st.rerun()

    st.divider()

    # --- SUMMARY TABLE ---
    st.subheader("📋 Inspection History")
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            # FORCE DISPLAY FORMAT: DD-MM-YYYY
            view_df['Date'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y')
            view_df['Time'] = pd.to_datetime(view_df['created_at']).dt.strftime('%H:%M')
            
            # Show "Yes/No" for photo
            view_df['📸 Photo'] = view_df['Photo'].apply(lambda x: "✅" if len(str(x)) > 100 else "❌")
            
            show_cols = ['id', 'Date', 'Time', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo', 'Notes']
            st.dataframe(view_df[show_cols], use_container_width=True)

            # --- PHOTO PREVIEW AT BOTTOM ---
            st.divider()
            photo_only = view_df[view_df['Photo'].astype(str).str.len() > 100].copy()
            if not photo_only.empty:
                pick = st.selectbox("Select Record to View Photo:", ["-- Select --"] + photo_only['id'].astype(str).tolist())
                if pick != "-- Select --":
                    row = photo_only[photo_only['id'].astype(int) == int(pick)].iloc[0]
                    raw_data = str(row['Photo'])
                    if "," in raw_data: raw_data = raw_data.split(",")[1]
                    st.image(base64.b64decode(raw_data), width=500, caption=f"ID: {pick}")

# --- PAGE 3: MIGRATION (FIX DATE SWAP) ---
elif menu == "Migration Tool":
    st.title("📂 Migration (Force DD-MM Fix)")
    
    if st.button("🗑️ CLEAR ALL DATA"):
        supabase.table("quality").delete().neq("id", 0).execute()
        st.success("Database cleared!")
        st.rerun()

    if st.button("🚀 Run Migration"):
        if os.path.exists("quality_logs.csv"):
            old_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in old_df.iterrows():
                try:
                    # dayfirst=True ensures 02-03 is MARCH 2nd
                    ts_obj = pd.to_datetime(r.get('Timestamp', ''), dayfirst=True)
                    clean_ts = ts_obj.strftime('%Y-%m-%d %H:%M:%S')
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
            st.success("Migration complete! Dates are correct in App.")
            st.rerun()
