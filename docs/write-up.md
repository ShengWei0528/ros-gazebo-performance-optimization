# Method and findings

*Condensed English write-up of the weekly progress reports and summary reports of the capstone project (Yuan Ze University, 2025). Traditional Chinese version: [write-up.zh-TW.md](write-up.zh-TW.md).*

## 1. Problem

ROS + Gazebo is a common platform for developing and testing robot software, but it needs a lot of compute and graphics resources. On limited hardware (here: Windows + WSL2) the simulation often cannot run in real time: the **real-time factor (RTF)** drops below 1.0 and CPU and memory usage stay high, which slows down every experiment.

**Goal:** find where the CPU time goes in a TurtleBot3 Gazebo simulation and remove the bottlenecks one layer at a time (graphics → sensors → ROS communication → operating-system scheduling) until the simulation runs at RTF ≥ 1.0 with spare CPU left over.

## 2. Setup

| Item | Value (as recorded in the reports) |
|---|---|
| Host | Windows 10 + WSL2, Ubuntu 20.04 LTS, 4 logical CPUs |
| Middleware | ROS 1 Noetic |
| Simulator | Gazebo 11 |
| Robot | TurtleBot3 Waffle Pi (weeks 1–2); TurtleBot3 Burger with LDS-01 LiDAR at 2.5 Hz (weeks 4–6); camera and 9-axis IMU added in week 5 |
| World | `turtlebot3_world` (weeks 1–2); a simple indoor room with obstacles (week 6) |
| Metrics | RTF (`gz stats`), CPU and memory (`htop`/`top`), topic rate and latency (`rostopic hz`) |

CPU percentages follow the `htop` convention: 100 % = one core fully busy, so a 4-core machine can show up to 400 %.

## 3. Stage by stage

### Week 1: baseline and bottleneck analysis

- Launched `turtlebot3_world` with the Waffle Pi model and the Gazebo GUI.
- Per-process view in `htop`: `gzserver` (physics + sensor simulation) took about 50 % CPU and `gzclient` (rendering) about 35 %, while the ROS processes (`rosout`, `roslaunch`) together stayed below 25 %. **Conclusion: the ROS communication layer is not the bottleneck; physics and rendering are.**
- Plan for week 2: disable shadows, remove extra light sources, try running without the GUI.

> The week-1 report's own first reading was RTF 1.00, about 110 % CPU and about 1.07 GB of memory. The later summary reports use RTF 0.40, about 150 % CPU and 1.5 GB as the "before optimization" baseline for the default GUI setup. Both are kept here as recorded; no raw logs exist to reconcile them.

### Week 2: rendering settings and headless mode

1. Copied the stock world file and edited the copy (see [`configs/optimized_world_snippet.sdf`](../configs/optimized_world_snippet.sdf) and the screenshot `figures/week2_optimized_world_file.png`):
   - `<scene>`: `shadows=false`, `grid=false`, `origin_visual=false`
   - `sun` light: `cast_shadows=false`
   - duplicated scene settings removed
2. Ran the optimized world with the GUI, then headless (`gui:=false`, so only `gzserver` runs).

| Configuration | RTF | CPU | Memory |
|---|---|---|---|
| Default GUI (week-1 baseline) | 0.40 | ≈150 % | 1.5 GB |
| Optimized world, GUI on | 1.00 | ≈94 % (gzserver 48 % + gzclient 46 %) | 1.02 GB |
| Optimized world, headless | 1.00 | ≈46 % | 387 MB |

Going headless removed about 48 percentage points of CPU (−51 % relative to the optimized GUI run) and about 630 MB of memory, with RTF unchanged at 1.00. **Recommendation from the report:** use `gui:=false` for every run that does not need a human watching (navigation tests, reinforcement-learning training, multi-robot runs).

### Week 3: sensor parameters

LiDAR and camera resolution and update rate were lowered with a batch script. The six-week summary records a further CPU reduction of about 33 %. No separate report or table exists for this week.

### Week 4: LiDAR subscriber as a Nodelet

A Nodelet runs several nodes as plugins inside one process (a *nodelet manager*), so messages are passed by pointer instead of being serialized and copied between processes.

Steps: new Nodelet package with a Nodelet class and a functionally equivalent plain node → plugin description file → registration in `CMakeLists.txt` / `package.xml` → `catkin_make` → launch file that starts a nodelet manager and loads the LiDAR Nodelet. Both versions were checked to print the same minimum distance from `/scan` before measuring.

| Mode | RTF | CPU | `/scan` latency |
|---|---|---|---|
| Standalone node | 1.00 | 42 % | 3.2 ms |
| Nodelet | 1.02 | 38 % | 1.5 ms |

Latency roughly halved (−53 %) because the inter-process copy disappeared.

### Week 5: all sensor pipelines as Nodelets

LiDAR, camera and IMU-filter nodes were all converted and loaded into the same nodelet manager.

| Metric | LiDAR-only Nodelet | All sensors as Nodelets | Change |
|---|---|---|---|
| RTF | 1.02 | 1.00 | −0.02 |
| CPU | 38 % | 30 % | −8 points |
| Memory | 1.30 GB | 1.20 GB | −0.10 GB |
| `/scan` latency | 1.5 ms | 1.2 ms | −20 % |
| `/camera` latency | 5.5 ms | 2.8 ms | −49 % |
| `/imu` latency | 1.8 ms | 1.0 ms | −44 % |

