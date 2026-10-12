# Data

| File | Phase | What it contains | Raw per-trial data? |
|---|---|---|---|
| `ros1_stage_summary.csv` | ROS 1, weeks 1–6 | Stage-by-stage summary table (before optimization → graphics → Nodelet → scheduling) from Table 1 of the first summary report (May 2025). The `source` column says where each row comes from and which other report disagrees with it. | No: one reading per stage |
| `ros1_graphics_week2.csv` | ROS 1, week 2 | Default GUI vs optimized GUI vs headless (`gui:=false`). | No: one reading per configuration |
| `ros1_nodelet_results.csv` | ROS 1, weeks 4–5 | Standalone node vs Nodelet (week 4); LiDAR-only Nodelet vs all sensors as Nodelets (week 5), including topic latencies. | No: one reading per configuration |
| `ros1_scheduling_results.csv` | ROS 1, week 6 | Five scheduling strategies under a CPU-heavy background node: RTF, total CPU, estimated `/scan` latency, memory. Values as stated in the week-6 report (not re-verified). | No: one reading per strategy |

## Column notes

- **RTF**: real-time factor reported by Gazebo (`gz stats`); 1.0 means simulated time advances as fast as wall-clock time.
- **CPU (%)**: `htop`/`top` style, where 100 % = one fully loaded core. Weeks 1–5 report the Gazebo/ROS processes; week 6 reports the total over all cores, including the background stress node.
- **Memory**: as read from `htop`. MB values from the reports are converted to GB (e.g. 387 MB → 0.387 GB); `ros1_scheduling_results.csv` keeps MB (`memory_mb`).
- **Latency (ms)**: message latency estimated in the reports from `rostopic hz` timing and simulated-vs-wall-clock time. These are estimates, not end-to-end traces.
- `stage_week` (stage summary) is the week in which that optimization stage was worked on; it does not mean the numbers appear in that week's report. `report_week` (Nodelet file) is the report the row was transcribed from.
- `short_label` columns are only used as chart axis labels (`|` = line break).

## Caveats

- The tables are single observations transcribed from the weekly progress reports. No raw logs were kept, so there are no error bars and no significance tests for them.
- The reports do not agree on every number:
  - **Starting point.** The week-1 report's own reading of the default GUI setup was RTF 1.00, ≈110 % CPU and ≈1066 MB. The week-2 report's cross-week table and the summary reports use RTF 0.40, ≈150 % CPU and 1.5 GB for the same "before optimization" setup.
  - **Memory after Nodelets.** The summary table gives ≈380 MB for the Nodelet and scheduling stages. The week-5 report gives 1.30 GB → 1.20 GB for the same phase, and the six-week summary gives 1.2 GB as the end state.
  - All values are kept as each report states them; there are no logs to reconcile them.
- The week-6 values come from a single report that has no raw logs or measurement screenshots. They are reproduced as stated and have not been re-verified.
- Test conditions changed between weeks (robot model `waffle_pi` in weeks 1–2, `burger` with an LDS-01 LiDAR in weeks 4–6; extra sensors in week 5; an artificial CPU load in week 6). Compare rows within one table, not across tables.
