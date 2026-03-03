import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import base64
from io import BytesIO
from PIL import Image
from supabase import create_client, Client

# --- 1. SETUP & CONNECTION ---
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
        # Fetches dynamic Job Codes from the Production table
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
# Default lists in case DB is empty
base_inspectors = ["Subodth", "Prasanth", "RamaSai", "Naresh"]
base_stages = ["RM Inspection", "Marking", "Fit-up", "Welding", "Final"]

if not df.empty:
    # Combine defaults with any unique values found in the database
    all_inspectors = sorted(list(set(base_inspectors + df["Inspector"].dropna().unique().tolist())))
    all_stages = sorted(list(set(base_stages + df["Stage"].dropna().unique().tolist())))
    all_jobs = get_production_jobs()
    
    # Filter out system placeholders from dropdowns
    all_inspectors = [i for i in all_inspectors if i not in ["N/A", ""]]
    all_stages = [s for s in all_stages if s not in ["N/A", ""]]
else:
    all_inspectors = sorted(base_inspectors)
    all_stages = sorted(base_stages)
    all_jobs = get_production_jobs()

# --- PAGE 1: INSPECTION ENTRY ---
if menu == "Inspection Entry":
    st.title("📝 New Quality Inspection")
    
    with st.form("qc_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            job = st.selectbox("Select Job Code", ["-- Select --"] + all_jobs)
            ins = st.selectbox("Select Inspector", ["-- Select --"] + all_inspectors)
        with col2:
            stg = st.selectbox("Select Stage", ["-- Select --"] + all_stages)
            sts = st.radio("Inspection Result", ["Passed", "Rework", "Failed"], horizontal=True)

        rem = st.text_area("Observations / Remarks")
        cam = st.camera_input("Capture Photo Evidence")
        
        if st.form_submit_button("🚀 Submit Inspection"):
            if "-- Select --" in [job, ins, stg]:
                st.warning("⚠️ Please select Job, Inspector, and Stage.")
            else:
                img_str = ""
                if cam:
                    img = Image.open(cam)
                    img.thumbnail((400, 400)) # Compress for DB storage
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=40, optimize=True)
                    img_str = base64.b64encode(buf.getvalue()).decode()
                
                payload = {
                    "created_at": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                    "Inspector": ins, "Job_Code": job, "Stage": stg,
                    "Status": sts, "Notes": rem, "Photo": img_str
                }
                supabase.table("quality").insert(payload).execute()
                st.success("✅ Inspection Saved Successfully!")
                st.rerun()

    st.divider()
    st.subheader("📋 Recent Inspection Ledger")
    if not df.empty:
        # Filter out "SYSTEM_ADD" rows so the ledger only shows real inspections
        view_df = df[df['Notes'] != "SYSTEM_ADD"].copy()
        if not view_df.empty:
            view_df = view_df.rename(columns={'id': 'ID', 'created_at': 'Timestamp'})
            view_df['Timestamp'] = pd.to_datetime(view_df['Timestamp']).dt.strftime('%d-%m-%Y %H:%M')
            cols = ['ID', 'Timestamp', 'Inspector', 'Job_Code', 'Stage', 'Status', 'Notes']
            st.dataframe(view_df[cols], use_container_width=True)

            # DELETE SECTION
            with st.expander("🗑️ Delete Accidental Entry"):
                del_id = st.selectbox("Select ID to Delete", ["-- Select --"] + view_df['ID'].tolist())
                if st.button("Confirm Delete"):
                    if del_id != "-- Select --":
                        supabase.table("quality").delete().eq("id", del_id).execute()
                        st.success(f"Entry {del_id} deleted!")
                        st.rerun()
        else:
            st.info("No inspection records logged yet.")

# --- PAGE 2: MANAGE LISTS (DYNAMIC ADD) ---
elif menu == "Manage Lists (Add New)":
    st.title("🗂️ Manage Dynamic Lists")
    st.info("Add new items here to update the dropdowns in the Inspection Entry form.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Add Inspector")
        new_i = st.text_input("New Inspector Name")
        if st.button("Add Inspector") and new_i:
            # We use a system flag in 'Notes' to hide these from the ledger
            supabase.table("quality").insert({"Inspector": new_i, "Notes": "SYSTEM_ADD", "Job_Code": "N/A", "Stage": "N/A"}).execute()
            st.success(f"Added {new_i}")
            st.rerun()

    with c2:
        st.subheader("Add Stage")
        new_s = st.text_input("New Inspection Stage (e.g., Hydro Test)")
        if st.button("Add Stage") and new_s:
            supabase.table("quality").insert({"Stage": new_s, "Notes": "SYSTEM_ADD", "Job_Code": "N/A", "Inspector": "N/A"}).execute()
            st.success(f"Added {new_s}")
            st.rerun()

# --- PAGE 3: PHOTO VIEWER ---
elif menu == "View Evidence Photos":
    st.title("🔍 Quality Evidence Gallery")
    # Only show records that actually have a photo attached
    photo_df = df[df['Photo'].str.len() > 50].copy() if not df.empty else pd.DataFrame()
    
    if not photo_df.empty:
        photo_df['label'] = photo_df['Job_Code'] + " | " + photo_df['Stage'] + " (" + photo_df['created_at'].astype(str) + ")"
        choice = st.selectbox("Select Inspection Record to View Photo:", photo_df['label'].tolist())
        
        if choice:
            row = photo_df[photo_df['label'] == choice].iloc[0]
            st.image(base64.b64decode(row['Photo']), caption=f"Evidence: {row['Job_Code']} - {row['Stage']}", width=700)
            st.write(f"**Inspector:** {row['Inspector']} | **Status:** {row['Status']}")
            st.info(f"**Remarks:** {row['Notes']}")
    else:
        st.info("No photos found in the database.")

# --- PAGE 4: MIGRATION (FIXED FOR JSON) ---
elif menu == "Migration Tool":
    st.title("📂 Data Migration")
    st.warning("This tool moves your old quality_logs.csv data into the cloud.")
    
    if st.button("🚀 Start Migration"):
        if os.path.exists("quality_logs.csv"):
            try:
                old_df = pd.read_csv("quality_logs.csv")
                
                # Column & Date Fix
                if 'Timestamp' in old_df.columns:
                    old_df['created_at'] = pd.to_datetime(old_df['Timestamp'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
                    old_df = old_df.drop(columns=['Timestamp'])
                
                # CRITICAL: Clean for JSON Compliance
                old_df = old_df.fillna("") 
                
                data_records = old_df.to_dict(orient='records')
                progress = st.progress(0)
                
                # Small batch size (3) because photos are very heavy
                batch_size = 3 
                for i in range(0, len(data_records), batch_size):
                    batch = data_records[i:i + batch_size]
                    supabase.table("quality").insert(batch).execute()
                    percent = min((i + batch_size) / len(data_records), 1.0)
                    progress.progress(percent)
                
                st.success(f"✅ Migrated {len(data_records)} records!")
                st.balloons()
            except Exception as e:
                st.error(f"Migration failed: {e}")
        else:
            st.error("File 'quality_logs.csv' not found.")
