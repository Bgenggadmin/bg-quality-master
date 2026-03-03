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
        # DESC=True ensures 03-03 (March) is ABOVE 02-03 (February)
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
    # Clean list
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", ""]]
else:
    all_workers, all_inspectors, all_stages, all_jobs = [], ["Subodth", "Prasanth", "RamaSai", "Naresh"], ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"], get_production_jobs()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Inspection Entry", "Manage Lists", "Migration Tool"])

# --- PAGE 1: ENTRY & LEDGER & PHOTO ---
if menu == "Inspection Entry":
    st.title("📝 Quality Inspection & History")
    
    # --- SECTION A: ENTRY FORM ---
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
                st.warning("Please select all fields.")
            else:
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

    # --- SECTION B: SUMMARY TABLE ---
    st.subheader("📋 Inspection History (Newest First)")
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            # Date format fix for Table
            view_df['Timestamp'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y %H:%M')
            # Status for photo
            view_df['📸 Photo Status'] = view_df['Photo'].apply(lambda x: "✅ Available" if len(str(x)) > 100 else "❌ No Photo")
            
            show_cols = ['id', 'Timestamp', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo Status', 'Notes']
            st.dataframe(view_df[show_cols], use_container_width=True)

            # --- SECTION C: PHOTO PREVIEW (AT BOTTOM) ---
            st.divider()
            st.subheader("🔍 Selected Photo Preview")
            
            # Filter rows that actually have photos
            photo_only = view_df[view_df['Photo'].astype(str).str.len() > 100].copy()
            if not photo_only.empty:
                photo_only['Label'] = photo_only['Job_Code'] + " | " + photo_only['Stage'] + " (" + photo_only['Timestamp'] + ")"
                pick = st.selectbox("Select a record from the list above to view its photo:", ["-- Select --"] + photo_only['Label'].tolist())
                
                if pick != "-- Select --":
                    row = photo_only[photo_only['Label'] == pick].iloc[0]
                    raw_data = str(row['Photo'])
                    if "," in raw_data: raw_data = raw_data.split(",")[1]
                    
                    st.image(base64.b64decode(raw_data), use_container_width=True, caption=f"Evidence for {pick}")
            else:
                st.info("No photos recorded yet in the history.")

# --- PAGE 2: MANAGE LISTS ---
elif menu == "Manage Lists":
    st.title("🗂️ Manage Names & Stages")
    c1, c2 = st.columns(2)
    with c1:
        nw = st.text_input("New Worker Name")
        if st.button("Add Worker") and nw:
            supabase.table("quality").insert({"Worker": nw, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.rerun()
    with c2:
        ns = st.text_input("New Stage Name")
        if st.button("Add Stage") and ns:
            supabase.table("quality").insert({"Stage": ns, "Notes": "SYS", "Job_Code": "N/A"}).execute()
            st.rerun()

# --- PAGE 3: MIGRATION (WITH DATE FIX) ---
elif menu == "Migration Tool":
    st.title("📂 Migration & Clean Up")
    
    if st.button("🗑️ CLEAR ALL DATA (Restart Fresh)"):
        # Warning: This clears everything
        supabase.table("quality").delete().neq("id", 0).execute()
        st.success("Database cleared!")
        st.rerun()

    if st.button("🚀 Start Migration (Force March 2nd/3rd)"):
        if os.path.exists("quality_logs.csv"):
            old_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in old_df.iterrows():
                # FIXED: Force DD-MM format for Indian Dates
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
            st.success("Migration complete! Dates are now correct.")
            st.rerun()
