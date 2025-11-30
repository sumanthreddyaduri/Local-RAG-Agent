from flask import Flask, render_template, request, redirect, url_for
import os
import json
from backend import ingest_files

app = Flask(__name__)
CONFIG_FILE = "config.json"
UPLOAD_DIR = "./uploaded_files"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Initialize Config
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f: json.dump({"model": "gemma3:270m"}, f)

def get_config():
    with open(CONFIG_FILE, "r") as f: return json.load(f)

@app.route("/")
def index():
    config = get_config()
    message = request.args.get("message")
    status = request.args.get("status")
    return render_template("index.html", config=config, message=message, status=status)

@app.route("/set_model", methods=["POST"])
def set_model():
    model = request.form.get("model")
    with open(CONFIG_FILE, "w") as f: json.dump({"model": model}, f)
    
    msg = f"Switched to {model}"
    if "gemma" in model.lower():
        msg = "Switched to Gemma"
    elif "qwen" in model.lower():
        msg = "Switched to Qwen"
        
    return redirect(url_for("index", message=msg, status="success"))

@app.route("/upload", methods=["POST"])
def upload():
    if "files" not in request.files:
        return redirect(url_for("index", message="No file part", status="error"))
    
    files = request.files.getlist("files")
    paths = []
    for file in files:
        if file.filename == "": continue
        path = os.path.join(UPLOAD_DIR, file.filename)
        file.save(path)
        paths.append(path)
    
    if paths:
        success, msg = ingest_files(paths)
        status = "success" if success else "error"
        return redirect(url_for("index", message=msg, status=status))
    
    return redirect(url_for("index", message="No files selected", status="error"))

if __name__ == "__main__":
    # Remove llama3 from options in template if hardcoded, but here we just pass config.
    # The template has hardcoded options. I should update the template too if I want to be clean.
    app.run(port=8501, debug=True)
