from flask import Flask, request, jsonify
from functools import wraps

app = Flask(__name__)
last_command = ""
last_result = ""  # store most recent Pico output

API_KEY = "supersecretkey"  # store safely, not in code

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
@require_key
def get_command():
    return jsonify({"command": last_command})

@app.route("/setcmd", methods=["POST"])
@require_key
def set_command():
    global last_command
    data = request.json
    last_command = data.get("command", "")
    print(f"[Ducky Command] {last_command}")
    return jsonify({"status": "ok"})

@app.route("/postresult", methods=["POST"])
@require_key
def post_result():
    global last_result
    data = request.json
    result = data.get("result", "")
    print(f"[Pico Result] {result}")
    last_result = result  # save for frontend
    return jsonify({"status": "ok"})

@app.route("/getresults", methods=["GET"])
@require_key
def get_results():
    global last_result
    r = last_result
    last_result = ""  # clear after read
    return jsonify({"result": r})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
