#!/bin/sh

# Create analysis report
export component_list_json=./component_list.json
export target_path_json=./target_path.json
export max_node_depth=20
export timeout=120
export draw_all_message_flow=false
export report_store_dir=./output
export relpath_from_report_store_dir=false
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt
export start_strip=0
export end_strip=0

export trace_data=~/work/caret_tracedata/universe/session-20231114050140/session-20231114050140
sh ../report/report_analysis/make_report.sh

# Create validation report
export component_list_json=./component_list.json
export target_path_json=./target_path.json
export max_node_depth=20
export timeout=120
export draw_all_message_flow=false
export report_store_dir=./output
export relpath_from_report_store_dir=false
export callback_list_csv=./callback_list.csv
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt
export start_strip=0
export end_strip=0

export trace_data=~/work/caret_tracedata/universe/session-20231114050140/session-20231114050140
sh ../report/report_validation/make_report.sh
