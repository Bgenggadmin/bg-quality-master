import streamlit as st
import pandas as pd
from datetime import datetime
import os
import base64
from PIL import Image
import io

# --- 1. DATA FILES ---
QUALITY_LOG = "bg_quality_records_v3.csv"

# --- 2. IMAGE HELPER ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        # Resize to keep the file small for GitHub storage
        img.thumbnail((400, 400))
        buffered = io.BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

# --- 3. SECURITY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🛡️ B&G Quality Control Access")
    pwd = st.text_input("Enter Quality Dept Password", type="password")
    if st.button("Log In"):
        if pwd == "BGQUALITY": 
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 4. MAIN INTERFACE ---
st.title("✅ B&G Engineering: Quality Assurance")
tabs = st.tabs(["📋 Inspection Log", "📊 Quality Analytics"])

with tabs[0]:
    st.subheader("New Quality Inspection Entry")
    supervisors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]
    inspection_types = ["Marking","Fitup","Nozzle Orientation","PMI (Material ID)","Runout","Load Test","Hydrotest","DP Test","FAT","Surface Finish"]
    
    c1, c2 = st.columns(2)
    with c1:
        inspector = st.selectbox("Inspector Name", supervisors)
        job_code = st.text_input("Job Code (e.g., DIST-05)")
    with c2:
        test_type = st.selectbox("Inspection Type", inspection_types)
        status = st.radio("Result Status", ["✅ PASSED", "❌ REWORK"])

    # --- PHOTO UPLOAD OPTION ---
    st.write("📷 **Upload Evidence (Photo of Test/Job)**")
    # This works with both mobile cameras and gallery
    img_file = st.file_uploader("Take a photo or choose a file", type=['jpg', 'png', 'jpeg'])
    
    details = st.text_area("Technical Remarks")

    if st.button("Submit Quality Report"):
        img_str = image_to_base64(img_file)
        now = datetime.now()
        # Row: Date, Time, Inspector, Job, Test, Status, Remarks, Image_Data
        row = f"{now.strftime('%Y-%m-%d')},{now.strftime('%H:%M')},{inspector},{job_code},{test_type},{status},{details.replace(',','|')},{img_str}\n"
        with open(QUALITY_LOG, "a") as f: f.write(row)
        st.success(f"Quality Report with Photo Saved!")

with tabs[1]:
    st.subheader("Inspection History & Photos")
    if os.path.exists(QUALITY_LOG):
        df = pd.read_csv(QUALITY_LOG, names=["Date","Time","Inspector","Job","Test","Status","Remarks","PhotoData"])
        
        search_job = st.text_input("Search Job Code (e.g., DIST-05)")
        if search_job:
            filtered_df = df[df["Job"].str.contains(search_job, case=False)]
            for index, row in filtered_df.iterrows():
                with st.container():
                    col_text, col_img = st.columns([2, 1])
                    with col_text:
                        st.write(f"**Date:** {row['Date']} | **Test:** {row['Test']}")
                        st.write(f"**Status:** {row['Status']} | **Inspector:** {row['Inspector']}")
                        st.write(f"**Notes:** {row['Remarks']}")
                    with col_img:
                        if pd.notnull(row['PhotoData']) and row['PhotoData'] != "":
                            st.image(base64.b64decode(row['PhotoData']), use_container_width=True)
                    st.divider()
    else:
        st.info("No records yet.")
