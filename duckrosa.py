# aMiscreant
import os
from functools import wraps

from flask import Flask, request, jsonify
from flask import send_from_directory

app = Flask(__name__)
last_command = "" # store last command sent
last_result = ""  # store most recent Pico output

UPLOAD_DIR = "firmware/"

API_KEY = "supersecretkey"  # store safely, not in code ToDo

def require_key(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.headers.get("X-API-KEY") != API_KEY:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return open("index/duckrosa.html").read()

@app.route("/getcmd", methods=["GET"])
@require_key # require key
def get_command():
    return jsonify({"command": last_command})

@app.route("/setcmd", methods=["POST"])
@require_key # require key
def set_command():
    global last_command
    data = request.json
    last_command = data.get("command", "")
    print(f"[Ducky Command] {last_command}")
    return jsonify({"status": "ok"})

@app.route("/postresult", methods=["POST"])
@require_key # require key
def post_result():
    global last_result
    data = request.json
    result = data.get("result", "")
    print(f"[Pico Result] {result}")
    last_result = result  # save for frontend
    return jsonify({"status": "ok"})

@app.route("/getresults", methods=["GET"])
@require_key # require key
def get_results():
    global last_result
    r = last_result
    last_result = ""  # clear after read
    return jsonify({"result": r})

@app.route("/uploadbin", methods=["POST"])
@require_key # require key
def upload_bin():
    if "binfile" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["binfile"]
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(save_path)
    print(f"[UploadBin] Saved {save_path}")
    return jsonify({"status": "ok", "filename": f.filename})


@app.route("/firmware/<path:filename>", methods=["GET"])
@require_key  # keep it protected
def firmware_files(filename):
    """
    Serve files from the firmware directory.
    Example: /firmware/nuke.uf2
    """
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
