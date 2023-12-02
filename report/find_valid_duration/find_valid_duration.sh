#!/bin/sh

# shellcheck disable=SC2154

set -e

# Variable settings
script_path=$(dirname "$0")/..
trace_data_name=$(basename "${trace_data}")

# Path analysis
python3 "${script_path}"/analyze_path/add_path_to_architecture.py "${trace_data}" "${target_path_json}" --architecture_file_path=architecture_path.yaml --max_node_depth="${max_node_depth}" --timeout="${timeout}" -v
python3 "${script_path}"/find_valid_duration/find_valid_duration.py "${trace_data}" --architecture_file_path=architecture_path.yaml --duration "${duration}" -v
