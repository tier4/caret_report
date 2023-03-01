#!/bin/sh

# shellcheck disable=SC1090

set -e

script_path=$(cd $(dirname $0)/../.. && pwd)
work_dir="$(pwd)"/work_verify

. /opt/ros/"$ROS_DISTRO"/setup.sh
. ~/ros2_caret_ws/install/local_setup.sh

# Create work directory
if [ -e "${work_dir}" ]; then
    rm -rf "${work_dir}"
fi
mkdir "${work_dir}"
cd "${work_dir}" || exit

# Download reference data
wget -nv https://github.com/tier4/CARET_report/releases/download/20221227/autoware_launch_trace_20221227-150253_universe_rosbag.zip
unzip autoware_launch_trace_20221227-150253_universe_rosbag.zip
git clone https://github.com/tier4/CARET_report.git -b gh-pages reference_result

# Create report
trace_data="$(pwd)"/autoware_launch_trace_20221227-150253_universe_rosbag
sample_autoware_dir="${script_path}"/sample_autoware
component_list_json=component_list.json
target_path_json=target_path.json
start_strip=20
end_strip=5
max_node_depth=10
timeout=30
draw_all_message_flow=false
export trace_data component_list_json target_path_json start_strip end_strip max_node_depth timeout draw_all_message_flow
cd "${sample_autoware_dir}" || exit
sh "${script_path}"/report/report_analysis/make_report.sh
mv output/report_autoware_launch_trace_20221227-150253_universe_rosbag "${work_dir}"/.

# Compare result
cd "${work_dir}" || exit
report_dir_1=./reference_result
report_dir_2=./report_autoware_launch_trace_20221227-150253_universe_rosbag
export report_dir_1 report_dir_2
sh "${script_path}"/report/compare/compare.sh
