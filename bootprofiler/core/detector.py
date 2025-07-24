def detect_init():
    """Detect whether the system uses systemd or not"""
    try:
        with open("/proc/1/comm") as f:
            name = f.read().strip().lower()
        if "systemd" in name:
            return "systemd"
        return "non-systemd"
    except Exception:
        return "unknown"
