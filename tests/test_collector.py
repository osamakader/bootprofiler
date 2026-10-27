import json
import subprocess

from bootprofiler.core import collector


def _fake_check_output(responses):
    def fake(cmd, **kwargs):
        result = responses[cmd[0]]
        if isinstance(result, Exception):
            raise result
        return result
    return fake


def test_restricted_dmesg_falls_back_to_journal(monkeypatch):
    journal = "\n".join(json.dumps(r) for r in [
        {"_SOURCE_MONOTONIC_TIMESTAMP": "0", "MESSAGE": "Linux version 6.8.0"},
        {"_SOURCE_MONOTONIC_TIMESTAMP": "1400085", "MESSAGE": list(b"Run /init as init process")},
        {"MESSAGE": "no timestamp"},
    ])
    monkeypatch.setattr(subprocess, "check_output", _fake_check_output({
        "dmesg": subprocess.CalledProcessError(1, "dmesg"),
        "journalctl": journal,
    }))
    errors = []
    log = collector._capture_dmesg(errors)
    assert log == (
        "[    0.000000] Linux version 6.8.0\n"
        "[    1.400085] Run /init as init process\n"
    )
    assert errors == []


def test_unavailable_kernel_log_is_reported(monkeypatch):
    monkeypatch.setattr(subprocess, "check_output", _fake_check_output({
        "dmesg": subprocess.CalledProcessError(1, "dmesg"),
        "journalctl": FileNotFoundError(),
    }))
    monkeypatch.setattr(collector.os.path, "exists", lambda path: False)
    data = collector.collect_non_systemd_data()
    assert data["dmesg"] is None
    assert "kernel log unavailable" in data["warning"]
