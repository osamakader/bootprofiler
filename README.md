# BootProfiler

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Cross-init **Linux Boot Profiler** for Embedded and Desktop systems.  
Analyze boot performance using logs or live data, across **systemd**, **SysVinit**, **BusyBox**, and more.

---

## ✨ Features
- **Cross-init support**: Works on systemd and non-systemd (embedded) systems.
- **Kernel driver delay analysis** from `dmesg`.
- **Top slow services** using `systemd-analyze blame`.
- **Offline analysis** from logs (`--dmesg`, `--systemd-blame`, `--systemd-time`).
- **Interactive HTML report** with boot timeline (Firmware → Loader → Kernel → Userspace).
- **Portable**: No systemd dependency for non-systemd targets.

---

## 🚀 Installation
```bash
git clone https://github.com/osamakader/bootprofiler.git
cd bootprofiler
pip install --editable .
