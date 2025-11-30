import streamlit as st
import os
import json
from backend import ingest_files

CONFIG_FILE = "config.json"
UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Config
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f: json.dump({"model": "gemma3:270m"}, f)

st.set_page_config(page_title="AI Control Room", layout="centered")
st.header("🎛️ Agent Control Panel")

# 1. Model Selector
with open(CONFIG_FILE, "r") as f: config = json.load(f)
model_options = ["gemma3:270m", "qwen2.5:0.5b", "llama3"]
current_index = model_options.index(config["model"]) if config["model"] in model_options else 0

selected_model = st.selectbox("Active Brain (Model)", model_options, index=current_index)

if selected_model != config["model"]:
    with open(CONFIG_FILE, "w") as f: json.dump({"model": selected_model}, f)
    st.toast(f"Switched to {selected_model}", icon="🧠")

st.divider()

# 2. File Ingestion
st.subheader("📂 Ingest Knowledge")
files = st.file_uploader("Drop PDFs, Excels, PPTs here", accept_multiple_files=True)

if st.button("Process Files") and files:
    paths = []
    progress = st.progress(0)
    for i, f in enumerate(files):
        path = os.path.join(UPLOAD_DIR, f.name)
        with open(path, "wb") as wb: wb.write(f.getbuffer())
        paths.append(path)
        progress.progress((i + 1) / len(files))
    
    with st.spinner("Reading & Indexing..."):
        success, msg = ingest_files(paths)
        if success: st.success(msg)
        else: st.error(msg)
