#!/bin/sh

export component_list_json=./component_list.json
export target_path_json=./target_path.json
export max_node_depth=20
export timeout=120
export draw_all_message_flow=false
export report_store_dir=./output
export relpath_from_report_store_dir=false
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt
export callback_list_csv=./callback_list.csv
export start_strip=0
export end_strip=0
export sim_time=false

export trace_data=~/work/caret_tracedata/universe/session-20231114050140/session-20231114050140

## Use this to find the valid start/end of the trace data automatically
# export duration=1200
# sh ../report/find_valid_duration/find_valid_duration.sh
# export start_strip=$(cat start_strip.txt)
# export end_strip=$(cat end_strip.txt)
# rm start_strip.txt end_strip.txt

# Create analysis report
sh ../report/report_analysis/make_report.sh

# Create validation report
sh ../report/report_validation/make_report.sh
