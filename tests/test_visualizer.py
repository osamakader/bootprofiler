import os
import subprocess
import sys
from pathlib import Path

import pytest

from bootprofiler.core import visualizer
from bootprofiler.core.parser import parse_data

ROOT = Path(__file__).resolve().parent.parent

RAW = {
    "dmesg": (
        "[    0.000000] Linux version 6.8.0\n"
        "[    1.500000] [drm] Initialized i915 [/bold]\n"
        "[    2.000000] Run /init as init process\n"
    ),
    "blame": "1.000s [weird]-unit.service\n",
}


@pytest.mark.parametrize("style", ["simple", "pretty"])
def test_log_text_is_not_rich_markup(style, capsys, monkeypatch):
    monkeypatch.setattr(visualizer, "console", visualizer.Console(width=200, no_color=True))
    visualizer.print_cli_report(parse_data(RAW), 10, style=style)
    out = capsys.readouterr().out
    assert "[drm] Initialized i915 [/bold]" in out
    assert "[weird]-unit.service" in out


def test_html_report_is_utf8_under_c_locale(tmp_path):
    out = tmp_path / "report.html"
    code = (
        "from bootprofiler.core.parser import parse_data;"
        "from bootprofiler.core.visualizer import save_html_report;"
        f"save_html_report(parse_data({RAW!r}), {str(out)!r})"
    )
    env = dict(os.environ, LC_ALL="C", PYTHONUTF8="0", PYTHONPATH=str(ROOT))
    subprocess.run([sys.executable, "-c", code], check=True, env=env)
    html = out.read_text(encoding="utf-8")
    assert "<meta charset='utf-8'>" in html
    assert "→" in html


def test_html_service_bars_scale_to_slowest_unit(tmp_path):
    parsed = parse_data({"blame": "2.000s slow.service\n0.500s fast.service\n"})
    out = tmp_path / "report.html"
    visualizer.save_html_report(parsed, str(out))
    html = out.read_text(encoding="utf-8")
    assert "width:100.0%" in html
    assert "width:25.0%" in html
