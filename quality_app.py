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
st.set_page_config(page_title="B&G Quality Master", layout="wide")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("❌ Secrets missing!")
    st.stop()

# --- 2. DATA UTILITIES ---
def load_all_data():
    try:
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

df = load_all_data()

# --- 3. FIXED DYNAMIC DROPDOWNS ---
# This section ensures that any name ever entered as a "Worker" shows up here
if not df.empty:
    # 1. Get all unique values from the Worker column
    # 2. Remove 'N/A', empty strings, and None values
    raw_workers = df["Worker"].dropna().unique().tolist()
    all_workers = sorted([str(w) for w in raw_workers if str(w).strip() not in ["N/A", "", "None", "nan"]])
    
    # Do the same for Jobs, Inspectors, and Stages
    all_jobs = sorted([str(j) for j in df["Job_Code"].dropna().unique().tolist() if str(j).strip() not in ["N/A", ""]])
    
    base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
    db_inspectors = [str(i) for i in df["Inspector"].dropna().unique().tolist() if str(i).strip() not in ["N/A", ""]]
    all_inspectors = sorted(list(set(base_inspectors + db_inspectors)))
    
    base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]
    db_stages = [str(s) for s in df["Stage"].dropna().unique().tolist() if str(s).strip() not in ["N/A", ""]]
    all_stages = sorted(list(set(base_stages + db_stages)))
else:
    all_workers, all_jobs = [], []
    all_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
    all_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Menu", ["📝 Inspection Entry", "🗂️ Manage Lists", "📂 Migration Tool"])

# --- PAGE 1: ENTRY & LEDGER ---
if menu == "📝 Inspection Entry":
    st.title("Quality Inspection Ledger")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            job = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            wrk = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
        with c2:
            ins = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
            stg = st.selectbox("Stage", ["-- Select --"] + all_stages)
        
        sts = st.radio("Status", ["Passed", "Rework", "Failed"], horizontal=True)
        rem = st.text_area("Notes")
        cam = st.camera_input("Photo Evidence")

        if st.form_submit_button("Submit"):
            if "-- Select --" in [job, wrk, ins, stg]:
                st.warning("Please fill all fields.")
            else:
                save_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                img_str = ""
                if cam:
                    img = Image.open(cam).convert('RGB')
                    img.thumbnail((500, 500))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=50)
                    img_str = base64.b64encode(buf.getvalue()).decode()

                payload = {
                    "created_at": save_time, "Job_Code": job, "Worker": wrk,
                    "Inspector": ins, "Stage": stg, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("Saved!")
                st.rerun()

    st.divider()
    
    # LEDGER DISPLAY
    if not df.empty:
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            view_df['Date'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y')
            view_df['Time'] = pd.to_datetime(view_df['created_at']).dt.strftime('%H:%M')
            view_df['📸 Photo'] = view_df['Photo'].apply(lambda x: "✅" if len(str(x)) > 100 else "❌")
            
            show_cols = ['id', 'Date', 'Time', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo', 'Notes']
            st.dataframe(view_df[show_cols], use_container_width=True)

            # PHOTO PREVIEW AT THE BOTTOM
            st.divider()
            photo_only = view_df[view_df['Photo'].astype(str).str.len() > 100].copy()
            if not photo_only.empty:
                pick = st.selectbox("View Photo for ID:", ["-- Select ID --"] + photo_only['id'].astype(str).tolist())
                if pick != "-- Select ID --":
                    row = photo_only[photo_only['id'].astype(int) == int(pick)].iloc[0]
                    img_data = str(row['Photo'])
                    if "," in img_data: img_data = img_data.split(",")[1]
                    st.image(base64.b64decode(img_data), width=500)

# --- PAGE 2: MANAGE LISTS ---
elif menu == "🗂️ Manage Lists":
    st.title("Manage Lists")
    
    def quick_add(col, val):
        payload = {
            "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 
            "Job_Code": "N/A", "Worker": "N/A", "Inspector": "N/A", 
            "Stage": "N/A", "Status": "N/A", "Notes": "SYS", "Photo": ""
        }
        payload[col] = val
        supabase.table("quality").insert(payload).execute()
        st.success(f"Added {val} to {col}")
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        new_w = st.text_input("New Worker Name")
        if st.button("Add Worker") and new_w: quick_add("Worker", new_w)
    with c2:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job") and new_j: quick_add("Job_Code", new_j)

# --- PAGE 3: MIGRATION TOOL ---
elif menu == "📂 Migration Tool":
    st.title("Corrected Migration")
    if st.button("🚀 Run Migration (Force DD-MM)"):
        if os.path.exists("quality_logs.csv"):
            csv_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in csv_df.iterrows():
                try:
                    ts_obj = pd.to_datetime(r.get('Timestamp', ''), dayfirst=True)
                    clean_ts = ts_obj.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    clean_ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                
                records.append({
                    "created_at": clean_ts, "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')), "Inspector": str(r.get('Inspector', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')), "Status": str(r.get('Status', 'Passed')),
                    "Notes": str(r.get('Notes', '')), "Photo": str(r.get('Photo', ''))
                })
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.success("Migration Successful!")
            st.rerun()
