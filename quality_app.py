# --- 3. UI & FORM ---
st.title("🛡️ B&G Quality Control")

# 1. FIELD INPUTS
job_code = st.text_input("Job Code (e.g. 2KL ANFD_1361)")
col1, col2 = st.columns(2)
with col1:
    activity = st.selectbox("Inspection Activity", ["Material Inward", "Marking", "Cutting", "Fit-up", "Welding", "DP Test", "Hydro Test", "Final Painting"])
    heat_no = st.text_input("Heat Number / Batch No")
with col2:
    supervisor = st.selectbox("QC Inspector", ["Prasanth", "Sunil", "Ravindra", "Naresh", "RamaSai", "Subodth"])
    result = st.radio("Result", ["✅ Pass", "❌ Fail", "⚠️ Rework"], horizontal=True)

notes = st.text_area("Inspection Notes", placeholder="Mention any defects or observations here...")

# 2. PHOTO SECTION (Moved outside for stability)
st.write("📸 **Inspection Proof**")
use_camera = st.toggle("Turn on Camera") # Toggle is better than checkbox for hardware
uploaded_file = None

if use_camera:
    uploaded_file = st.camera_input("Snap a photo")
else:
    uploaded_file = st.file_uploader("Upload from Gallery", type=['jpg', 'jpeg', 'png'])

# 3. SUBMIT BUTTON
if st.button("🚀 Submit Inspection Report", use_container_width=True):
    if not job_code:
        st.error("Please enter a Job Code before submitting.")
    else:
        photo_url = "No Photo"
        if uploaded_file:
            photo_url = save_photo_to_github(uploaded_file, job_code)
        
        new_row = {
            "Timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
            "Job_Code": job_code,
            "Activity": activity,
            "Heat_Number": heat_no,
            "Inspection_Result": result,
            "Supervisor": supervisor,
            "Notes": notes,
            "Photo_URL": photo_url
        }
        
        # Save and Sync
        if os.path.exists(LOGS_FILE):
            df = pd.read_csv(LOGS_FILE)
        else:
            df = pd.DataFrame(columns=HEADERS)
            
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv(LOGS_FILE, index=False)
        sync_to_github(LOGS_FILE, f"QC Entry: {job_code} - {activity}")
        
        st.balloons()
        st.success(f"✅ {activity} for {job_code} Recorded successfully!")
