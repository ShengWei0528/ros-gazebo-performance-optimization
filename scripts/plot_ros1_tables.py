#!/usr/bin/env python3
"""Redraw the ROS 1 (Noetic) progress-report tables as bar charts.

The CSV files in ``data/ros1_*.csv`` are transcriptions of the summary tables
in the weekly progress reports (single observations read from ``gz stats``,
``htop`` and ``rostopic hz``; no per-trial raw logs exist), so the charts have
no error bars.

Usage::

    python scripts/plot_ros1_tables.py [--data data] [--out figures] [--format auto|svg|png]
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from charts import Figure, Panel, render

REPO = Path(__file__).resolve().parent.parent


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def col(rows: List[Dict[str, str]], name: str) -> List[float]:
    return [float(r[name]) for r in rows]


def labels(rows: List[Dict[str, str]]) -> List[str]:
    return [r["short_label"] for r in rows]


def stage_figure(rows: List[Dict[str, str]]) -> Figure:
    lab = labels(rows)
    return Figure(
        title="ROS 1 + Gazebo 11: effect of each optimization stage",
        panels=[
            Panel("Real-time factor", "RTF (1.0 = real time)", lab, col(rows, "rtf"),
                  value_fmt="{:.2f}", ref_line=1.0, ref_label="real time"),
            Panel("CPU usage", "CPU (% of one core)", lab, col(rows, "cpu_percent"), value_fmt="{:.0f}"),
            Panel("Memory", "Memory (GB)", lab, col(rows, "memory_gb"), value_fmt="{:.2f}"),
        ],
        note="Values from Table 1 of the first summary report (single observations). "
             "Other reports give different baseline and memory values; see data/README.md.",
    )


def graphics_figure(rows: List[Dict[str, str]]) -> Figure:
    lab = [s.replace(" ", "|", 1) for s in labels(rows)]
    return Figure(
        title="Week 2: Gazebo rendering settings",
        panels=[
            Panel("Real-time factor", "RTF (1.0 = real time)", lab, col(rows, "rtf"),
                  value_fmt="{:.2f}", ref_line=1.0, ref_label="real time"),
            Panel("CPU usage", "CPU (% of one core)", lab, col(rows, "cpu_percent"), value_fmt="{:.0f}"),
            Panel("Memory", "Memory (GB)", lab, col(rows, "memory_gb"), value_fmt="{:.2f}"),
        ],
        note="Values transcribed from the week-2 progress report (htop / gz stats readings).",
    )


def nodelet_figure(rows: List[Dict[str, str]]) -> Figure:
    week5 = [r for r in rows if r["report_week"] == "5"]
    lab = labels(week5)
    return Figure(
        title="Week 5: converting every sensor pipeline to Nodelets",
        panels=[
            Panel("CPU usage", "CPU (% of one core)", lab, col(week5, "cpu_percent"), value_fmt="{:.0f}"),
            Panel("/scan latency", "Latency (ms)", lab, col(week5, "scan_latency_ms"), value_fmt="{:.1f}"),
            Panel("/camera latency", "Latency (ms)", lab, col(week5, "camera_latency_ms"), value_fmt="{:.1f}"),
            Panel("/imu latency", "Latency (ms)", lab, col(week5, "imu_latency_ms"), value_fmt="{:.1f}"),
        ],
        note="Values transcribed from the week-5 progress report (htop, gz stats, rostopic hz).",
    )


def scheduling_figure(rows: List[Dict[str, str]]) -> Figure:
    lab = labels(rows)
    return Figure(
        title="Week 6: OS-level scheduling under a CPU-heavy background load",
        panels=[
            Panel("Real-time factor", "RTF (1.0 = real time)", lab, col(rows, "rtf"),
                  value_fmt="{:.2f}", ref_line=1.0, ref_label="real time"),
            Panel("Total CPU usage", "CPU (% summed over cores)", lab, col(rows, "cpu_percent"),
                  value_fmt="{:.0f}"),
            Panel("Sensor-data latency", "Estimated /scan latency (ms)", lab,
                  col(rows, "gazebo_latency_ms"), value_fmt="{:.1f}"),
        ],
        note="Values as stated in the week-6 report (no raw logs; not re-verified). "
             "A matrix-multiplication stress node ran in the background.",
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=REPO / "data")
    ap.add_argument("--out", type=Path, default=REPO / "figures")
    ap.add_argument("--format", choices=("auto", "svg", "png"), default="auto",
                    help="auto = PNG via matplotlib if installed, else SVG")
    args = ap.parse_args()

    jobs = [
        ("ros1_stage_summary.csv", stage_figure, "ros1_stage_progression"),
        ("ros1_graphics_week2.csv", graphics_figure, "ros1_week2_gui_vs_headless"),
        ("ros1_nodelet_results.csv", nodelet_figure, "ros1_week5_nodelet_latency"),
        ("ros1_scheduling_results.csv", scheduling_figure, "ros1_week6_scheduling"),
    ]
    for csv_name, builder, stem in jobs:
        fig = builder(read_rows(args.data / csv_name))
        for path in render(fig, args.out / stem, args.format):
            print(f"wrote {path.relative_to(REPO) if path.is_relative_to(REPO) else path}")


if __name__ == "__main__":
    main()
