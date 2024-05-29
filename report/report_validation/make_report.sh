#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
use_python=true # to avoid reading trace data every step
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")
report_dir_name=output/val_"${trace_data_name}"
is_path_analysis_only=${is_path_analysis_only:-false}
is_html_only=${is_html_only:-false}

mkdir -p "${report_dir_name}"

# Save misc files
if [ -f "${trace_data}"/caret_record_info.yaml ]; then
    cp "${trace_data}"/caret_record_info.yaml "${report_dir_name}"/.
fi
cp "${component_list_json}" "${report_dir_name}"/.
cp "${target_path_json}" "${report_dir_name}"/.
cp "${callback_list_csv}" "${report_dir_name}"/.

if ${use_python}; then
    find_valid_duration=${find_valid_duration:-false}
    duration=${duration:-1200}

    if ! ${is_html_only}; then
        # Analyze and validate
        python3 "${script_path}"/report_validation/validate_all.py "${trace_data}" "${report_dir_name}" \
            --sub_trace_data="${sub_trace_data}" \
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
            --report_directory="${report_dir_name}" \
            --callback_list_filename="${callback_list_csv}" \
            --topic_list_filename="topic_list.csv" \
            --expectation_topic_csv_filename="topic_list_pubsub.csv" \
            --expectation_callback_csv_filename="${callback_list_csv}" \
            --is_path_analysis_only="${is_path_analysis_only}" \
            -f -v
    fi

    # Make html pages
    python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"
    python3 "${script_path}"/validate_topic/make_report_validate_topic.py "${report_dir_name}" --component_list_json="${component_list_json}"
    if ! ${is_path_analysis_only} && ! ${is_html_only}; then
        python3 "${script_path}"/trace_validation_failure/make_report_trace_validation_failure.py "${report_dir_name}"
    fi
    python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"
    python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"
    python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --relpath_from_report_store_dir="${relpath_from_report_store_dir}"
    python3 "${script_path}"/report_validation/make_html_validation.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --note_text_top="${note_text_top}" --note_text_bottom="${note_text_bottom}" --num_back=3
else
    # Generate topic expectation list
    python3 "${script_path}"/validate_topic/generate_expectation_list.py "${trace_data}" --report_directory="${report_dir_name}" --callback_list_filename="${callback_list_csv}" --topic_list_filename=topic_list.csv --expectation_csv_filename=topic_list_pubsub.csv

    # Validate Callback
    python3 "${script_path}"/validate_callback/validate_callback.py "${trace_data}" --report_directory="${report_dir_name}" --component_list_json="${component_list_json}" --expectation_csv_filename="${callback_list_csv}" --start_strip "${start_strip}" --end_strip "${end_strip}" --sim_time "${sim_time}" -f -v
    python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

    # Validate Topic
    python3 "${script_path}"/validate_topic/validate_topic.py "${trace_data}" --report_directory="${report_dir_name}" --component_list_json="${component_list_json}" --expectation_csv_filename="${report_dir_name}/topic_list_pubsub.csv" --start_strip "${start_strip}" --end_strip "${end_strip}" --sim_time "${sim_time}" -f -v
    python3 "${script_path}"/validate_topic/make_report_validate_topic.py "${report_dir_name}" --component_list_json="${component_list_json}"

    # Trace Validation failure
    python3 "${script_path}"/trace_validation_failure/make_report_trace_validation_failure.py "${report_dir_name}"

    # Re-make html for Callback to generate link to topics
    python3 "${script_path}"/validate_callback/make_report_validate_callback.py "${report_dir_name}" --component_list_json="${component_list_json}"

    # Path analysis
    python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" --target_path_json="${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
    python3 "${script_path}"/analyze_path/analyze_path.py "${trace_data}" "${report_dir_name}" --architecture_file_path=architecture_path.yaml --start_strip "${start_strip}" --end_strip "${end_strip}" --sim_time "${sim_time}" -f -v -m "${draw_all_message_flow}"
    python3 "${script_path}"/analyze_path/make_report_analyze_path.py "${report_dir_name}"

    # Track of response time
    python3 "${script_path}"/track_path/make_report_track_path.py "${report_dir_name}" "${report_store_dir}" --relpath_from_report_store_dir="${relpath_from_report_store_dir}"

    # Top page
    python3 "${script_path}"/report_validation/make_html_validation.py "${trace_data}" "${report_dir_name}" --component_list_json="${component_list_json}" --note_text_top="${note_text_top}" --note_text_bottom="${note_text_bottom}" --num_back=3
fi

echo "<<< OK. All report pages are created >>>"
