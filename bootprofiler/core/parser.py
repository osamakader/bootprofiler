import re

def parse_data(raw):
    parsed = {
        "firmware": 0.0,
        "loader": 0.0,
        "kernel": {"start": 0.0, "end": 0.0},
        "userspace": 0.0,
        "total": 0.0,
        "kernel_delays": [],
        "services": []
    }

    is_systemd = bool(raw.get("time") or raw.get("blame"))

    if raw.get("dmesg"):
        parsed["kernel"] = estimate_kernel_time(raw["dmesg"])
        parsed["kernel_delays"] = extract_kernel_delays(raw["dmesg"])

    if is_systemd:
        if raw.get("time"):
            parsed.update(parse_systemd_time(raw["time"]))
        parsed["services"] = parse_systemd_blame(raw.get("blame", ""))
        if parsed["total"] == 0 and parsed["kernel"]["end"] > 0:
            parsed["total"] = parsed["kernel"]["end"]
    else:
        parsed["total"] = parsed["kernel"]["end"]

    return parsed

def parse_systemd_time(text):
    result = {
        "firmware": 0.0,
        "loader": 0.0,
        "kernel": {"start": 0.0, "end": 0.0},
        "userspace": 0.0,
        "total": 0.0
    }
    m = re.search(
        r"([\d\.]+)s \(firmware\)\s+\+\s+([\d\.]+)s \(loader\)\s+\+\s+([\d\.]+)s \(kernel\)\s+\+\s+([\d\.]+)s \(userspace\)\s+=\s+([\d\.]+)s",
        text
    )
    if m:
        result["firmware"] = float(m.group(1))
        result["loader"] = float(m.group(2))
        result["kernel"]["end"] = float(m.group(3))
        result["userspace"] = float(m.group(4))
        result["total"] = float(m.group(5))
    return result

def parse_systemd_blame(text):
    services = []
    for line in text.splitlines():
        m = re.match(r"\s*(\d+\.\d+|\d+)(ms|s)\s+(.*)", line)
        if m:
            duration = float(m.group(1))
            if m.group(2) == "ms":
                duration /= 1000.0  # convert to seconds
            services.append({"name": m.group(3), "duration": duration})
    services.sort(key=lambda x: x["duration"], reverse=True)
    return services

def estimate_kernel_time(dmesg_text):
    last_ts = 0.0
    for line in dmesg_text.splitlines():
        m = re.match(r"\[\s*(\d+\.\d+)\]", line)
        if m:
            last_ts = float(m.group(1))
    return {"start": 0.0, "end": last_ts}

def extract_kernel_delays(dmesg_text, top_n=5):
    delays = []
    prev_time, prev_msg = None, None
    for line in dmesg_text.splitlines():
        m = re.match(r"\[\s*(\d+\.\d+)\]\s+(.*)", line)
        if m:
            t, msg = float(m.group(1)), m.group(2)
            if prev_time is not None:
                delta = t - prev_time
                delays.append({"delta": delta, "from": prev_msg, "to": msg, "start": prev_time, "end": t})
            prev_time, prev_msg = t, msg
    delays.sort(key=lambda x: x["delta"], reverse=True)
    return delays[:top_n]
