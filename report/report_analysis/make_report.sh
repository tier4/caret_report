#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
use_python=true # to avoid reading trace data every step
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/report_"${trace_data_name}"
is_path_analysis_only=${is_path_analysis_only:-false}
is_html_only=${is_html_only:-false}

mkdir -p "${report_dir_name}"

# Save misc files
if [ -f "${trace_data}"/caret_record_info.yaml ]; then
    cp "${trace_data}"/caret_record_info.yaml "${report_dir_name}"/.
fi
cp "${component_list_json}" "${report_dir_name}"/.
cp "${target_path_json}" "${report_dir_name}"/.

if ${use_python}; then
    find_valid_duration=${find_valid_duration:-false}
    duration=${duration:-1200}

    if ! ${is_html_only}; then
        # Analyze
        python3 "${script_path}"/report_analysis/analyze_all.py "${trace_data}" "${report_dir_name}" \
            --component_list_json="${component_list_json}" \
            --start_strip "${start_strip}" \
            --end_strip "${end_strip}" \
            --sim_time "${sim_time}" \
            --target_path_json="${target_path_json}" \
            --architecture_file_path=architecture_path.yaml \
            --max_node_depth="${max_node_depth}" \
            --timeout="${timeout}" \
            --find_valid_duration="${find_valid_duration}" \
            --duration="${duration}" \
            --is_path_analysis_only="${is_path_analysis_only}" \
            -f -v
    fi

    # Make html pages
    python3 "${script_path}"/analyze_node/make_report_analyze_node.py "${report_dir_name}"
    python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"
    python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --relpath_from_report_store_dir="${relpath_from_report_store_dir}"
    python3 "${script_path}"/report_analysis/make_html_analysis.py "${trace_data}" "${report_dir_name}" --note_text_top "${note_text_top}" --note_text_bottom "${note_text_bottom}" --num_back 3
else
    # Path analysis
    python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" --target_path_json="${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
    python3 "${script_path}"/analyze_path/analyze_path.py "${trace_data}" "${report_dir_name}" --architecture_file_path=architecture_path.yaml --start_strip "${start_strip}" --end_strip "${end_strip}" --sim_time "${sim_time}" -f -v -m "${draw_all_message_flow}"
    python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"

    # Track of response time
    python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --relpath_from_report_store_dir="${relpath_from_report_store_dir}"

    # Node analysis
    python3 "${script_path}"/analyze_node/analyze_node.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --start_strip "${start_strip}" --end_strip "${end_strip}" --sim_time "${sim_time}" -f -v
    python3 "${script_path}"/analyze_node/make_report_analyze_node.py "${report_dir_name}"

    # Make top page
    python3 "${script_path}"/report_analysis/make_html_analysis.py "${trace_data}" "${report_dir_name}" --note_text_top "${note_text_top}" --note_text_bottom "${note_text_bottom}" --num_back 3
fi

echo "<<< OK. All report pages are created >>>"
