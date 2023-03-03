# CARET Analysis for Autoware

This page shows how to analyze [Autoware](https://github.com/autowarefoundation/autoware) with CARET

1. Get Autoware project
2. Install CARET
3. Download useful scripts for CARET
4. Build Autoware with CARET
5. Run Autoware to record trace data
6. Create analysis report

## 1. Get Autoware project

- Follow [the instruction (Source installation)](https://autowarefoundation.github.io/autoware-documentation/main/installation/autoware/source-installation/) to install Autoware
- Run [the tutorial (Rosbag replay simulation)](https://autowarefoundation.github.io/autoware-documentation/main/tutorials/ad-hoc-simulation/rosbag-replay-simulation/)
- Note:
  - We will re-build Autoware with CARET later, but it's recommended to make sure Autoware itself works appropriately in your PC
  - This explanation assumes you install Autoware to `${autoware_dir}` (e.g. `export autoware_dir=~/autoware` )

## 2. Install CARET

- Follow [the instruction](https://tier4.github.io/CARET_doc/latest/installation/installation/)
- Note:
  - This explanation assumes you install CARET to `${caret_dir}` (e.g. `export caret_dir=~/ros2_caret_ws/` )

## 3. Download useful scripts for CARET

- We will be downloading two components:
  - filter setting script ( `caret_topic_filter.bash` )
    - Autoware uses lots of nodes and topics. If all nodes and communications are traced, it causes trace data lost
    - So, it's better to ignore nodes and topics which are not necessary for your analysis
  - [caret_autoware_launch](https://github.com/tier4/caret_autoware_launch) package
    - Basically, you need to manually start trace session by yourself as described [here](https://tier4.github.io/CARET_doc/latest/recording/recording/)
    - It's handy to wrap Autoware launcher to automatically start CARET trace session

```sh
cd ${autoware_dir}
git clone https://github.com/tier4/caret_autoware_launch.git
cp caret_autoware_launch/scripts/caret_topic_filter.bash .
```

## 4. Build Autoware with CARET

### Build Autoware

- Note:
  - Before building Autoware, CARET needs to be enabled like the following commands
  - It's also important to set `BUILD_TESTING=Off`

```sh
cd ${autoware_dir}
rm -rf build/ install/ log/

source ${caret_dir}/install/local_setup.bash
colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=Off
```

### Check compilation (optional)

The following command checks if Autoware is built with CARET. It outputs warnings if a package is built without CARET. You can ignore them unless package names which you want to analyze are included in the warning message

```sh
cd ${autoware_dir}
ros2 caret check_caret_rclcpp -w ./

# Expected result
INFO    : 2023-01-17 14:12:28 | All packages are built using caret-rclcpp.

# Acceptable result (these packages are not necessary to analyze performance)
WARNING : 2022-08-25 18:14:31 | The following packages have not been built using caret-rclcpp:
 tier4_calibration_rviz_plugin
 initial_pose_button_panel
 autoware_auto_perception_rviz_plugin
 tier4_vehicle_rviz_plugin
 tier4_control_rviz_plugin
 localization_error_monitor
```

## 5. Run Autoware to record trace data

- There are two ways to record trace data:
  - Run Autoware and start recording via CLI
  - Run Autoware and start recording via launch
- Note:
  - Before running Autoware, some environmental settings need to be done like the following commands
  - Please modify map_path and rosbag file for your environment
  - Make sure that object detection works and path is created when you set a 2D Goal Pose, so that you can analyze end-to-end path later

### Run Autoware and start recording via CLI

- Recording can be started via CLI while autoware is running
- The trace data will be created in `~/.ros/tracing/session-yyyymmddhhmmss`

```sh
cd ${autoware_dir}
source ${caret_dir}/install/local_setup.bash
source ./install/local_setup.bash
export LD_PRELOAD=$(readlink -f ${caret_dir}/install/caret_trace/lib/libcaret.so)
source ./caret_topic_filter.bash

ros2 launch autoware_launch logging_simulator.launch.xml map_path:=$HOME/work/rosbag_map/universe/sample-map-rosbag vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit

# on another terminal
cd ${autoware_dir}
source ./install/local_setup.bash
ros2 bag play ~/work/rosbag_map/universe/sample-rosbag

# on another terminal
source ${caret_dir}/install/local_setup.bash
ros2 caret record -f 10000 --light
## press enter to start recording, then press enter to stop recording
```

### Run Autoware and start recording via launch

- Recording can be started automatically via launch file using `caret_autoware_launch` instead of `autoware_launch`
- It's handy but record will start at the beginning of Autoware, so the first few seconds in trace data will be meaningless
- The trace data will be created in `~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss`

```sh
cd ${autoware_dir}
source ${caret_dir}/install/local_setup.bash
source ./install/local_setup.bash
export LD_PRELOAD=$(readlink -f ${caret_dir}/install/caret_trace/lib/libcaret.so)
source ./caret_topic_filter.bash

ros2 launch caret_autoware_launch logging_simulator.launch.xml map_path:=$HOME/work/rosbag_map/universe/sample-map-rosbag vehicle_model:=sample_vehicle sensor_model:=sample_sensor_kit

# on another terminal
cd ${autoware_dir}
source ./install/local_setup.bash
ros2 bag play ~/work/rosbag_map/universe/sample-rosbag
```

### Validate trace data (optional)

- The following command checks if trace data is valid
- Please refer to the following explanation for warning messages
  - <https://tier4.github.io/CARET_doc/latest/recording/validating/>
- Also, the size of the trace data is usually 1 MByte per second. It's recommended to check trace data size, as well

```sh
ros2 caret check_ctf -d ~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss
```

## 6. Create analysis report

```sh
cd ${path-to-this-repo}/sample_autoware

export trace_data=~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss    # modify for your environment
export start_strip=20
export end_strip=5
export component_list_json=./component_list.json
export target_path_json=./target_path.json
export max_node_depth=10
export timeout=60
export draw_all_message_flow=false
export stats_path_list_csv=./stats_path_list.csv

sh ../report/report_analysis/make_report.sh
```

- Note: Setting files in this directory are just a sample, and may not work with your trace data. Please modify them as you want

## FAQ

### General

<https://tier4.github.io/CARET_doc/latest/faq/faq>

### Build

- Build for a package which uses `pcl_ros` fails (e.g. `static_centerline_optimizer` , `map_loader` )
  - Please refer to [this issue](https://github.com/tier4/caret/issues/56)

- Build fails due to `too few arguments to function ‘void ros_trace_rclcpp_publish(const void*, const void*, uint64_t)’`
  - Please refer to [this issue](https://github.com/tier4/caret/issues/69)

### Recording

- Trace data size is extremely small
  - If you use LTTng 2.13+, run the following command before starting Autoware
    - `ulimit -n 65535`

### Analysis report

- Path results in a created report is blank
  - Please find `Target path not found` error message in script log and modify `target_path.json`
  - If a node in `target_path.json` doesn't run at all while recording, the path will be blank
    - e.g. If route (2D GOAL) is not set, a path including planning module will be blank
  - `target_path.json` is just a sample and path may be changed as Autoware is modified
