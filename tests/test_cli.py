import os
import subprocess
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from bootprofiler.cli import analyze

ROOT = Path(__file__).resolve().parent.parent


def test_top_must_be_positive(tmp_path):
    blame = tmp_path / "blame.txt"
    blame.write_text("1.000s foo.service\n")
    result = CliRunner().invoke(analyze, ["--systemd-blame", str(blame), "--top", "0", "--format", "pretty"])
    assert result.exit_code == 2
    assert "--top" in result.output


@pytest.mark.parametrize("style", ["simple", "pretty"])
def test_report_prints_under_c_locale(tmp_path, style):
    dmesg = tmp_path / "dmesg.txt"
    dmesg.write_text("[    0.000000] Linux version\n[    1.000000] Run /init as init process\n")
    env = dict(os.environ, LC_ALL="C", PYTHONUTF8="0", PYTHONIOENCODING="", PYTHONPATH=str(ROOT))
    result = subprocess.run(
        [sys.executable, "-m", "bootprofiler.cli", "--dmesg", str(dmesg), "--format", style],
        capture_output=True, env=env,
    )
    assert result.returncode == 0, result.stderr.decode()
    assert b"Run /init as init process" in result.stdout


def test_log_path_must_be_a_file(tmp_path):
    result = CliRunner().invoke(analyze, ["--dmesg", str(tmp_path)])
    assert result.exit_code == 2
    assert "is a directory" in result.output
