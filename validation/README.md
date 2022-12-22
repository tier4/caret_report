# Validation report

- This script evaluates if callbacks and topics run appropriately
- (Currently only for Autoware validation)

## What is created with this script?

- Input:
  - CARET trace data (CTF file)
  - Expectation file (csv file)
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
- `report_{dir_name_of_trace_data}` is created
- Open `index.html` to see a report

```sh
# Settings: modify for your usage and environment
export script_path=`pwd`/../validation        # Path to 'validation' directory in this repo cloned
export component_list_json=./component_list.json    # Path to setting file you prepare
export trace_data=~/.ros/tracing/caret_sample/      # Path to CARET trace data (CTF file)
export start_strip=10                               # strip time at the start [sec] for analysis
export end_strip=5                                  # strip time at the end [sec] for analysis
export expectation_callback_csv_filename=${script_path}/experiment/expectation_callback.csv
export expectation_topic_csv_filename=${script_path}/experiment/expectation_topic.csv
export note_text_top=./note_text_top.txt
export note_text_bottom=./note_text_bottom.txt

# Run script
sh ${script_path}/make_report.sh
```