Camera and IMU latency dropped by close to half, which the report credits to zero-copy message passing. RTF dipped slightly because more nodes now share the load, but it stayed at real time.

### Week 6: operating-system scheduling under load

To make scheduling effects visible, the headless simulation (TurtleBot3 Burger driving and scanning in a room) ran next to an extra **CPU-heavy ROS node doing continuous matrix multiplication with OpenBLAS**, standing in for SLAM or RL workloads. Five strategies were compared:

1. **Default**: Linux CFS scheduling, no pinning.
2. **Real-time priority**: `chrt -f -p 99 <gzserver_PID>` (SCHED_FIFO), so the physics loop is not pre-empted.
3. **CPU affinity**: `taskset` pins `gzserver` to CPU0, the stress node to CPU1–2 and the other ROS nodes to CPU3.
4. **Priority + affinity** together.
5. **Priority + affinity + `OPENBLAS_NUM_THREADS=1`**, which stops OpenBLAS from spawning one worker thread per core.

| Strategy | RTF | Total CPU | Est. `/scan` latency | Memory |
|---|---|---|---|---|
| Default (CFS) | 0.68 | 380 % | 8.5 ms | 500 MB |
| Real-time priority only | 0.85 | 370 % | 5.0 ms | 500 MB |
| CPU affinity only | 0.88 | 355 % | 4.1 ms | 498 MB |
| Priority + affinity | 0.95 | 360 % | 3.2 ms | 498 MB |
| + single-threaded OpenBLAS | **1.03** | **180 %** | **2.5 ms** | 480 MB |

The week-6 report gives these values without raw logs or measurement screenshots. They are reproduced as stated and have not been re-verified.

Observations from the report:

- Priority and affinity each help, and together they add up (0.68 → 0.95). Priority keeps `gzserver` from being pre-empted; affinity gives it a core it does not share with the heavy job. By RTF, these two steps account for most of the gain.
- Limiting OpenBLAS to one thread gave the largest CPU reduction and was the step that pushed RTF above 1.0 (0.95 → 1.03). On an already saturated machine, the extra BLAS threads mostly added contention and synchronization overhead. Removing them halved total CPU (≈360 % → 180 %). The report notes the stress job's results were unaffected.
- `/scan` was published below its nominal 2.5 Hz (about 1.7 Hz) in the default case and returned to 2.5 Hz after tuning.
- Memory barely changes (480–500 MB), so the gain comes from scheduling, not from trading memory for speed.
- Caveat: SCHED_FIFO at priority 99 needs root and can starve other processes if misused. The report considered the risk acceptable for a single-simulation WSL2 setup.

## 4. Overall progression (ROS 1)

| Stage | RTF | CPU | Memory | Main measures |
|---|---|---|---|---|
| Before optimization | 0.40 | ≈150 % | 1.50 GB | none |
| Graphics | 1.00 | ≈46 % | 387 MB | no shadows / extra lights, headless |
| Nodelet | 1.02 | ≈38 % | ≈380 MB | LiDAR Nodelet |
| Scheduling | 1.02 | ≈38 % | ≈380 MB | CPU affinity, real-time priority |

This table is Table 1 of the first summary report (May 2025). Relative to its starting point: RTF 0.40 → 1.02 (+155 %), CPU ≈150 % → ≈38 % (−75 %), memory 1.5 GB → ≈380 MB (−75 %), LiDAR latency 3.2 ms → 1.5 ms (−53 %). The rendering stage gave the largest jump; Nodelets and scheduling mainly improved latency and stability.

> **The reports disagree on two points.** (1) Starting point: the week-1 report measured RTF 1.00, ≈110 % CPU and ≈1.07 GB for the default GUI setup, whereas this table (and the week-2 cross-week table) uses 0.40 / ≈150 % / 1.5 GB. (2) Memory after Nodelets: this table gives ≈380 MB for the Nodelet and scheduling stages, but the week-5 report gives 1.30 GB → 1.20 GB for the same phase, and the six-week summary gives 1.2 GB as the end state. No raw logs exist to reconcile them, so the memory figures in particular should be read with care.

## 5. Candidate techniques surveyed

The May 2025 report also surveyed other optimizations. They are listed here as a checklist; **they were not measured individually in this project**:

- *ROS layer:* Nodelets / composition, `TCP_NODELAY` on subscribers, fewer relay nodes, topic rate and message-size control, timestamp synchronization.
- *Gazebo layer:* simpler collision geometry and models, `max_step_size` / `real_time_update_rate` tuning, disabling unused sensors, headless mode, non-blocking plugin callbacks, fewer links/joints, GPU sensors (`gpu_ray`), CPU pinning, disabling skybox / fog / shadows, simpler worlds.

## 6. Limitations and next steps (from the reports)

- Physics is still the main load: the Gazebo physics engine keeps about 50 % of one core busy. Options are a lower update rate or moving to Ignition Gazebo.
- Only one robot was tested. Three TurtleBots in parallel were planned next.
- Camera and image-processing pipelines need more work.
- Next scheduling experiments: `isolcpus`, cgroups and a real-time kernel.
- All tuning steps should become scripts so the setup can be reproduced in one command.
- Measurement quality: the numbers are single readings from `htop` / `gz stats`, conditions changed between weeks, and some reports disagree with each other (see §4). Repeated runs with logged raw data would make the comparisons statistically sound.
