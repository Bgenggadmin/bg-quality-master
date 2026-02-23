import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
import extra_streamlit_components as cookie_manager

# --- 1. PERSISTENT LOGIN (COOKIE) ---
controller = cookie_manager.CookieManager()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Wait for cookies to load
all_cookies = controller.get_all()
if not all_cookies:
    st.stop()

# Check for existing 30-day login
if controller.get("bg_quality_login") == "true":
    st.session_state["authenticated"] = True

# --- 2. LOGIN INTERFACE ---
if not st.session_state["authenticated"]:
    st.title("✅ B&G Quality: Secure Access")
    pwd = st.text_input("Enter Quality Password", type="password")
    remember = st.checkbox("Keep me logged in for 30 days")
    
    if st.button("Log In"):
        if pwd == "BGQUALITY": 
            st.session_state["authenticated"] = True
            if remember:
                # Set cookie for 30 days
                controller.set("bg_quality_login", "true", expires_at=datetime.now() + timedelta(days=30))
            st.rerun()
        else: 
            st.error("Access Denied")
    st.stop()

# --- 3. MAIN INTERFACE (Camera Enabled) ---
st.title("✅ B&G Engineering: Quality Master")
tests = ["Marking", "Fitup", "Nozzle Orientation", "PMI", "Hydrotest", "DP Test", "FAT"]
inspectors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]

with st.form("quality_form"):
    inspector = st.selectbox("Inspector Name", inspectors)
    job_code = st.text_input("Job Code (e.g., SSR501)")
    test_type = st.selectbox("Inspection Stage", tests)
    status = st.radio("Status", ["🟢 Passed", "🔴 Rework"])
    
    st.write("### 📸 Photo Evidence")
    cam_photo = st.camera_input("Take Live Shopfloor Photo") #
    upload_photo = st.file_uploader("Or Upload Gallery Photo", type=["jpg", "png"])
    
    if st.form_submit_button("Submit Record"):
        # Process image to Base64
        photo = cam_photo if cam_photo else upload_photo
        img_str = ""
        if photo:
            img = Image.open(photo)
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
        # Log to CSV
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        row = f"{now},{inspector},{job_code},{test_type},{status},{img_str}\n"
        with open("bg_quality_records.csv", "a") as f:
            f.write(row)
        st.success("Inspection Logged!")
