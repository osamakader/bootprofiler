import subprocess
import os

# Plain `dmesg` emits `[    0.000000]` monotonic timestamps, which matches our parser.
# `dmesg -T` uses human-readable dates and breaks estimate_kernel_time / extract_kernel_delays.


def collect_data(init_type):
    if init_type == "systemd":
        return collect_systemd_data()
    return collect_non_systemd_data()


def _capture_dmesg():
    """Return dmesg text with monotonic `[ sec ]` timestamps, or None."""
    for cmd in (["dmesg"], ["dmesg", "-k"]):
        try:
            return subprocess.check_output(
                cmd,
                text=True,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, OSError):
            continue
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
        data["error"] = "systemd-analyze not available"
        data["dmesg"] = _capture_dmesg()
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

    if errors and not data.get("time") and not data.get("blame"):
        data["error"] = "; ".join(errors)
    elif errors:
        data["warning"] = "; ".join(errors)

    data["dmesg"] = _capture_dmesg()
    return data


def collect_non_systemd_data():
    data = {}
    if os.path.exists("/var/log/boot.log"):
        with open("/var/log/boot.log", encoding="utf-8", errors="replace") as f:
            data["boot_log"] = f.read()
    data["dmesg"] = _capture_dmesg()
    return data
