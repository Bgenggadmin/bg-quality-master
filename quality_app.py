import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import base64
from io import BytesIO
from PIL import Image
import extra_streamlit_components as cookie_manager

# --- 1. CONFIG & DATA ---
# This list will be integrated with the Production app in the next step
default_jobs = ["SSR501", "SSR502", "PROJECT-A", "PROJECT-B"] 
inspectors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]
tests = ["Marking", "Fitup", "Nozzle Orientation", "PMI", "Hydrotest", "DP Test", "FAT"]

# --- 2. PERSISTENT LOGIN & COOKIES ---
controller = cookie_manager.CookieManager()
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# Check for existing 30-day login
all_cookies = controller.get_all()
if all_cookies and controller.get("bg_quality_login") == "true":
    st.session_state["authenticated"] = True

if not st.session_state["authenticated"]:
    st.title("✅ B&G Quality: Secure Access")
    pwd = st.text_input("Enter Quality Password", type="password")
    remember = st.checkbox("Keep me logged in for 30 days")
    if st.button("Log In"):
        if pwd == "BGQUALITY": 
            st.session_state["authenticated"] = True
            if remember:
                controller.set("bg_quality_login", "true", expires_at=datetime.now() + timedelta(days=30))
            st.rerun()
        else: st.error("Access Denied")
    st.stop()

# --- 3. MAIN INTERFACE ---
st.title("✅ B&G Engineering: Quality Master")
tab1, tab2, tab3 = st.tabs(["📸 New Inspection", "📊 View Records", "⚙️ Admin Tool"])

with tab1:
    with st.form("quality_form"):
        c1, c2 = st.columns(2)
        with c1:
            inspector = st.selectbox("Inspector Name", inspectors)
            job_code = st.selectbox("Integrated Job Code", default_jobs) # Integrated list
            test_type = st.selectbox("Inspection Stage", tests)
        with c2:
            status = st.radio("Status", ["🟢 Passed", "🔴 Rework Required"])
            # ADDED: Technical Notes Section
            notes = st.text_area("📋 Technical Notes / Observations", placeholder="Enter specific vessel details...")

        st.write("### 🖼️ Photo Evidence")
        cam_photo = st.camera_input("Take Live Shopfloor Photo") #
        
        if st.form_submit_button("Submit Quality Record"):
            # Process Image
            img_str = ""
            if cam_photo:
                img = Image.open(cam_photo)
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Save Record
            now = datetime.now().strftime('%Y-%m-%d %H:%M')
            # Formatting notes to avoid CSV errors
            safe_notes = notes.replace(",", ";").replace("\n", " ")
            row = f"{now},{inspector},{job_code},{test_type},{status},{safe_notes},{img_str}\n"
            with open("bg_quality_records.csv", "a") as f:
                f.write(row)
            st.success(f"Record for {job_code} saved!")

with tab2:
    st.subheader("Inspection History")
    try:
        df = pd.read_csv("bg_quality_records.csv", names=["Time","Inspector","Job","Test","Status","Notes","Photo"])
        st.dataframe(df.drop(columns=["Photo"]).sort_values(by="Time", ascending=False))
    except: st.info("No records found.")

# --- 4. ADDED: ADMIN TOOL (Removal/Management) ---
with tab3:
    st.subheader("🛠️ Quality Admin Management")
    admin_pwd = st.text_input("Enter Admin Override Key", type="password")
    
    if admin_pwd == "BG2026": # Master Admin Password
        try:
            df_admin = pd.read_csv("bg_quality_records.csv", names=["Time","Inspector","Job","Test","Status","Notes","Photo"])
            st.write("### Delete Incorrect Entries")
            selected_row = st.selectbox("Select Record to REMOVE", range(len(df_admin)), 
                                      format_func=lambda x: f"{df_admin.iloc[x]['Time']} - {df_admin.iloc[x]['Job']}")
            
            if st.button("🗑️ Permanently Delete Record"):
                new_df = df_admin.drop(df_admin.index[selected_row])
                new_df.to_csv("bg_quality_records.csv", index=False, header=False)
                st.warning("Record Deleted. Refreshing...")
                st.rerun()
        except: st.error("No data available to manage.")
