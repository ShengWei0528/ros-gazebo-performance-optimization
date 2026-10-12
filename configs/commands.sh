#!/usr/bin/env bash
# Commands used in the ROS 1 (Noetic) phase, collected from the weekly progress
# reports. This is a reference sheet, not a one-shot script: run the blocks you
# need in separate terminals. Anything in <angle brackets> is a placeholder.
# Where a report described a step in prose instead of giving the command, the
# command below is a reconstruction and is marked as such.
#
# Environment in the reports: Windows 10 + WSL2, Ubuntu 20.04, ROS Noetic,
# Gazebo 11, TurtleBot3 simulation packages.

# --- Week 1: baseline ---------------------------------------------------------
export TURTLEBOT3_MODEL=waffle_pi
roslaunch turtlebot3_gazebo turtlebot3_world.launch
# observe: htop (CPU / memory per process), Gazebo GUI real-time factor

# --- Week 2: rendering settings ----------------------------------------------
mkdir -p ~/turtlebot3_ws/worlds
cp /opt/ros/noetic/share/turtlebot3_gazebo/worlds/turtlebot3_world.world \
   ~/turtlebot3_ws/worlds/my_optimized_world.world
# edit the copy as shown in configs/optimized_world_snippet.sdf, then:

# (a) optimized world, GUI on (as recorded in the report)
roslaunch turtlebot3_gazebo turtlebot3_world.launch \
  world_file:=$HOME/turtlebot3_ws/worlds/my_optimized_world.world

# (b) optimized world, headless: gzclient is not started
roslaunch turtlebot3_gazebo turtlebot3_world.launch \
  world_file:=$HOME/turtlebot3_ws/worlds/my_optimized_world.world gui:=false

# real-time factor readout
gz stats -p -d 3

# --- Weeks 4-5: Nodelets --------------------------------------------------------
# standalone subscriber vs. the same logic loaded into a nodelet manager
rosrun turtlebot3_lidar_nodelet simple_lidar_node
# The week-4 report writes this as `roslaunch my_lidar_nodelet.launch`;
# <your_nodelet_pkg> is a placeholder for the package that holds the launch file.
roslaunch <your_nodelet_pkg> my_lidar_nodelet.launch
rostopic hz /scan          # publish rate / jitter

# --- Week 6: OS-level scheduling (under a CPU-heavy background node) -----------
# 1) real-time FIFO priority for the Gazebo server
sudo chrt -f -p 99 <gzserver_PID>
# 2) CPU affinity: gzserver on CPU0, the stress node on CPU1-2, other ROS nodes on CPU3
#    (taskset commands reconstructed from the core layout described in the
#    week-6 report; the report does not list the exact commands)
taskset -cp 0   <gzserver_PID>
taskset -cp 1,2 <stress_node_PID>
# 3) keep OpenBLAS single-threaded (set before launching the nodes)
export OPENBLAS_NUM_THREADS=1
