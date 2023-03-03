# Validation report

- This script evaluates if callbacks and topics run appropriately
- (Currently only for Autoware validation)

## What is created with this script?

- Input:
  - CARET trace data (CTF file)
  - Expectation file (csv file)
    - callback_list.csv
    - topic_list.csv
- Output (html pages):
  - Index page (index.html)
    - Summary
    - Pass/Failed status for callbacks and topics per component
  - Callback validation report
    - Pass/Failed status for callbacks
    - Callback details: frequency, period and latency
  - Topic validation report
    - Pass/Failed status for topics
    - Topic details: frequency, period and communication latency

## Requirements

[Please refer to the top page](https://github.com/tier4/CARET_report#requirements)

## How to use

- Run the following commands
  - Make sure to modify settings for your usage and environment
  - Make sure to prepare setting files
- `val_{dir_name_of_trace_data}` is created
- Open `index.html` to see a report

```sh
# Settings: modify for your usage and environment
export trace_data=~/.ros/tracing/caret_sample/      # Path to CARET trace data (CTF file)
export start_strip=20                               # strip time at the start [sec] for analysis
export end_strip=5                                  # strip time at the end [sec] for analysis
export component_list_json=./component_list.json    # Path to setting file you prepare
export target_path_json=./target_path.json          # Path to setting file you prepare
export max_node_depth=10                            # The number of depth to search path
export timeout=60                                   # Timeout[sec] to search path
export draw_all_message_flow=false                  # Flag to a create message flow graph for a whole time period (this will increase 
export stats_path_list_csv=./stats_path_list.csv    # Path to setting file you prepare
export callback_list_csv=./callback_list.csv
export topic_list_csv=./topic_list.csv
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt

# Run script
sh ../report/report_validation/make_report.sh
```

## How to update callback_list.csv and topic_list.csv

- These lists should be updated as a target application changes
- The following files will be generated to update these files easily
  - callback_list_new.csv: callbacks which are used in the trace data but not listed in callback_list.csv
  - callback_list_deleted.csv: callbacks which are not found or not used in the trace data
  - topic_list_new.csv: topics which are used in the trace data but not listed in topic_list.csv
  - topic_list_unknown.csv: topics which are not found in the trace data
  - topic_list_deleted.csv: topics which are not found or not used in the trace data
