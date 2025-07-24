from rich.console import Console
import os

console = Console()

def print_cli_report(parsed,top):
    console.print("[bold green]BOOT PROFILER REPORT[/bold green]")
    console.print(f"Total boot time: {parsed['total']:.3f}s")
    if parsed.get("firmware"): console.print(f"  - Firmware:  {parsed['firmware']:.3f}s")
    if parsed.get("loader"): console.print(f"  - Loader:    {parsed['loader']:.3f}s")
    console.print(f"  - Kernel:    {parsed['kernel']['end']:.3f}s")
    if parsed["userspace"]: console.print(f"  - Userspace: {parsed['userspace']:.3f}s")

    if parsed["kernel_delays"]:
        console.print("\n[cyan]Top Kernel Delays:[/cyan]")
        for i, d in enumerate(parsed["kernel_delays"], 1):
            console.print(f"{i}) [{d['start']:.3f}s → {d['end']:.3f}s] {d['from']} → {d['to']} ({d['delta']:.2f}s)")

    if parsed["services"]:
        console.print("\n[yellow]Top Services:[/yellow]")
        for i, s in enumerate(parsed["services"][:top], 1):
            console.print(f"{i}) {s['name']}: {s['duration']:.2f}s")

def save_html_report(parsed, filename, top=10):
    total = parsed['total']
    html = "<html><head><title>Boot Profiler Report</title></head><body>"
    html += "<h1>Boot Profiler Report</h1>"
    html += f"<p>Total Boot Time: {total:.2f}s</p>"

    # Main boot phases timeline
    html += "<div style='display:flex; width:100%; font-size:14px; height:30px; align-items:center;'>"
    if parsed['firmware'] > 0:
        html += f"<div title='Firmware: {parsed['firmware']:.3f}s' style='flex:{parsed['firmware']}; background:#4fa3d1; height:100%;'></div>"
    if parsed['loader'] > 0:
        html += f"<div title='Loader: {parsed['loader']:.3f}s' style='flex:{parsed['loader']}; background:#38b2ac; height:100%;'></div>"
    html += f"<div title='Kernel: {parsed['kernel']['end']:.3f}s' style='flex:{parsed['kernel']['end']}; background:#48bb78; height:100%;'></div>"

    # Userspace with nested service bars
    if parsed['userspace'] > 0:
        html += "<div style='flex:{}; background:#9f7aea; height:100%; display:flex; flex-direction:column;'>".format(parsed['userspace'])
        html += "<div style='font-size:12px; color:#fff; padding-left:4px;'>Userspace</div>"
        html += "<div style='display:flex; flex-grow:1; height:18px;'>"

        # Sum of top services durations to scale sub-bars proportionally
        services = parsed.get("services", [])[:top]
        total_services_time = sum(s["duration"] for s in services) or 1.0  # avoid div by zero

        # Colors for services (some shades of purple)
        colors = ["#d4bfff", "#c0aaff", "#b399ff", "#a380ff", "#8e68ff", "#7b4dff", "#682eff", "#5614ff", "#4200ff", "#2f00e5"]

        for i, s in enumerate(services):
            width_ratio = s["duration"] / total_services_time
            flex_val = width_ratio * parsed['userspace']
            color = colors[i % len(colors)]
            html += f"<div title='{s['name']}: {s['duration']:.3f}s' style='flex:{flex_val}; background:{color};'></div>"

        html += "</div></div>"
    html += "</div><hr>"

    # List top services under timeline
    if parsed["services"]:
        html += "<h2>Top Services</h2><ul>"
        for s in parsed["services"][:top]:
            html += f"<li>{s['name']}: {s['duration']:.3f}s</li>"
        html += "</ul>"

    # List kernel delays
    if parsed["kernel_delays"]:
        html += "<h2>Top Kernel Delays</h2><ul>"
        for d in parsed["kernel_delays"]:
            html += f"<li>{d['from']} → {d['to']}: {d['delta']:.3f}s</li>"
        html += "</ul>"

    html += "</body></html>"

    with open(filename, "w") as f:
        f.write(html)

