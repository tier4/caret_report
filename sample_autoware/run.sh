#!/bin/sh

export component_list_json=./component_list.json
export target_path_json=./target_path.json
# export target_path_json=./target_path_latest.json
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
export is_path_analysis_only=false
export is_html_only=false
export find_valid_duration=false
export duration=0

if [ $# -lt 1 ]; then
  echo "Error: Please specify the path to trace_data (cf: ~/.ros/tracing/session-ooo) as an argument."
  echo "Usage: $0 <trace_data_path> [sub_trace_data_path:optional]"
  exit 1
fi

export trace_data=$1
if [ $# -ge 2 ]; then
  export sub_trace_data=$2
fi

# Create analysis report
sh ../report/report_analysis/make_report.sh

# Create validation report
sh ../report/report_validation/make_report.sh
