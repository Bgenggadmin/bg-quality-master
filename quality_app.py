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
st.set_page_config(page_title="B&G Quality Master", layout="wide")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except:
    st.error("❌ Secrets missing!")
    st.stop()

# --- 2. DATA LOADING ---
@st.cache_data(ttl=5) # Refresh every 5 seconds to catch new list items
def load_all_records():
    try:
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

df = load_all_records()

# --- 3. FIXED DYNAMIC DROPDOWNS (AGGRESSIVE SCAN) ---
def get_clean_list(dataframe, column_name):
    if dataframe.empty or column_name not in dataframe.columns:
        return []
    # Pull every unique value, convert to string, remove spaces, and filter out junk
    raw_list = dataframe[column_name].astype(str).unique().tolist()
    clean_list = [x.strip() for x in raw_list if x.strip() not in ["N/A", "", "None", "nan", "NULL"]]
    return sorted(list(set(clean_list)))

# Generate lists
all_workers = get_clean_list(df, "Worker")
all_jobs = get_clean_list(df, "Job_Code")

# Default UI Lists
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
db_inspectors = get_clean_list(df, "Inspector")
all_inspectors = sorted(list(set(base_inspectors + db_inspectors)))

base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]
db_stages = get_clean_list(df, "Stage")
all_stages = sorted(list(set(base_stages + db_stages)))

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Menu", ["📝 Inspection Entry", "🗂️ Manage Lists", "📂 Migration Tool"])

# --- PAGE 1: ENTRY & LEDGER ---
if menu == "📝 Inspection Entry":
    st.title("Quality Inspection Ledger")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            # Use the dynamically generated lists here
            job_choice = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            worker_choice = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
        with c2:
            ins_choice = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
            stg_choice = st.selectbox("Stage", ["-- Select --"] + all_stages)
        
        sts = st.radio("Status", ["Passed", "Rework", "Failed"], horizontal=True)
        rem = st.text_area("Notes")
        cam = st.camera_input("Photo Evidence")

        if st.form_submit_button("Submit"):
            if "-- Select --" in [job_choice, worker_choice, ins_choice, stg_choice]:
                st.warning("⚠️ Please select all fields from the dropdowns.")
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
                    "created_at": save_time, "Job_Code": job_choice, "Worker": worker_choice,
                    "Inspector": ins_choice, "Stage": stg_choice, "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Record Saved!")
                st.cache_data.clear() # Clear cache to show new entry immediately
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

# --- PAGE 2: MANAGE LISTS (FIXED RECOVERY) ---
elif menu == "🗂️ Manage Lists":
    st.title("Manage Dropdowns")
    st.write("Add missing Workers or Job Codes here:")
    
    def quick_add_system(col, val):
        # We fill with 'SYS' so it stays hidden in ledger but visible in dropdowns
        payload = {
            "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 
            "Job_Code": val if col == "Job_Code" else "N/A", 
            "Worker": val if col == "Worker" else "N/A", 
            "Inspector": val if col == "Inspector" else "N/A", 
            "Stage": val if col == "Stage" else "N/A", 
            "Status": "N/A", "Notes": "SYS", "Photo": ""
        }
        supabase.table("quality").insert(payload).execute()
        st.cache_data.clear()
        st.success(f"Added '{val}' to lists.")
        st.rerun()

    c1, c2 = st.columns(2)
    with c1:
        new_w = st.text_input("New Worker Name")
        if st.button("Add Worker") and new_w: quick_add_system("Worker", new_w)
    with c2:
        new_j = st.text_input("New Job Code")
        if st.button("Add Job") and new_j: quick_add_system("Job_Code", new_j)

# --- PAGE 3: MIGRATION ---
elif menu == "📂 Migration Tool":
    st.title("Data Migration")
    if st.button("🚀 Run Migration"):
        if os.path.exists("quality_logs.csv"):
            csv_df = pd.read_csv("quality_logs.csv").fillna("")
            records = []
            for _, r in csv_df.iterrows():
                try:
                    ts = pd.to_datetime(r.get('Timestamp', ''), dayfirst=True).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    ts = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')
                records.append({
                    "created_at": ts, "Job_Code": str(r.get('Job_Code', 'N/A')),
                    "Worker": str(r.get('Worker', 'N/A')), "Inspector": str(r.get('Inspector', 'N/A')),
                    "Stage": str(r.get('Stage', 'N/A')), "Status": str(r.get('Status', 'Passed')),
                    "Notes": str(r.get('Notes', '')), "Photo": str(r.get('Photo', ''))
                })
            for i in range(0, len(records), 5):
                supabase.table("quality").insert(records[i:i+5]).execute()
            st.cache_data.clear()
            st.success("Migration Done!")
