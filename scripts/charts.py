"""Small bar-chart helpers used by ``plot_ros1_tables.py``.

Every figure is a row of panels; each panel is one metric drawn as a bar chart
(optionally with +/- error bars and a dashed reference line such as RTF = 1.0).

* ``render_svg`` uses only the Python standard library, so the script always
  runs - even on a machine without matplotlib.
* ``render_png`` uses matplotlib with the non-interactive Agg backend
  (no seaborn) and is used when matplotlib is installed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from html import escape
from pathlib import Path
from typing import List, Optional, Sequence

# Light chart surface, inks and two bar colours (neutral = reference/baseline).
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
BLUE = "#2a78d6"
NEUTRAL = "#a8a69e"
FONT = "system-ui, -apple-system, 'Segoe UI', 'DejaVu Sans', Arial, sans-serif"


@dataclass
class Panel:
    """One metric panel. Labels may contain '|' to force a line break."""

    title: str
    ylabel: str
    labels: Sequence[str]
    values: Sequence[float]
    errors: Optional[Sequence[float]] = None
    colors: Optional[Sequence[str]] = None
    value_fmt: str = "{:.2f}"
    ref_line: Optional[float] = None
    ref_label: str = ""
    ymax: Optional[float] = None
    tooltips: Optional[Sequence[str]] = None

    def bar_colors(self) -> List[str]:
        if self.colors:
            return list(self.colors)
        return [NEUTRAL] + [BLUE] * (len(self.values) - 1)


@dataclass
class Figure:
    title: str
    panels: List[Panel] = field(default_factory=list)
    note: str = ""


# ----------------------------------------------------------------- axis maths
def _nice_step(span: float, target_ticks: int = 5) -> float:
    raw = span / target_ticks
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag + 1e-12:
            return m * mag
    return 10 * mag


def _axis_top(panel: Panel) -> tuple[float, float]:
    errs = panel.errors or [0.0] * len(panel.values)
    peak = max(v + e for v, e in zip(panel.values, errs))
    if panel.ref_line is not None:
        peak = max(peak, panel.ref_line)
    top = panel.ymax if panel.ymax is not None else peak * 1.18
    step = _nice_step(top)
    top = math.ceil(top / step - 1e-9) * step
    return top, step


def _tick_text(value: float, step: float) -> str:
    """Format a tick with exactly as many decimals as the tick step needs."""
    step_text = f"{step:.4f}".rstrip("0").rstrip(".")
    decimals = len(step_text.split(".")[1]) if "." in step_text else 0
    return f"{value:.{decimals}f}"


# ------------------------------------------------------------------- SVG path
def render_svg(fig: Figure, path: Path) -> Path:
    """Write ``fig`` as a standalone SVG file (no third-party packages)."""
    max_bars = max(len(p.values) for p in fig.panels)
    pw, ph = max(300, 76 + 66 * max_bars), 330   # panel size (wider for many bars)
    ml, mr, mt, mb = 62, 14, 40, 78              # plot margins inside a panel
    head = 48
    foot = 30 if fig.note else 8
    width = pw * len(fig.panels) + 20
    height = head + ph + foot
    out: List[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT}">',
        f"<title>{escape(fig.title)}</title>",
        f'<rect width="{width}" height="{height}" fill="{SURFACE}"/>',
        f'<text x="{width / 2:.1f}" y="30" text-anchor="middle" font-size="17" '
        f'font-weight="600" fill="{INK}">{escape(fig.title)}</text>',
    ]
    for i, panel in enumerate(fig.panels):
        ox, oy = 10 + i * pw, head
        x0, x1 = ox + ml, ox + pw - mr
        y0, y1 = oy + ph - mb, oy + mt          # y0 = baseline, y1 = top of plot
        top, step = _axis_top(panel)

        def ys(v: float) -> float:
            return y0 - (v / top) * (y0 - y1)

        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{oy + 18}" text-anchor="middle" '
                   f'font-size="14" font-weight="600" fill="{INK}">{escape(panel.title)}</text>')
        # grid + y ticks
        n_ticks = int(round(top / step))
        for k in range(n_ticks + 1):
            v = k * step
            y = ys(v)
            colour = AXIS if k == 0 else GRID
            out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" '
                       f'stroke="{colour}" stroke-width="1"/>')
            out.append(f'<text x="{x0 - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="11" '
                       f'fill="{MUTED}">{_tick_text(v, step)}</text>')
        cy = (y0 + y1) / 2
        out.append(f'<text x="{ox + 16}" y="{cy:.1f}" text-anchor="middle" font-size="12" '
                   f'fill="{INK_2}" transform="rotate(-90 {ox + 16} {cy:.1f})">'
                   f"{escape(panel.ylabel)}</text>")
        # reference line
        if panel.ref_line is not None:
            yr = ys(panel.ref_line)
            out.append(f'<line x1="{x0}" y1="{yr:.1f}" x2="{x1}" y2="{yr:.1f}" stroke="{MUTED}" '
                       f'stroke-width="1.5" stroke-dasharray="5 4"/>')
            if panel.ref_label:
                out.append(f'<text x="{x1 - 2}" y="{yr - 5:.1f}" text-anchor="end" font-size="10" '
                           f'fill="{MUTED}">{escape(panel.ref_label)}</text>')
        # bars
        n = len(panel.values)
        slot = (x1 - x0) / n
        bw = min(56.0, slot * 0.62)
        colours = panel.bar_colors()
        errs = panel.errors or [0.0] * n
        for j, (lab, v, e) in enumerate(zip(panel.labels, panel.values, errs)):
            cx = x0 + slot * (j + 0.5)
            bx, yt = cx - bw / 2, ys(v)
            r = min(4.0, bw / 2, max(0.0, y0 - yt))
            d = (f"M{bx:.1f},{y0:.1f} L{bx:.1f},{yt + r:.1f} Q{bx:.1f},{yt:.1f} {bx + r:.1f},{yt:.1f} "
                 f"L{bx + bw - r:.1f},{yt:.1f} Q{bx + bw:.1f},{yt:.1f} {bx + bw:.1f},{yt + r:.1f} "
                 f"L{bx + bw:.1f},{y0:.1f} Z")
            tip = panel.tooltips[j] if panel.tooltips else f"{lab.replace('|', ' ')}: {panel.value_fmt.format(v)}"
            out.append(f'<path d="{d}" fill="{colours[j]}"><title>{escape(tip)}</title></path>')
            label_y = yt
            if e:
                ya, yb = ys(v + e), ys(max(0.0, v - e))
                out.append(f'<line x1="{cx:.1f}" y1="{ya:.1f}" x2="{cx:.1f}" y2="{yb:.1f}" '
                           f'stroke="{INK_2}" stroke-width="1.5"/>')
                for yy in (ya, yb):
                    out.append(f'<line x1="{cx - 5:.1f}" y1="{yy:.1f}" x2="{cx + 5:.1f}" y2="{yy:.1f}" '
                               f'stroke="{INK_2}" stroke-width="1.5"/>')
                label_y = ya
            out.append(f'<text x="{cx:.1f}" y="{label_y - 6:.1f}" text-anchor="middle" font-size="12" '
                       f'fill="{INK}">{escape(panel.value_fmt.format(v))}</text>')
            # x label (multi-line)
            lines = lab.split("|")
            text = "".join(f'<tspan x="{cx:.1f}" dy="{0 if k == 0 else 13}">{escape(t)}</tspan>'
                           for k, t in enumerate(lines))
            out.append(f'<text x="{cx:.1f}" y="{y0 + 17:.1f}" text-anchor="middle" font-size="11" '
                       f'fill="{INK_2}">{text}</text>')
    if fig.note:
        out.append(f'<text x="{width / 2:.1f}" y="{height - 12}" text-anchor="middle" font-size="11" '
                   f'fill="{MUTED}">{escape(fig.note)}</text>')
    out.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


# ------------------------------------------------------------- matplotlib path
def matplotlib_available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def render_png(fig: Figure, path: Path) -> Path:
    """Write ``fig`` as a PNG with matplotlib (Agg backend, no seaborn)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(fig.panels)
    max_bars = max(len(p.values) for p in fig.panels)
    panel_w = max(3.4, 0.95 * max_bars)          # inches; wider panels for many bars
    mfig, axes = plt.subplots(1, n, figsize=(panel_w * n, 4.0), dpi=150, squeeze=False)
    mfig.patch.set_facecolor(SURFACE)
    for ax, panel in zip(axes[0], fig.panels):
        ax.set_facecolor(SURFACE)
        xs = list(range(len(panel.values)))
        errs = panel.errors if panel.errors else None
        ax.bar(xs, panel.values, width=0.6, color=panel.bar_colors(), zorder=2)
        if errs:
            ax.errorbar(xs, panel.values, yerr=errs, fmt="none", ecolor=INK_2,
                        elinewidth=1.5, capsize=4, zorder=3)
        top, _ = _axis_top(panel)
        ax.set_ylim(0, top)
        if panel.ref_line is not None:
            ax.axhline(panel.ref_line, color=MUTED, linestyle="--", linewidth=1.2, zorder=1)
        for x, v, e in zip(xs, panel.values, errs or [0.0] * len(xs)):
            ax.text(x, v + e + top * 0.015, panel.value_fmt.format(v), ha="center",
                    va="bottom", fontsize=9, color=INK)
        ax.set_xticks(xs)
        ax.set_xticklabels([lab.replace("|", "\n") for lab in panel.labels], fontsize=8, color=INK_2)
        ax.set_title(panel.title, fontsize=11, color=INK, fontweight="bold")
        ax.set_ylabel(panel.ylabel, fontsize=9, color=INK_2)
        ax.tick_params(axis="y", labelsize=8, colors=MUTED)
        ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(AXIS)
    mfig.suptitle(fig.title, fontsize=13, color=INK, fontweight="bold")
    if fig.note:
        mfig.text(0.5, 0.01, fig.note, ha="center", fontsize=8, color=MUTED)
    mfig.tight_layout(rect=(0, 0.04 if fig.note else 0, 1, 0.94))
    path.parent.mkdir(parents=True, exist_ok=True)
    mfig.savefig(path, facecolor=SURFACE)
    plt.close(mfig)
    return path


def render(fig: Figure, stem: Path, fmt: str = "auto") -> List[Path]:
    """Render ``fig`` next to ``stem`` and return the written paths.

    fmt = "png"  -> PNG with matplotlib (error if matplotlib is missing)
    fmt = "svg"  -> SVG with the standard library only
    fmt = "auto" -> PNG when matplotlib is installed, otherwise SVG
    """
    if fmt == "auto":
        fmt = "png" if matplotlib_available() else "svg"
    if fmt == "png":
        if not matplotlib_available():
            raise SystemExit("matplotlib is not installed; use --format svg or pip install matplotlib")
        return [render_png(fig, stem.with_suffix(".png"))]
    return [render_svg(fig, stem.with_suffix(".svg"))]
