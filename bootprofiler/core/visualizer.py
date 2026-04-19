from html import escape

from rich import box
from rich.bar import Bar
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_cli_report(parsed, top, style="simple"):
    """Print boot report to the terminal."""
    if (style or "simple").lower() == "pretty":
        print_cli_report_pretty(parsed, top)
    else:
        print_cli_report_simple(parsed, top)


def print_cli_report_simple(parsed, top):
    console.print("[bold green]BOOT PROFILER REPORT[/bold green]")
    console.print(f"Total boot time: {parsed['total']:.3f}s")
    if parsed.get("firmware"):
        console.print(f"  - Firmware:  {parsed['firmware']:.3f}s")
    if parsed.get("loader"):
        console.print(f"  - Loader:    {parsed['loader']:.3f}s")
    console.print(f"  - Kernel:    {parsed['kernel']['end']:.3f}s")
    if parsed["userspace"]:
        console.print(f"  - Userspace: {parsed['userspace']:.3f}s")

    if parsed["kernel_delays"]:
        console.print("\n[cyan]Top Kernel Delays:[/cyan]")
        for i, d in enumerate(parsed["kernel_delays"], 1):
            console.print(
                f"{i}) [{d['start']:.3f}s → {d['end']:.3f}s] "
                f"{d['from']} → {d['to']} ({d['delta']:.2f}s)"
            )

    if parsed["services"]:
        console.print("\n[yellow]Top Services:[/yellow]")
        for i, s in enumerate(parsed["services"][:top], 1):
            console.print(f"{i}) {s['name']}: {s['duration']:.2f}s")


def _phase_segments(parsed):
    """Return list of (label, seconds, style) for boot phases."""
    segs = []
    fw = float(parsed.get("firmware") or 0)
    ld = float(parsed.get("loader") or 0)
    kr = float(parsed["kernel"]["end"] or 0)
    us = float(parsed.get("userspace") or 0)
    if fw > 0:
        segs.append(("Firmware", fw, "bold cyan"))
    if ld > 0:
        segs.append(("Loader", ld, "bold turquoise2"))
    if kr > 0:
        segs.append(("Kernel", kr, "bold green"))
    if us > 0:
        segs.append(("Userspace", us, "bold magenta"))
    return segs


def _boot_phase_bar(parsed, max_width=72):
    """Horizontal stacked bar of phase durations (Unicode blocks)."""
    segs = _phase_segments(parsed)
    total_time = float(parsed.get("total") or 0)
    if not segs or total_time <= 0:
        return Group(
            Text("No phase breakdown available for chart.", style="dim"),
            Text(f"Reported total: {total_time:.3f}s", style="dim"),
        )

    # Leave margin for panel borders/padding so the bar stays on one line.
    bar_chars = max(12, min(max_width, max(20, console.size.width - 24)))
    fracs = [sec / total_time for _, sec, _ in segs]
    raw = [f * bar_chars for f in fracs]
    counts = [int(x) for x in raw]
    remainder = bar_chars - sum(counts)
    if remainder > 0:
        order = sorted(
            range(len(segs)),
            key=lambda i: raw[i] - counts[i],
            reverse=True,
        )
        for k in range(remainder):
            counts[order[k % len(order)]] += 1

    line = Text()
    for (_, _, style), n in zip(segs, counts):
        if n > 0:
            line.append("█" * n, style=style)

    caption = Text(f"Total span: {total_time:.3f}s (sum of phases above)", style="dim")
    return Group(line, caption)


