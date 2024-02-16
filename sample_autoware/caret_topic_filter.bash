#!/bin/bash

export CARET_IGNORE_NODES="\
/aggregator_node:\
/autoware_api/*:\
/awapi/*:\
/control/transform_listener_impl_*:\
/fault_injection:\
/launch_ros*:\
/planning/mission_planning/mission_planning_container:\
/planning/scenario_planning/parking/parking_container:\
/robot_state_publisher:\
/rosapi*:\
/rosbag2_player:\
/rosbag2_recorder:\
/rosbridge_websocket:\
/rviz*:\
/static_map_to_odom_tf_publisher:\
/system/system_monitor/system_monitor/system_monitor_container:\
/transform_listener_impl*:\
/system/dummy_diag_publisher/dummy_diag_publisher_*:\
/system/system_monitor/ntp_monitor:\
/caret_trace_*:\
"

export CARET_IGNORE_TOPICS="\
/api/*:\
/autoware/*:\
/awapi/*:\
/client_count:\
/clock:\
/connect_clients:\
/control/trajectory_follower/lane_departure_checker_node/debug/*:\
/diagnostics:\
/diagnostics_agg:\
/diagnostics_err:\
/diagnostics_toplevel_state:\
/initialpose:\
/initialpose2d:\
/localization/debug*:\
/localization/pose_estimator/exe_time_ms:\
/localization/pose_estimator/iteration_num:\
/localization/pose_estimator/transform_probability:\
/localization/pose_twist_fusion_filter/debug*:\
/map/pointcloud_map:\
/map/vector_map:\
/map/vector_map_marker:\
/parameter_events:\
/perception/object_recognition/detection/clustering/debug*:\
/planning/planning_diagnostics/planning_error_monitor/debug/*:\
/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner/debug/*:\
/planning/scenario_planning/lane_driving/behavior_planning/behavior_velocity_planner/debug/*:\
/planning/scenario_planning/lane_driving/behavior_planning/debug/*:\
/planning/scenario_planning/lane_driving/motion_planning/obstacle_avoidance_planner/debug/*:\
/planning/scenario_planning/lane_driving/motion_planning/obstacle_stop_planner/debug/*:\
/planning/scenario_planning/lane_driving/motion_planning/surround_obstacle_checker/debug/*:\
/planning/scenario_planning/motion_velocity_smoother/debug/*:\
/planning/scenario_planning/parking/freespace_planner/debug/*:\
/robot_description:\
/rosout:\
/sensing/lidar/.*/dual_return_outlier_filter/debug/*:\
/sensing/radar/.*/from_can_bus:\
/sensing/imu/.*/from_can_bus:\
/simulation/*:\
/tf:\
/tf_static:\
/vehicle/engage:\
/vehicle/raw_vehicle_cmd_converter/debug*:\
"

# if you want to select nodes or topics,
# please remove comment out of the followings.
# export CARET_SELECT_NODES=\
# "\
# /rviz*\
# "

# export CARET_SELECT_TOPICS=\
# "\
# /clock:\
# /parameter_events\
# "
