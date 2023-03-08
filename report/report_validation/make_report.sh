#!/bin/sh

# shellcheck disable=SC2154

set -e

mkdir -p output

# Variable settings
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/val_"${trace_data_name}"

# Generate topic expectation list
python3 "${script_path}"/validate_topic/generate_expectation_list.py "${trace_data}" --report_directory="${report_dir_name}" --topic_list_filename="${topic_list_csv}" --expectation_csv_filename="${topic_list_csv}_pubsub.csv"

# Validate Callback
python3 "${script_path}"/validate_callback/validate_callback.py "${trace_data}" --report_directory="${report_dir_name}" --component_list_json="${component_list_json}" --expectation_csv_filename="${callback_list_csv}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Validate Topic
python3 "${script_path}"/validate_topic/validate_topic.py "${trace_data}" --report_directory="${report_dir_name}" --component_list_json="${component_list_json}" --expectation_csv_filename="${report_dir_name}/${topic_list_csv}_pubsub.csv" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/validate_topic/make_report_validate_topic.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Trace Validation failure
python3 "${script_path}"/trace_validation_failure/make_report_trace_validation_failure.py "${report_dir_name}"

# Re-make html for Callback to generate link to topics
python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Path analysis
python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" "${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
python3 "${script_path}"/analyze_path/analyze_path.py "${trace_data}" "${report_dir_name}" --architecture_file_path=architecture_path.yaml --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v -m "${draw_all_message_flow}"
python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"

# Track of response time
python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${stats_path_list_csv}"

# Index page
python3 "${script_path}"/report_validation/make_report_validation.py "${report_dir_name}" --component_list_json="${component_list_json}" --note_text_top="${note_text_top}" --note_text_bottom="${note_text_bottom}"

echo "<<< OK. All report pages are created >>>"
