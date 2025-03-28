#!/bin/bash

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

# /work directory is not always mounted
if [ -d /work ]; then
    cd /work || exit 1
fi

# $trace_data_name is not always set
if [ -z "$trace_data_name" ]; then
    trace_data_name=""
fi

export trace_data=/${trace_data_name}
export report_store_dir=/report_store_dir

sh /CARET_report/report/report_analysis/make_report.sh

exec "$@"
