#!/bin/sh

# export script_path=../report
# export component_list_json=./component_list.json
# export target_path_json=./target_path.json
# export start_time=15
# export duration_time=9999
# export max_node_depth=4
# export draw_all_message_flow=false
# export note_text_top=./note_text_top.txt
# export note_text_bottom=./note_text_bottom.txt
# export trace_data=~/Downloads/autoware_launch_trace_20221227-150253_universe_rosbag
# sh ${script_path}/make_report.sh

export script_path=../validation
export component_list_json=./component_list.json
export start_strip=15
export end_strip=5
export callback_list_csv=./callback_list.csv
export topic_list_csv=./topic_list.csv
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt
export trace_data=~/Downloads/autoware_launch_trace_20221227-150253_universe_rosbag
sh ${script_path}/make_report.sh
