#!/bin/sh

# set -e

WORK_DIR=`pwd`/verify_work

. /opt/ros/"$ROS_DISTRO"/setup.sh
. ~/ros2_caret_ws/install/local_setup.sh

# Create work directory
if [ -e "${WORK_DIR}" ]; then
    rm -rf "${WORK_DIR}"
fi
mkdir "${WORK_DIR}"
cd "${WORK_DIR}"

# Download reference data
wget -nv https://github.com/tier4/CARET_report/releases/download/20220831/autoware_launch_trace_20220826-105249_universe_rosbag.zip
unzip autoware_launch_trace_20220826-105249_universe_rosbag.zip
git clone https://github.com/tier4/CARET_report.git -b gh-pages reference_result

# Create report
export script_path=`pwd`/../
export trace_data=`pwd`/autoware_launch_trace_20220826-105249_universe_rosbag
export sample_autoware_dir=`pwd`/../sample_autoware
export package_list_json=package_list.json
export target_path_json=target_path.json
export start_time=20
export duration_time=9999
export max_node_depth=2
export draw_all_message_flow=false
cd ${sample_autoware_dir}
sh ${script_path}/make_report.sh
mv report_autoware_launch_trace_20220826-105249_universe_rosbag "${WORK_DIR}"/.

# Compare result
cd "${WORK_DIR}"
export report_dir_1=./reference_result
export report_dir_2=./report_autoware_launch_trace_20220826-105249_universe_rosbag
sh ${script_path}/compare/compare.sh
