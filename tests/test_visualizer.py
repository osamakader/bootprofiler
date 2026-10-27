import pytest

from bootprofiler.core import visualizer
from bootprofiler.core.parser import parse_data

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
