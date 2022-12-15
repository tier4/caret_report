#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
trace_data_name=$(basename "${trace_data}")
report_dir_name=report_${trace_data_name}

# Callback
# python3 "${script_path}"/callback/validate_callback.py "${trace_data}" --component_list_json="${component_list_json}" --expectation_csv_filename="${expectation_csv_filename}" -s "${start_time}" -d "${duration_time}" -f -v
# python3 "${script_path}"/callback/make_report_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

# Topic
# python3 "${script_path}"/topic/validate_topic.py "${trace_data}" --component_list_json="${component_list_json}" --expectation_csv_filename="${expectation_csv_filename}" -s "${start_time}" -d "${duration_time}" -f -v
python3 "${script_path}"/topic/make_report_topic.py "${report_dir_name}" --component_list_json="${component_list_json}"



# Top page
# python3 "${script_path}"/top/make_report_top.py "${report_dir_name}" --component_list_json="${component_list_json}"

echo "<<< OK. All report pages are created >>>"
