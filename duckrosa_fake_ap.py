#!/usr/bin/env python3
"""
DuckRosa HostAP + Flask C2
--------------------------
- Spins up a WPA2 AP (no Internet required)
- Runs a safe Flask fake-terminal server
- Devices (e.g., Pico W) can connect and poll payloads
"""

import subprocess
import tempfile
import os
import signal
import atexit
import time
from functools import wraps

from flask import Flask, request, jsonify

# -----------------------------
# Flask server setup
# -----------------------------
app = Flask(__name__)

last_command = "" # store last command sent
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

# -----------------------------
# HostAPD setup
# -----------------------------
HOSTAPD_CONF = """
interface={iface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel=6
wpa=2
wpa_passphrase={password}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
"""

DNSMASQ_CONF = """
interface={iface}
dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,24h
"""

def terminate_proc(proc):
    try:
        proc.send_signal(signal.SIGINT)
        proc.terminate()
    except Exception:
        pass

def start_hostapd(iface="wlo1", ssid="DuckRosaAP", password="SecretPass123"):
    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".conf")
    tmp.write(HOSTAPD_CONF.format(iface=iface, ssid=ssid, password=password))
    tmp.close()
    print(f"[+] Launching hostapd AP '{ssid}' on {iface}...")
    proc = subprocess.Popen(["sudo", "hostapd", tmp.name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    atexit.register(lambda: terminate_proc(proc))
    return proc

def start_dnsmasq(iface="wlo1"):
    tmp = tempfile.NamedTemporaryFile(delete=False, mode="w", suffix=".conf")
    tmp.write(DNSMASQ_CONF.format(iface=iface))
    tmp.close()
    print(f"[+] Launching dnsmasq DHCP server on {iface}...")
    proc = subprocess.Popen(["sudo", "dnsmasq", "-C", tmp.name, "-d"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    atexit.register(lambda: terminate_proc(proc))
    return proc

def configure_ip(iface="wlo1"):
    # Bring interface down first
    subprocess.run(["sudo", "ip", "link", "set", iface, "down"])
    # Assign static IP
    subprocess.run(["sudo", "ip", "addr", "flush", "dev", iface])
    subprocess.run(["sudo", "ip", "addr", "add", "192.168.50.1/24", "dev", iface])
    # Bring interface up
    subprocess.run(["sudo", "ip", "link", "set", iface, "up"])

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    AP_IFACE = "wlo1"       # your AP-capable interface
    AP_SSID = "DuckRosaAP"
    AP_PASSWORD = "SecretPass123"

    print("[*] Configuring interface...")
    configure_ip(AP_IFACE)

    print("[*] Starting hostapd...")
    hostapd_proc = start_hostapd(iface=AP_IFACE, ssid=AP_SSID, password=AP_PASSWORD)

    # Wait a bit to ensure hostapd is up before starting DHCP
    time.sleep(2)

    print("[*] Starting dnsmasq DHCP server...")
    dnsmasq_proc = start_dnsmasq(iface=AP_IFACE)

    print("[+] Starting Flask C2 server on 192.168.50.1:5000...")
    try:
        app.run(host="0.0.0.0", port=5000)
    except KeyboardInterrupt:
        print("\n[!] Shutting down...")
        terminate_proc(hostapd_proc)
        terminate_proc(dnsmasq_proc)
        os._exit(0)