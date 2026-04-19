import click
import os
from bootprofiler.core.detector import detect_init
from bootprofiler.core.collector import collect_data
from bootprofiler.core.parser import parse_data
from bootprofiler.core.visualizer import print_cli_report, save_html_report

@click.command()
@click.option("--dmesg", type=click.Path(exists=True), help="Path to dmesg log file")
@click.option("--bootlog", type=click.Path(exists=True), help="Path to /var/log/boot.log file")
@click.option("--bootchart", type=click.Path(exists=True), help="Path to bootchart.tgz file")
@click.option("--systemd-time", type=click.Path(exists=True), help="systemd-analyze time output")
@click.option("--systemd-blame", type=click.Path(exists=True), help="systemd-analyze blame output")
@click.option("--output", "-o", default=None, help="Save HTML report to file")
@click.option("--top", default=10, help="Number of top services to display")
def analyze(dmesg, bootlog, bootchart, systemd_time, systemd_blame, output, top):
    """Analyze system boot or logs from files."""
    if any([dmesg, bootlog, bootchart, systemd_time, systemd_blame]):
        raw_data = {
            "dmesg": read_file(dmesg),
            "boot_log": read_file(bootlog),
            "bootchart": bootchart,
            "time": read_file(systemd_time),
            "blame": read_file(systemd_blame),
        }
    else:
        init_type = detect_init()
        click.echo(f"[INFO] Detected init system: {init_type}")
        raw_data = collect_data(init_type)
        if raw_data.get("error"):
            click.echo(f"[ERROR] {raw_data['error']}", err=True)
        elif raw_data.get("warning"):
            click.echo(f"[WARN] {raw_data['warning']}")

    parsed = parse_data(raw_data)
    print_cli_report(parsed, top)

    if output:
        save_html_report(parsed, output, top)
        click.echo(f"[INFO] HTML report saved to {output}")

def read_file(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    return None

if __name__ == "__main__":
    analyze()
