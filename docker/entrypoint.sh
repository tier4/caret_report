#!/bin/bash -e

# shellcheck disable=SC1090,SC1091

# Add user and group: start
USER_ID=$(id -u)
GROUP_ID=$(id -g)

if [ x"$GROUP_ID" != x"0" ]; then
    groupadd -g "$GROUP_ID" "$USER_NAME"
fi

if [ x"$USER_ID" != x"0" ]; then
    useradd -d /home/"$USER_NAME" -m -s /bin/bash -u "$USER_ID" -g "$GROUP_ID" "$USER_NAME"
fi
export HOME=/home/"$USER_NAME"

sudo chmod u-s /usr/sbin/useradd
sudo chmod u-s /usr/sbin/groupadd
# Add user and group: end

. /opt/ros/"$ROS_DISTRO"/setup.sh
. /ros2_caret_ws/install/local_setup.sh

cd /work
export component_list_json=/work/${component_list_json}
export target_path_json=/work/${target_path_json}

# export start_time=15
# export duration_time=600
# export max_node_depth=20
# export draw_all_message_flow=false

export script_path=/CARET_report
export trace_data=/trace_data

sh ${script_path}/make_report.sh

exec "$@"
