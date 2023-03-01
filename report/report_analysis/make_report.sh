#!/bin/sh

# shellcheck disable=SC2154

set -e

mkdir -p output

# Variable settings
script_path=$(dirname $0)/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/report_"${trace_data_name}"

# Path analysis
python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" "${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
python3 "${script_path}"/analyze_path/analyze_path.py "${trace_data}" "${report_dir_name}" --architecture_file_path=architecture_path.yaml --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v -m "${draw_all_message_flow}"
python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"

# Track of response time
python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" stats_path_list.csv

# Node analysis
python3 "${script_path}"/analyze_node/analyze_node.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/analyze_node/make_report_analyze_node.py "${report_dir_name}"

# # Check callback health
# python3 "${script_path}"/check_callback_sub/check_callback_sub.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
# python3 "${script_path}"/check_callback_sub/make_report_sub.py "${report_dir_name}"
# python3 "${script_path}"/check_callback_timer/check_callback_timer.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
# python3 "${script_path}"/check_callback_timer/make_report_timer.py "${report_dir_name}"

# Make top page
python3 "${script_path}"/report_analysis/make_report_analysis.py "${report_dir_name}" --note_text_top "${note_text_top}" --note_text_bottom "${note_text_bottom}"

echo "<<< OK. All report pages are created >>>"
