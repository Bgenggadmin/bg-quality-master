import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 1. DATA FILES ---
QUALITY_LOG = "bg_quality_records_v2.csv"

# --- 2. SECURITY ---
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

# --- 3. MAIN INTERFACE ---
st.title("✅ B&G Engineering: Quality Assurance")
tabs = st.tabs(["📋 Inspection Log", "📊 Quality Analytics"])

# --- TAB 1: INSPECTION LOG ---
with tabs[0]:
    st.subheader("New Quality Inspection Entry")
    
    supervisors = ["Prasanth", "RamaSai", "Subodth", "Naresh", "Ravindra"]
    
    # Updated with your specific fabrication checks
    inspection_types = [
        "Marking",
        "Fitup",
        "Nozzle Orientation",
        "PMI (Material ID)",
        "Runout",
        "Load Test",
        "Hydrotest", 
        "DP Test (Dye Penetrant)", 
        "FAT (Factory Acceptance Test)",
        "Surface Finish",
        "Final Dimensional Check"
    ]
    
    c1, c2 = st.columns(2)
    with c1:
        inspector = st.selectbox("Inspector Name", supervisors)
        job_code = st.text_input("Job Code (e.g., DIST-05)")
        unit = st.selectbox("Unit Location", ["A", "B", "C"])
    with c2:
        test_type = st.selectbox("Inspection Type", inspection_types)
        status = st.radio("Result Status", ["✅ PASSED", "❌ FAILED / REWORK", "⚠️ HOLD"])
    
    details = st.text_area("Observation / Technical Remarks (e.g., Deviation in mm)")

    if st.button("Submit Quality Report"):
        now = datetime.now()
        row = f"{now.strftime('%Y-%m-%d')},{now.strftime('%H:%M')},{inspector},{job_code},{unit},{test_type},{status},{details.replace(',', ';')}\n"
        with open(QUALITY_LOG, "a") as f: f.write(row)
        st.success(f"Quality Report for {job_code} Recorded!")

# --- TAB 2: QUALITY ANALYTICS ---
with tabs[1]:
    st.subheader("Quality Trends & Rework Analysis")
    if os.path.exists(QUALITY_LOG):
        df = pd.read_csv(QUALITY_LOG, names=["Date","Time","Inspector","Job","Unit","Test","Status","Remarks"])
        
        st.write("### 📈 Overall Inspection Status")
        st.bar_chart(df["Status"].value_counts())
        
        st.write("### 📍 Issues by Test Type")
        fails = df[df["Status"] == "❌ FAILED / REWORK"]
        if not fails.empty:
            st.bar_chart(fails.groupby("Test").size())
            
        with st.expander("🔍 Search Full History"):
            st.dataframe(df)
    else:
        st.info("No quality records found.")
