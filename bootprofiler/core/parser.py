import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")

# Units emitted by systemd's format_timespan(), in seconds.
_TIMESPAN_UNITS = {
    "y": 31557600.0,
    "month": 2629800.0,
    "w": 604800.0,
    "d": 86400.0,
    "h": 3600.0,
    "min": 60.0,
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "µs": 1e-6,
}
_TIMESPAN_TOKEN = re.compile(r"(\d+(?:\.\d+)?)(y|month|w|d|h|min|ms|us|µs|s)")


def parse_timespan(text):
    """Convert a systemd timespan such as '1min 2.345s' or '812ms' to seconds.

    Returns None if the text is not a timespan.
    """
    tokens = text.split()
    if not tokens:
        return None
    total = 0.0
    for token in tokens:
        m = _TIMESPAN_TOKEN.fullmatch(token)
        if not m:
            return None
        total += float(m.group(1)) * _TIMESPAN_UNITS[m.group(2)]
    return total


def parse_data(raw):
    parsed = {
        "firmware": 0.0,
        "loader": 0.0,
        "kernel": {"start": 0.0, "end": 0.0},
        "initrd": 0.0,
        "userspace": 0.0,
        "total": 0.0,
        "kernel_delays": [],
        "services": [],
    }

    is_systemd = bool(raw.get("time") or raw.get("blame"))

    # Monotonic `[ 0.000000]` lines come from plain `dmesg` or may appear in boot.log.
    log_for_kernel = raw.get("dmesg") or raw.get("boot_log")
    if log_for_kernel:
        parsed["kernel"] = estimate_kernel_time(log_for_kernel)
        parsed["kernel_delays"] = extract_kernel_delays(log_for_kernel)

    if is_systemd:
        timing = parse_systemd_time(raw["time"]) if raw.get("time") else None
        if timing:
            parsed.update(timing)
        parsed["services"] = parse_systemd_blame(raw.get("blame", ""))
        if raw.get("unit_starts") and raw.get("boot_finish"):
            parsed["services"] = drop_post_boot_units(
                parsed["services"], raw["unit_starts"], raw["boot_finish"]
            )
        if parsed["total"] == 0 and parsed["kernel"]["end"] > 0:
            parsed["total"] = parsed["kernel"]["end"]
    else:
        parsed["total"] = parsed["kernel"]["end"]

    return parsed

def parse_systemd_time(text):
    """Parse the `Startup finished in ...` line of `systemd-analyze time`.

    Phases are optional: VMs and BIOS boots omit firmware/loader, and
    initrd-based boots add an initrd phase. Returns None if no line matches.
    """
    text = _ANSI_ESCAPE.sub("", text)
    m = re.search(r"Startup finished in (.+?)\s*=\s*(.+?)\s*$", text, re.MULTILINE)
    if not m:
        return None
    total = parse_timespan(m.group(2))
    if total is None:
        return None

    phases = {}
    for part in m.group(1).split("+"):
        pm = re.fullmatch(r"\s*(.+?)\s+\((\w+)\)\s*", part)
        if pm:
            seconds = parse_timespan(pm.group(1))
            if seconds is not None:
                phases[pm.group(2)] = seconds

    return {
        "firmware": phases.get("firmware", 0.0),
        "loader": phases.get("loader", 0.0),
        "kernel": {"start": 0.0, "end": phases.get("kernel", 0.0)},
        "initrd": phases.get("initrd", 0.0),
        "userspace": phases.get("userspace", 0.0),
        "total": total,
    }

def parse_systemd_blame(text):
    services = []
    for line in text.splitlines():
        line = _ANSI_ESCAPE.sub("", line).strip()
        if not line:
            continue
        # The timespan may have several words ("1min 2.345s"); the unit name follows it.
        parts = line.split()
        for i in range(len(parts) - 1, 0, -1):
            duration = parse_timespan(" ".join(parts[:i]))
            if duration is not None:
                services.append({"name": " ".join(parts[i:]), "duration": duration})
                break
    services.sort(key=lambda x: x["duration"], reverse=True)
    return services

_DMESG_LINE = re.compile(r"\[\s*(\d+\.\d+)\]\s*(.*)")
# The kernel hands over to userspace (initramfs or rootfs init) here.
_INIT_HANDOFF = re.compile(r"Run \S+ as init process")


def _kernel_boot_lines(dmesg_text):
    """Yield (timestamp, message) for dmesg lines up to the init handoff.

    Without a handoff marker every timestamped line is yielded.
    """
    for line in dmesg_text.splitlines():
        m = _DMESG_LINE.match(line)
        if not m:
            continue
        t, msg = float(m.group(1)), m.group(2)
        yield t, msg
        if _INIT_HANDOFF.search(msg):
            return


def drop_post_boot_units(services, unit_starts, boot_finish):
    """Remove units that started after boot finished.

    `unit_starts` is `systemctl show -p Id -p InactiveExitTimestampMonotonic` output
    and `boot_finish` the manager's FinishTimestampMonotonic, both in microseconds.
    Units without a start time are kept.
    """
    try:
        finish = int(boot_finish.strip())
    except ValueError:
        return services
    if finish <= 0:  # boot not finished yet
        return services

    starts = {}
    unit = None
    for line in unit_starts.splitlines():
        key, _, value = line.partition("=")
        if key == "Id":
            unit = value
        elif key == "InactiveExitTimestampMonotonic" and unit and value.isdigit():
            starts[unit] = int(value)
    return [s for s in services if starts.get(s["name"], 0) <= finish]


def estimate_kernel_time(dmesg_text):
    last_ts = 0.0
    for t, _ in _kernel_boot_lines(dmesg_text):
        last_ts = t
    return {"start": 0.0, "end": last_ts}

def extract_kernel_delays(dmesg_text, top_n=5):
    delays = []
    prev_time, prev_msg = None, None
    for t, msg in _kernel_boot_lines(dmesg_text):
        if prev_time is not None:
            delta = t - prev_time
            delays.append({"delta": delta, "from": prev_msg, "to": msg, "start": prev_time, "end": t})
        prev_time, prev_msg = t, msg
    delays.sort(key=lambda x: x["delta"], reverse=True)
    return delays[:top_n]
