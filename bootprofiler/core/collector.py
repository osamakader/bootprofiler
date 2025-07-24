import subprocess
import os

def collect_data(init_type):
    if init_type == "systemd":
        return collect_systemd_data()
    else:
        return collect_non_systemd_data()

def collect_systemd_data():
    data = {}
    try:
        data["time"] = subprocess.check_output(["systemd-analyze", "time"], text=True)
        data["blame"] = subprocess.check_output(["systemd-analyze", "blame"], text=True)
    except FileNotFoundError:
        data["error"] = "systemd-analyze not available"
    return data

def collect_non_systemd_data():
    data = {}
    if os.path.exists("/var/log/boot.log"):
        with open("/var/log/boot.log") as f:
            data["boot_log"] = f.read()
    # Collect dmesg with timestamps
    try:
        data["dmesg"] = subprocess.check_output(["dmesg", "-T"], text=True)
    except Exception:
        data["dmesg"] = None
    return data
