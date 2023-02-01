#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
trace_data_name=$(basename "${trace_data}")
report_dir_name=report_${trace_data_name}

# # Generate topic expectation list
# python3 "${script_path}"/topic/generate_expectation_list.py "${trace_data}" --topic_list_filename=topic_list.csv --expectation_csv_filename="${expectation_topic_csv_filename}"

# Callback
python3 "${script_path}"/callback/validate_callback.py "${trace_data}" --component_list_json="${component_list_json}" --expectation_csv_filename="${expectation_callback_csv_filename}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/callback/make_report_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Topic
python3 "${script_path}"/topic/validate_topic.py "${trace_data}" --component_list_json="${component_list_json}" --expectation_csv_filename="${expectation_topic_csv_filename}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/topic/make_report_topic.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Re-make html for Callback to generage link to topics
python3 "${script_path}"/callback/make_report_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Index page
python3 "${script_path}"/index/make_report_index.py "${report_dir_name}" --component_list_json="${component_list_json}" --note_text_top="${note_text_top}" --note_text_bottom="${note_text_bottom}"

echo "<<< OK. All report pages are created >>>"
