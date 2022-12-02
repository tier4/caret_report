# CARET Analysis for Autoware

This page shows how to analyze [Autoware](https://github.com/autowarefoundation/autoware) with CARET

1. Get Autoware project
2. Install CARET
3. Modify Autoware code to work with CARET
4. Build Autoware with CARET
5. Run Autoware to get trace data
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

## 3. Modify Autoware code to work with CARET

- We will be making two types of modifications before building Autoware with CARET
  - 3.a Add configuration for CARET
  - 3.b Change code to avoid CARET restrictions

### 3.a Add configuration for CARET

- Changes, and Why the change is needed:
  - Add filter setting script
    - Autoware uses lots of nodes and topics. If all nodes and communications are traced, it causes trace data lost
    - So, it's better to ignore nodes and topics which are not necessary for your analysis
  - Add [caret_autoware_launch](https://github.com/tier4/caret_autoware_launch) package
    - Basically, you need to manually start trace session by yourself as described [here](https://tier4.github.io/CARET_doc/latest/recording/recording/)
    - It's handy to wrap Autoware launcher to automatically start CARET trace session
- How to modify:

  - Please refer to [this commit](https://github.com/takeshi-iwanari/autoware/commit/16fb26f365df64c4b7e279df35bdc41b72d7732b) , and make the same change
    - Make sure you have `src/vendor/caret_autoware_launch/` by updating `src` ( `vcs import src < autoware.repos && vcs pull src` )
  - Or, cherry-pick this change ( Note: this change is made on [20220823](https://github.com/autowarefoundation/autoware/commit/b1e2f6ef5982ccbe9434bff49397b2783713cb98), so it may not be valid in the future )

  ```sh
  cd ${autoware_dir}
  git remote add autoware_caret https://github.com/takeshi-iwanari/autoware
  git fetch autoware_caret 16fb26f365df64c4b7e279df35bdc41b72d7732b
  git cherry-pick -n 16fb26f365df64c4b7e279df35bdc41b72d7732b
  ```

### 3.b Change code to avoid CARET restrictions

- Changes, and Why the change is needed:
  - Keep a node you want to analyze within the following CARET restrictions:
    - CARET cannot trace data, when a node has "two or more" timer callback functions whose timer period are the same
    - CARET cannot trace data, when a node has "two or more" subscription callback functions whose topic name are the same
  - Dependency on `rclcpp` needs to be written in package.xml
  - Give more priority to CARET/rclcpp rather than ROS/rclcpp
- How to modify:

  - Please refer to [this commit](https://github.com/takeshi-iwanari/autoware.universe/commit/7c1eaa08f19f9cf09d697069e1f8e48fd35bb4cb) , and make the same change
  - Or, cherry-pick this change ( Note: this change is made on [20220823](https://github.com/autowarefoundation/autoware.universe/commit/2d62bdf127b8215c73be6416c57861d4a812ef0b), so it may not be valid in the future )

  ```sh
  cd ${autoware_dir}
  cd src/universe/autoware.universe/
  git remote add autoware_universe_caret https://github.com/takeshi-iwanari/autoware.universe
  git fetch autoware_universe_caret 7c1eaa08f19f9cf09d697069e1f8e48fd35bb4cb
  git cherry-pick -n 7c1eaa08f19f9cf09d697069e1f8e48fd35bb4cb
  ```

## 4. Build Autoware with CARET

### Build Autoware

- Note:
  - Before building Autoware, CARET needs to be enabled like the following commands

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

WARNING : 2022-08-25 18:14:31 | The following packages have not been built using caret-rclcpp:
 tier4_calibration_rviz_plugin
 initial_pose_button_panel
 autoware_auto_perception_rviz_plugin
 tier4_vehicle_rviz_plugin
 tier4_control_rviz_plugin
 localization_error_monitor
```

## 5. Run Autoware to get trace data

### Run Autoware

- Note:
  - Before running Autoware, some environmental settings need to be done like the following commands
  - To run Autoware, `caret_autoware_launch` is used instead of `autoware_launch`
  - Please modify map_path and rosbag file for your environment
  - Make sure that object detection works and path is created when you set a 2D Goal Pose, so that you can analyze end-to-end path later
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

### Check trace data (optional)

- The following command checks if trace data is valid. You may see lots of warnings, but you can ignore them unless callback names which you want to analyze are included in the warning message
- Also, the size of the trace data is usually 1 MByte per second. It's recommended to check trace data size, as well

```sh
ros2 caret check_ctf -d ~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss
```

## 6. Create analysis report

```sh
cd ${path-to-this-repo}/sample_autoware

export script_path=../
export package_list_json=./package_list.json
export target_path_json=./target_path.json
export trace_data=~/.ros/tracing/autoware_launch_trace_yyyymmdd-hhmmss    # modify for your environment
export start_time=20
export duration_time=9999
export max_node_depth=2
export draw_all_message_flow=false

sh ${script_path}/make_report.sh
```

## FAQ

### Build

- Build for a package which uses `pcl_ros` fails. (e.g. `static_centerline_optimizer` , `map_loader` )
  - Please refer to [this issue](https://github.com/tier4/caret/issues/56)

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
