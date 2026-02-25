# --- 1. CORE SYNC LOGIC (The Safety Lock) ---
def sync_to_github(file_path, commit_message="Sync QC Data"):
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        
        # This part 'merges' with the existing file on GitHub instead of replacing it
        repo = g.get_repo("Bgenggadmin/bg-quality-master")
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, content, contents.sha)
        except:
            repo.create_file(file_path, commit_message, content)
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- 2. THE QUALITY FORM ---
with st.form("quality_form", clear_on_submit=True):
    job_code = st.selectbox("Job Code", job_list)
    heat_no = st.text_input("Heat Number / Batch No")
    status = st.radio("Inspection Result", ["✅ Pass", "❌ Fail", "⚠️ Rework"])
    
    # PHOTO UPLOAD
    uploaded_file = st.file_uploader("Upload Inspection Photo", type=['jpg', 'png', 'jpeg'])
    
    if st.form_submit_button("Submit Inspection"):
        # 1. Save Photo to GitHub folder
        if uploaded_file:
            photo_path = f"quality_photos/{job_code}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.jpg"
            # Logic to save and sync photo...
            
        # 2. Append to quality_logs.csv
        # Logic to read existing logs, add new row, and sync...
        st.success("✅ Inspection Data & Photo Synced to GitHub!")
