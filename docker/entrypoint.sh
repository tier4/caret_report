#!/bin/bash
set -e

. /opt/ros/$ROS_DISTRO/setup.sh
. /ros2_caret_ws/install/local_setup.sh

cd /work
export package_list_json=/work/${package_list_json}
export target_path_json=/work/${target_path_json}

export start_time=15
export duration_time=600
export max_node_depth=20
export draw_all_message_flow=false

export script_path=/CARET_report
export trace_data=/trace_data

sh ${script_path}/make_report.sh

exec "$@"
