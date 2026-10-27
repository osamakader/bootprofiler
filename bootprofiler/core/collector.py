import json
import subprocess
import os

# Plain `dmesg` emits `[    0.000000]` monotonic timestamps, which matches our parser.
# `dmesg -T` uses human-readable dates and breaks estimate_kernel_time / extract_kernel_delays.


def collect_data(init_type):
    if init_type == "systemd":
        return collect_systemd_data()
    return collect_non_systemd_data()


def _journal_kernel_log():
    """Rebuild dmesg-style lines from the journal's kernel messages for this boot."""
    out = subprocess.check_output(
        ["journalctl", "-k", "-b", "-o", "json", "--no-pager"],
        text=True,
        stderr=subprocess.DEVNULL,
        timeout=60,
    )
    lines = []
    for entry in out.splitlines():
        try:
            rec = json.loads(entry)
            usec = int(rec["_SOURCE_MONOTONIC_TIMESTAMP"])
        except (ValueError, KeyError):
            continue
        msg = rec.get("MESSAGE", "")
        if isinstance(msg, list):  # journald stores non-UTF-8 messages as byte arrays
            msg = bytes(msg).decode("utf-8", errors="replace")
        lines.append(f"[{usec / 1e6:12.6f}] {msg}")
    return "\n".join(lines) + "\n" if lines else None


def _capture_dmesg(errors):
    """Return kernel log text with monotonic `[ sec ]` timestamps, or None.

    Plain `dmesg` fails for non-root users when kernel.dmesg_restrict=1, so fall
    back to the journal. Failures are appended to `errors`.
    """
    try:
        return subprocess.check_output(
            ["dmesg"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass
    try:
        log = _journal_kernel_log()
        if log:
            return log
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        pass
    errors.append("kernel log unavailable (dmesg needs root when kernel.dmesg_restrict=1)")
    return None


def collect_systemd_data():
    data = {}
    errors = []

    try:
        subprocess.check_output(
            ["systemd-analyze", "--version"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
    except FileNotFoundError:
        data["dmesg"] = _capture_dmesg(errors)
        data["error"] = "; ".join(["systemd-analyze not available"] + errors)
        return data
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
        errors.append(f"systemd-analyze: {e}")

    def _run(cmd):
        try:
            return subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL, timeout=120)
        except subprocess.CalledProcessError as e:
            errors.append(f"{' '.join(cmd)} failed (exit {e.returncode})")
        except (OSError, subprocess.TimeoutExpired) as e:
            errors.append(str(e))
        return None

    t = _run(["systemd-analyze", "time"])
    if t:
        data["time"] = t
    b = _run(["systemd-analyze", "blame"])
    if b:
        data["blame"] = b
    data["dmesg"] = _capture_dmesg(errors)

    if errors and not data.get("time") and not data.get("blame"):
        data["error"] = "; ".join(errors)
    elif errors:
        data["warning"] = "; ".join(errors)
    return data


def collect_non_systemd_data():
    data = {}
    errors = []
    if os.path.exists("/var/log/boot.log"):
        with open("/var/log/boot.log", encoding="utf-8", errors="replace") as f:
            data["boot_log"] = f.read()
    data["dmesg"] = _capture_dmesg(errors)
    if errors:
        data["warning"] = "; ".join(errors)
    return data
