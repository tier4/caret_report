#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/report_"${trace_data_name}"

mkdir -p "${report_dir_name}"

# Save misc files
if [ -f "${trace_data}"/caret_record_info.yaml ]; then
    cp "${trace_data}"/caret_record_info.yaml "${report_dir_name}"/.
fi
cp "${component_list_json}" "${report_dir_name}"/.
cp "${target_path_json}" "${report_dir_name}"/.

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

# Path analysis
python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" "${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
python3 "${script_path}"/analyze_path/analyze_path.py "${trace_data}" "${report_dir_name}" --architecture_file_path=architecture_path.yaml --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v -m "${draw_all_message_flow}"
python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"

# Track of response time
python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --report_store_mount_name="${report_store_mount_name}"

# Node analysis
python3 "${script_path}"/analyze_node/analyze_node.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
python3 "${script_path}"/analyze_node/make_report_analyze_node.py "${report_dir_name}"

# # Check callback health
# python3 "${script_path}"/check_callback_sub/check_callback_sub.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
# python3 "${script_path}"/check_callback_sub/make_report_sub.py "${report_dir_name}"
# python3 "${script_path}"/check_callback_timer/check_callback_timer.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" -f -v
# python3 "${script_path}"/check_callback_timer/make_report_timer.py "${report_dir_name}"

# Make top page
python3 "${script_path}"/report_analysis/make_report_analysis.py "${trace_data}" "${report_dir_name}" --note_text_top "${note_text_top}" --note_text_bottom "${note_text_bottom}"

echo "<<< OK. All report pages are created >>>"
