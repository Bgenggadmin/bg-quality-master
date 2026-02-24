import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image
import os

# --- 1. LOCAL STORAGE SETUP ---
DB_FILE = "quality_data.csv"

# Load existing data from the app's internal memory
if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(columns=["Timestamp", "Inspector", "Job_Code", "Stage", "Status", "Notes", "Photo"])

st.title("✅ B&G Quality Master")

# --- 2. BACKEND BACKUP BAR (Save to your PC) ---
with st.expander("📥 BACKEND CONTROL: Save Data to Local System"):
    if not df.empty:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="DOWNLOAD ALL RECORDS TO EXCEL",
            data=csv,
            file_name=f"BG_Quality_Backup_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        if st.button("Clear App Memory (Start Fresh)"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
                st.rerun()
    else:
        st.write("No data in backend yet.")

# --- 3. INSPECTION FORM ---
st.divider()
with st.form("quality_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        inspector = st.selectbox("Inspector", ["Prasanth", "RamaSai", "Subodth", "Naresh"])
        job = st.text_input("Job Code (e.g. SSR501)")
        stage = st.selectbox("Stage", ["Marking", "Fitup", "Hydro", "Final"])
    with c2:
        status = st.radio("Status", ["🟢 Passed", "🔴 Rework"])
        notes = st.text_area("Notes")

    photo = st.camera_input("Take Shopfloor Photo")
    
    if st.form_submit_button("Submit to App Backend"):
        # Process Photo to text
        img_str = "No Photo"
        if photo:
            img = Image.open(photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

        # Add to records
        new_row = pd.DataFrame([{
            "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "Inspector": inspector,
            "Job_Code": job,
            "Stage": stage,
            "Status": status,
            "Notes": notes,
            "Photo": img_str
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(DB_FILE, index=False)
        st.success(f"Record for {job} saved to app memory!")
        st.balloons()

# --- 4. VIEW LOGS ---
st.divider()
st.subheader("📊 Recent Inspection Logs")
st.dataframe(df.drop(columns=["Photo"]).sort_values(by="Timestamp", ascending=False))
