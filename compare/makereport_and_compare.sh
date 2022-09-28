#!/bin/sh

# shellcheck disable=SC1090

# set -e

WORK_DIR=$(pwd)/verify_work

. /opt/ros/"$ROS_DISTRO"/setup.sh
. ~/ros2_caret_ws/install/local_setup.sh

# Create work directory
if [ -e "${WORK_DIR}" ]; then
    rm -rf "${WORK_DIR}"
fi
mkdir "${WORK_DIR}"
cd "${WORK_DIR}" || exit

# Download reference data
wget -nv https://github.com/tier4/CARET_report/releases/download/20220831/autoware_launch_trace_20220826-105249_universe_rosbag.zip
unzip autoware_launch_trace_20220826-105249_universe_rosbag.zip
git clone https://github.com/tier4/CARET_report.git -b gh-pages reference_result

# Create report
script_path="$(pwd)"/../
trace_data="$(pwd)"/autoware_launch_trace_20220826-105249_universe_rosbag
sample_autoware_dir="$(pwd)"/../sample_autoware
package_list_json=package_list.json
target_path_json=target_path.json
start_time=20
duration_time=9999
max_node_depth=2
draw_all_message_flow=false
export script_path trace_data package_list_json target_path_json start_time duration_time max_node_depth draw_all_message_flow
cd "${sample_autoware_dir}" || exit
sh "${script_path}"/make_report.sh
mv report_autoware_launch_trace_20220826-105249_universe_rosbag "${WORK_DIR}"/.

# Compare result
cd "${WORK_DIR}" || exit
report_dir_1=./reference_result
report_dir_2=./report_autoware_launch_trace_20220826-105249_universe_rosbag
export report_dir_1 report_dir_2
sh "${script_path}"/compare/compare.sh