def print_cli_report_pretty(parsed, top):
    """Rich layout: panels, tables, and a phase bar."""
    total = float(parsed.get("total") or 0)
    kernel_end = float(parsed["kernel"]["end"] or 0)

    title = Text()
    title.append("BootProfiler", style="bold white on dark_green")
    title.append("  ")
    title.append("Boot summary", style="bold default")

    phase_table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="bold bright_white",
        title="Phase timing",
        expand=True,
    )
    phase_table.add_column("Phase", style="bold", no_wrap=True)
    phase_table.add_column("Duration", justify="right", style="green")
    phase_table.add_column("Share", justify="right", style="dim")

    rows = []
    if parsed.get("firmware"):
        rows.append(("Firmware", parsed["firmware"]))
    if parsed.get("loader"):
        rows.append(("Loader", parsed["loader"]))
    rows.append(("Kernel", kernel_end))
    if parsed.get("userspace"):
        rows.append(("Userspace", parsed["userspace"]))

    denom = total if total > 0 else 1.0
    for name, sec in rows:
        pct = 100.0 * sec / denom if denom else 0.0
        phase_table.add_row(name, f"{sec:.3f}s", f"{pct:.1f}%")

    phase_table.add_row(
        Text("Total", style="bold"),
        Text(f"{total:.3f}s", style="bold green"),
        Text("100.0%" if total > 0 else "—", style="bold dim"),
        end_section=True,
    )

    bar_block = _boot_phase_bar(parsed)
    legend_items = []
    for label, sec, style in _phase_segments(parsed):
        legend_items.append(Text(f"■ {label}", style=style))
    legend = Columns(legend_items, equal=False, column_first=False) if legend_items else Text("")

    overview = Group(
        phase_table,
        Text(),
        Panel(
            Group(bar_block, Text(), legend),
            title="Timeline",
            border_style="bright_blue",
            padding=(0, 1),
        ),
    )

    console.print()
    console.print(Panel(overview, title=title, border_style="green", padding=(1, 2)))
    console.print()

    if parsed["kernel_delays"]:
        delay_table = Table(
            box=box.ROUNDED,
            title="Kernel gaps (largest Δ between dmesg lines)",
            title_style="bold cyan",
            show_lines=False,
        )
        delay_table.add_column("#", justify="right", style="dim", width=3)
        delay_table.add_column("Δ time", justify="right", style="yellow")
        delay_table.add_column("Window", style="dim", max_width=22)
        delay_table.add_column("From → To", style="white")

        for i, d in enumerate(parsed["kernel_delays"], 1):
            window = f"{d['start']:.3f}s–{d['end']:.3f}s"
            span = f"{d['from'][:42]} → {d['to'][:42]}"
            if len(d["from"]) > 42 or len(d["to"]) > 42:
                span += "…"
            delay_table.add_row(
                str(i),
                f"{d['delta']:.3f}s",
                window,
                span,
            )
        console.print(delay_table)
        console.print()

    if parsed["services"]:
        svc_table = Table(
            box=box.ROUNDED,
            title=f"Top services (showing {min(top, len(parsed['services']))})",
            title_style="bold yellow",
            show_header=True,
            header_style="bold",
        )
        svc_table.add_column("Rank", justify="right", style="dim", width=5)
        svc_table.add_column("Unit", style="white", ratio=1)
        svc_table.add_column("Time", justify="right", style="green")
        svc_table.add_column("", width=18)

        max_d = max(s["duration"] for s in parsed["services"][:top]) or 1.0
        for i, s in enumerate(parsed["services"][:top], 1):
            bar = Bar(
                12,
                0.0,
                s["duration"] / max_d,
                width=12,
                color="yellow",
                bgcolor="grey23",
            )
            svc_table.add_row(
                str(i),
                s["name"],
                f"{s['duration']:.3f}s",
                bar,
            )
        console.print(svc_table)

    console.print()

def save_html_report(parsed, filename, top=10):
    total = parsed['total']
    html = "<html><head><title>Boot Profiler Report</title></head><body>"
    html += "<h1>Boot Profiler Report</h1>"
    html += f"<p>Total Boot Time: {total:.2f}s</p>"

    # Main boot phases timeline
    html += "<div style='display:flex; width:100%; font-size:14px; height:30px; align-items:center;'>"
    if parsed['firmware'] > 0:
        fw = parsed['firmware']
        html += f"<div title='Firmware: {fw:.3f}s' style='flex:{fw}; background:#4fa3d1; height:100%;'></div>"
    if parsed['loader'] > 0:
        ld = parsed['loader']
        html += f"<div title='Loader: {ld:.3f}s' style='flex:{ld}; background:#38b2ac; height:100%;'></div>"
    k = parsed['kernel']['end']
    html += f"<div title='Kernel: {k:.3f}s' style='flex:{k}; background:#48bb78; height:100%;'></div>"

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
            safe_title = escape(f"{s['name']}: {s['duration']:.3f}s", quote=True)
            html += (
                f"<div title=\"{safe_title}\" "
                f"style='flex:{flex_val}; background:{color};'></div>"
            )

        html += "</div></div>"
    html += "</div><hr>"

    # List top services under timeline
    if parsed["services"]:
        html += "<h2>Top Services</h2><ul>"
        for s in parsed["services"][:top]:
            html += f"<li>{escape(s['name'])}: {s['duration']:.3f}s</li>"
        html += "</ul>"

    # List kernel delays
    if parsed["kernel_delays"]:
        html += "<h2>Top Kernel Delays</h2><ul>"
        for d in parsed["kernel_delays"]:
            html += (
                f"<li>{escape(d['from'])} → {escape(d['to'])}: {d['delta']:.3f}s</li>"
            )
        html += "</ul>"

    html += "</body></html>"

    with open(filename, "w") as f:
        f.write(html)

