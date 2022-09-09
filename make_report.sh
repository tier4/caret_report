#!/bin/sh
set -e

trace_data_name=$(basename ${trace_data})
report_dir_name=report_${trace_data_name}

# Node analysis
python3 ${script_path}/analyze_node/analyze_node.py ${trace_data} --package_list_json=${package_list_json} -s ${start_time} -d ${duration_time} -f -v
python3 ${script_path}/analyze_node/make_report_node.py ${report_dir_name}

python3 ${script_path}/check_callback_sub/check_callback_sub.py ${trace_data} --package_list_json=${package_list_json} -s ${start_time} -d ${duration_time} -f -v
python3 ${script_path}/check_callback_sub/make_report_sub.py ${report_dir_name}

python3 ${script_path}/check_callback_timer/check_callback_timer.py ${trace_data} --package_list_json=${package_list_json} -s ${start_time} -d ${duration_time} -f -v
python3 ${script_path}/check_callback_timer/make_report_timer.py ${report_dir_name}

# Path analysis
python3 ${script_path}/analyze_path/add_path_to_architecture.py ${target_path_json} --trace_data=${trace_data} --max_node_depth=${max_node_depth} -v
python3 ${script_path}/analyze_path/analyze_path.py ${trace_data} architecture_path.yaml -s ${start_time} -d ${duration_time} -f -v -m ${draw_all_message_flow}
python3 ${script_path}/analyze_path/make_report_path.py ${report_dir_name}

# Make top page
python3 ${script_path}/top/make_report_top.py ${report_dir_name} --note_text_top note_text_top.txt --note_text_bottom note_text_bottom.txt

echo "<<< OK. All report pages are created >>>"
