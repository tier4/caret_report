#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/val_"${trace_data_name}"

mkdir -p "${report_dir_name}"

# Save misc files
if [ -f "${trace_data}"/caret_record_info.yaml ]; then
    cp "${trace_data}"/caret_record_info.yaml "${report_dir_name}"/.
fi
cp "${component_list_json}" "${report_dir_name}"/.
cp "${target_path_json}" "${report_dir_name}"/.
cp "${callback_list_csv}" "${report_dir_name}"/.
cp "${topic_list_csv}" "${report_dir_name}"/.

# Save parameters for report creation
report_info_access="${script_path}"/common/report_info_access.py
caret_report_info_file="${report_dir_name}"/caret_report_info.yaml
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save start_strip "${start_strip}"
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save end_strip "${end_strip}"
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save max_node_depth "${max_node_depth}"
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save timeout "${timeout}"
set +e
caret_version=$(ros2 caret version)
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save caret_version "${caret_version}"
caret_config_version=$(git log -n 1 --format=%H)
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save caret_config_version "${caret_config_version}"
current_dir=$(pwd)
cd ${script_path}
caret_report_version=$(git log -n 1 --format=%H)
cd ${current_dir}
python3 ${report_info_access} ${caret_report_info_file} ${trace_data_name} save caret_report_version "${caret_report_version}"
set -e

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
python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --report_store_mount_name="${report_store_mount_name}"

# Index page
python3 "${script_path}"/report_validation/make_report_validation.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --note_text_top="${note_text_top}" --note_text_bottom="${note_text_bottom}"

echo "<<< OK. All report pages are created >>>"
