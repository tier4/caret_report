#!/bin/sh

# shellcheck disable=SC1090

set -e

script_path=$(cd "$(dirname "$0")"/.. && pwd)
work_dir="$(pwd)"/work_verify

. /opt/ros/"$ROS_DISTRO"/setup.sh
. ~/ros2_caret_ws/install/local_setup.sh

# Create work directory
if [ -e "${work_dir}" ]; then
    rm -rf "${work_dir}"
fi
mkdir "${work_dir}"
cd "${work_dir}" || exit

# Download trace data
wget -nv https://github.com/tier4/caret_report/releases/download/20231114/session-20231114050140.tgz
tar xzvf session-20231114050140.tgz

# Download reference data
wget -v https://github.com/tier4/CARET_report/releases/download/20231114/report_session-20231114050140.zip
unzip report_session-20231114050140.zip
mv report_session-20231114050140 reference_result

# Create report
trace_data="$(pwd)"/session-20231114050140
sample_autoware_dir="${script_path}"/sample_autoware
start_strip=0
end_strip=0
sim_time=false
component_list_json=component_list.json
target_path_json=target_path.json
max_node_depth=20
timeout=120
draw_all_message_flow=false
report_store_dir=./output
relpath_from_report_store_dir=false
export trace_data start_strip end_strip sim_time component_list_json target_path_json max_node_depth timeout draw_all_message_flow report_store_dir relpath_from_report_store_dir
cd "${sample_autoware_dir}" || exit
sh "${script_path}"/report/report_analysis/make_report.sh
mv output/report_session-20231114050140 "${work_dir}"/.

# Compare result
cd "${work_dir}" || exit
report_dir_1=./reference_result
report_dir_2=./report_session-20231114050140
export report_dir_1 report_dir_2
sh "${script_path}"/compare/compare.sh
