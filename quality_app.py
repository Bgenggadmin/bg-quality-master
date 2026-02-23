import streamlit as st
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# --- 1. SECURITY ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("✅ B&G Quality Master Access")
    pwd = st.text_input("Enter Quality Password", type="password")
    if st.button("Log In"):
        if pwd == "BGQUALITY": 
            st.session_state["authenticated"] = True
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 2. MAIN INTERFACE ---
st.title("✅ B&G Engineering: Quality Master")
tabs = st.tabs(["📸 New Inspection", "📊 History & Reports"])

with tabs[0]:
    st.subheader("Record Technical Inspection")
    
    # Core B&G technical checks
    tests = ["Marking", "Fitup", "Nozzle Orientation", "PMI", "Runout", "Load Test", "Hydrotest", "DP Test", "FAT", "Surface Finish"]
    inspectors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]

    c1, c2 = st.columns(2)
    with c1:
        inspector = st.selectbox("Inspector Name", inspectors)
        job_code = st.text_input("Job Code (e.g., SSR501)", placeholder="Enter Project ID")
        test_type = st.selectbox("Inspection Stage", tests)
    with c2:
        status = st.radio("Inspection Status", ["🟢 Passed", "🔴 Rework Required"])
        remarks = st.text_area("Observations/Remarks")

    # --- UPDATED PHOTO SECTION ---
    st.write("---")
    st.write("### 🖼️ Photo Evidence")
    
    # Option 1: Live Camera
    cam_photo = st.camera_input("Take Live Shopfloor Photo")
    
    # Option 2: File Upload (Backup)
    upload_photo = st.file_uploader("Or Upload from Gallery", type=["jpg", "png", "jpeg"])

    # Processing the image
    final_img_str = ""
    photo_to_process = cam_photo if cam_photo else upload_photo

    if photo_to_process:
        img = Image.open(photo_to_process)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        final_img_str = base64.b64encode(buffered.getvalue()).decode()
        st.success("Photo captured and processed!")

    if st.button("Submit Quality Record"):
        if job_code:
            now = datetime.now()
            # Saving to CSV for B&G records
            row = f"{now.strftime('%Y-%m-%d %H:%M')},{inspector},{job_code},{test_type},{status},{remarks.replace(',',';')},{final_img_str}\n"
            with open("bg_quality_records.csv", "a") as f:
                f.write(row)
            st.balloons()
            st.success(f"Inspection for {job_code} logged successfully!")
        else:
            st.warning("Please enter a Job Code before submitting.")

with tabs[1]:
    st.subheader("Inspection History")
    try:
        df = pd.read_csv("bg_quality_records.csv", names=["Timestamp","Inspector","Job","Test","Status","Remarks","PhotoData"])
        st.dataframe(df.iloc[:, :-1].sort_values(by="Timestamp", ascending=False))
    except:
        st.info("No records found yet.")
