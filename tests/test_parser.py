import pytest

from bootprofiler.core.parser import (
    estimate_kernel_time,
    extract_kernel_delays,
    parse_data,
    parse_systemd_blame,
    parse_systemd_time,
    parse_timespan,
)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("4.268s", 4.268),
        ("812ms", 0.812),
        ("512us", 0.000512),
        ("1min 5.678s", 65.678),
        ("1h 2min 3s", 3723.0),
    ],
)
def test_parse_timespan(text, expected):
    assert parse_timespan(text) == pytest.approx(expected)


@pytest.mark.parametrize("text", ["", "abc", "5 s", "1min foo"])
def test_parse_timespan_rejects_garbage(text):
    assert parse_timespan(text) is None


def test_systemd_time_all_phases():
    t = parse_systemd_time(
        "Startup finished in 7.673s (firmware) + 16.101s (loader) + 4.021s (kernel) "
        "+ 4.071s (userspace) = 31.867s \ngraphical.target reached after 3.684s in userspace.\n"
    )
    assert t["firmware"] == 7.673
    assert t["loader"] == 16.101
    assert t["kernel"]["end"] == 4.021
    assert t["userspace"] == 4.071
    assert t["total"] == 31.867


def test_systemd_time_without_firmware_and_loader():
    t = parse_systemd_time("Startup finished in 812ms (kernel) + 3.456s (userspace) = 4.268s\n")
    assert t["firmware"] == 0.0
    assert t["kernel"]["end"] == pytest.approx(0.812)
    assert t["userspace"] == 3.456
    assert t["total"] == 4.268


def test_systemd_time_with_initrd_and_minutes():
    t = parse_systemd_time(
        "Startup finished in 1.234s (kernel) + 2.1s (initrd) + 1min 5.678s (userspace) = 1min 9.012s\n"
    )
    assert t["initrd"] == 2.1
    assert t["userspace"] == pytest.approx(65.678)
    assert t["total"] == pytest.approx(69.012)


def test_systemd_time_unparseable_keeps_dmesg_kernel_time():
    parsed = parse_data({
        "time": "Bootup is not yet finished.\n",
        "dmesg": "[    0.000000] Linux version\n[    1.500000] Run /sbin/init as init process\n",
    })
    assert parsed["kernel"]["end"] == 1.5
    assert parsed["total"] == 1.5


def test_systemd_blame_units():
    services = parse_systemd_blame(
        "1min 2.345s apt-daily.service\n"
        "     5.432s NetworkManager-wait-online.service\n"
        "      123ms foo.service\n"
        "\x1b[1m      512us bar.service\x1b[0m\n"
        "\n"
    )
    assert [s["name"] for s in services] == [
        "apt-daily.service",
        "NetworkManager-wait-online.service",
        "foo.service",
        "bar.service",
    ]
    assert services[0]["duration"] == pytest.approx(62.345)
    assert services[3]["duration"] == pytest.approx(0.000512)


DMESG_LIVE = (
    "[    0.000000] Linux version 6.8.0\n"
    "[    1.500000] [drm] Initialized i915\n"
    "[    2.000000] Run /init as init process\n"
    "[ 3600.000000] usb 1-1: new high-speed USB device\n"
)


def test_kernel_time_stops_at_init_handoff():
    assert estimate_kernel_time(DMESG_LIVE) == {"start": 0.0, "end": 2.0}


def test_kernel_delays_ignore_post_boot_messages():
    delays = extract_kernel_delays(DMESG_LIVE)
    assert [d["delta"] for d in delays] == [1.5, 0.5]
    assert delays[0]["to"] == "[drm] Initialized i915"


def test_kernel_time_without_handoff_uses_last_line():
    assert estimate_kernel_time("[    0.1] a\n[    0.7] b\n")["end"] == 0.7
