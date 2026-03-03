import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
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
except:
    st.error("❌ Database Connection Error. Check Streamlit Secrets.")
    st.stop()

# --- 2. DATA LOADING ---
def load_all_records():
    try:
        # Fetches newest data first
        response = supabase.table("quality").select("*").order("created_at", desc=True).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

df = load_all_records()

# --- 3. DYNAMIC DROPDOWN LOGIC ---
def get_clean_list(dataframe, column_name, defaults=[]):
    if dataframe.empty:
        return sorted(defaults)
    raw_values = dataframe[column_name].astype(str).unique().tolist()
    # Filter out placeholders and nulls
    clean = [x.strip() for x in raw_values if x.strip() not in ["N/A", "", "None", "nan", "NULL"]]
    return sorted(list(set(clean + defaults)))

# Generate final lists for the UI
all_workers = get_clean_list(df, "Worker")
all_jobs = get_clean_list(df, "Job_Code")
all_inspectors = get_clean_list(df, "Inspector", ["Subodth", "Prasanth", "RamaSai", "Naresh"])
all_stages = get_clean_list(df, "Stage", ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"])

# --- 4. NAVIGATION ---
st.sidebar.title("🛡️ Quality Menu")
menu = st.sidebar.radio("Go to:", ["📝 Inspection Entry", "🗂️ Manage Lists"])

# --- PAGE 1: INSPECTION ENTRY & HISTORY ---
if menu == "📝 Inspection Entry":
    st.title("Quality Inspection Entry")
    
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            job_choice = st.selectbox("Job Code", ["-- Select --"] + all_jobs)
            worker_choice = st.selectbox("Worker Name", ["-- Select --"] + all_workers)
        with c2:
            ins_choice = st.selectbox("Inspector", ["-- Select --"] + all_inspectors)
            stg_choice = st.selectbox("Stage", ["-- Select --"] + all_stages)
        
        sts = st.radio("Status", ["Passed", "Rework", "Failed"], horizontal=True)
        rem = st.text_area("Observations / Notes")
        cam = st.camera_input("📸 Take Photo")

        if st.form_submit_button("🚀 Submit to Cloud"):
            if "-- Select --" in [job_choice, worker_choice, ins_choice, stg_choice]:
                st.warning("⚠️ Please select all dropdown options.")
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
                st.success("✅ Record Successfully Synchronized.")
                st.rerun()

    st.divider()
    
    # LEDGER DISPLAY
    st.subheader("📋 Quality Ledger")
    if not df.empty:
        # Hide system entries
        view_df = df[df['Notes'] != "SYS"].copy()
        if not view_df.empty:
            view_df['Date'] = pd.to_datetime(view_df['created_at']).dt.strftime('%d-%m-%Y')
            view_df['Time'] = pd.to_datetime(view_df['created_at']).dt.strftime('%H:%M')
            view_df['📸 Photo'] = view_df['Photo'].apply(lambda x: "✅" if len(str(x)) > 100 else "❌")
            
            show_cols = ['id', 'Date', 'Time', 'Job_Code', 'Worker', 'Inspector', 'Stage', 'Status', '📸 Photo', 'Notes']
            st.dataframe(view_df[show_cols], use_container_width=True)

            # --- CSV EXPORT BUTTON (Fixed Placement) ---
            csv_data = view_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Ledger as CSV",
                data=csv_data,
                file_name=f"BG_Quality_Report_{datetime.now(IST).strftime('%d-%m-%Y')}.csv",
                mime='text/csv',
            )

            # PHOTO PREVIEW AT THE BOTTOM
            st.divider()
            photo_only = view_df[view_df['Photo'].astype(str).str.len() > 100].copy()
            if not photo_only.empty:
                st.subheader("🔍 Evidence Preview")
                pick = st.selectbox("Select ID to view photo:", ["-- Select ID --"] + photo_only['id'].astype(str).tolist())
                if pick != "-- Select ID --":
                    row = photo_only[photo_only['id'].astype(int) == int(pick)].iloc[0]
                    img_data = str(row['Photo'])
                    if "," in img_data: img_data = img_data.split(",")[1]
                    st.image(base64.b64decode(img_data), width=600)

# --- PAGE 2: MANAGE LISTS ---
elif menu == "🗂️ Manage Lists":
    st.title("Manage Master Dropdowns")
    st.info("Add new items here to make them available in the entry form.")
    
    def add_sys_item(col, val):
        payload = {
            "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'), 
            "Job_Code": val if col == "Job_Code" else "N/A", 
            "Worker": val if col == "Worker" else "N/A", 
            "Inspector": val if col == "Inspector" else "N/A", 
            "Stage": val if col == "Stage" else "N/A", 
            "Status": "N/A", "Notes": "SYS", "Photo": ""
        }
        supabase.table("quality").insert(payload).execute()
        st.success(f"✅ Added '{val}'")
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Workers & Jobs")
        new_w = st.text_input("New Worker Name")
        if st.button("Save Worker") and new_w: add_sys_item("Worker", new_w)
        
        new_j = st.text_input("New Job Code")
        if st.button("Save Job") and new_j: add_sys_item("Job_Code", new_j)
    
    with col2:
        st.subheader("Stages & Inspectors")
        new_s = st.text_input("New Inspection Stage")
        if st.button("Save Stage") and new_s: add_sys_item("Stage", new_s)
        
        new_i = st.text_input("New Inspector Name")
        if st.button("Save Inspector") and new_i: add_sys_item("Inspector", new_i)
