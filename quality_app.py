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
        # ORDER BY created_at DESC ensures LATEST data is 1st
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
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

if not df.empty:
    all_workers = sorted([w for w in df["Worker"].dropna().unique().tolist() if w not in ["N/A", ""]])
    all_inspectors = sorted(list(set(base_inspectors + df["Inspector"].dropna().unique().tolist())))
    all_stages = sorted(list(set(base_stages + df["Stage"].dropna().unique().tolist())))
    all_jobs = sorted(list(set(get_production_jobs() + df["Job_Code"].dropna().unique().tolist())))
    # Remove system placeholders
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", ""]]
    all_stages = [s for s in all_stages if s not in ["N/A", ""]]
else:
    all_workers, all_inspectors, all_stages, all_jobs = [], base_inspectors, base_stages, get_production_jobs()

# --- 4. NAVIGATION ---
st.sidebar.title("🛡️ Quality Menu")
menu = st.sidebar.radio("Go to:", ["Inspection Entry", "Manage Lists (Add New)", "View Evidence Photos", "Migration Tool"])

# --- PAGE 1: INSPECTION ENTRY & LEDGER ---
if menu == "Inspection Entry":
    st.title("📝 Quality Inspection Entry")
    with st.form("qc_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
        with c2:
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
            sts = st.radio("Result", ["Passed", "Rework", "Failed"], horizontal=True)
            rem = st.text_area("Observations")
        
        cam = st.camera_input("Capture Photo Evidence")
        
        if st.form_submit_button("🚀 Submit Inspection"):
            if "-- Select --" in [job, wrk, ins, stg]:
                st.warning("⚠️ Please fill all required fields.")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam).convert('RGB')
                    img.thumbnail((500, 500))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=50)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                # Manual IST Timestamp
                now_ist = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                payload = {
                    "created_at": now_ist, "Job_Code": job, "Worker": wrk, 
                    "Inspector": ins, "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Inspection Saved!")
                st.rerun()

    st.divider()
    st.subheader("📋 Inspection Ledger (Newest First)")
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            # 1. Format Timestamp
            view_df['Timestamp'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
            # 2. Add Photo Status Column
            view_df['📸 Photo'] = view_df['Photo'].apply(lambda x: "✅ Yes" if len(str(x)) > 100 else "❌ No")
            
            show_cols = ['id', 'Timestamp', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo', 'Notes']
            st.dataframe(view_df[show_cols], use_container_width=True)

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Manage Dynamic Dropdowns")
    col1, col2 = st.columns(2)
    with col1:
        new_w = st.text_input("New Worker Name")
        if st.button("Add Worker") and new_w:
            supabase.table("quality").insert({"Worker": new_w, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.success(f"Added {new_w}"); st.rerun()
            
        new_j = st.text_input("New Job Code")
        if st.button("Add Job Code") and new_j:
            supabase.table("quality").insert({"Job_Code": new_j, "Notes": "SYS", "Worker": "N/A"}).execute()
            st.success(f"Added {new_j}"); st.rerun()
    with col2:
        new_s = st.text_input("New Stage (e.g. Painting)")
        if st.button("Add Stage") and new_s:
            supabase.table("quality").insert({"Stage": new_s, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.success(f"Added {new_s}"); st.rerun()

# --- PAGE 3: VIEW PHOTOS (FIXED DECODING) ---
elif menu == "View Evidence Photos":
    st.title("🔍 Photo Evidence Gallery")
    if not df.empty and "Photo" in df.columns:
        photo_df = df[df['Photo'].astype(str).str.len() > 100].copy()
        if not photo_df.empty:
            photo_df['label'] = photo_df['Job_Code'] + " | " + photo_df['Stage'] + " (" + photo_df['created_at'].astype(str) + ")"
            choice = st.selectbox("Select Record:", photo_df['label'].tolist())
            if choice:
                row = photo_df[photo_df['label'] == choice].iloc[0]
                try:
                    raw_data = str(row['Photo'])
                    if "," in raw_data: raw_data = raw_data.split(",")[1]
                    st.image(base64.b64decode(raw_data), use_container_width=True)
                    st.write(f"**Inspector:** {row['Inspector']} | **Worker:** {row['Worker']}")
                except: st.error("❌ Could not decode this photo.")
        else: st.info("No photos found.")

# --- PAGE 4: MIGRATION ---
elif menu == "Migration Tool":
    st.title("📂 Migration")
    if st.button("🚀 Start Migration with Actual Times"):
        if os.path.exists("quality_logs.csv"):
            old_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in old_df.iterrows():
                try:
                    ts = pd.to_datetime(r.get('Timestamp', ''), dayfirst=True).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                records.append({
                    "created_at": ts, "Inspector": str(r.get('Inspector', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')), "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')), "Status": str(r.get('Status', 'Passed')),
                    "Notes": str(r.get('Notes', '')), "Photo": str(r.get('Photo', ''))
                })
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.success("Migration Done!"); st.rerun()
