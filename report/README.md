# Scripts to create report

## General analysis report

- [./report_analysis](./report_analysis)
- This report contains the following analysis
  - analyze_node
  - analyze_path
  - track_path
  - (check_callback_sub)
  - (check_callback_timer)
- Run the following commands
  - Make sure to modify settings for your usage and environment
  - Make sure to prepare setting files
- `output/report_{dir_name_of_trace_data}` is created
  - Open `index.html` to see a report

```sh
script_path=<path-to-caret_report>/report/report_analysis   # Path to CARET_report
export component_list_json=./component_list.json     # Path to setting file
export target_path_json=./target_path.json           # Path to setting file
export max_node_depth=20                             # The number of depth to search path. Increase it in case path is not found
export timeout=120                                   # Timeout[sec] to search path. Increase it in case path is not found
export draw_all_message_flow=false                   # Flag to a create message flow graph for a whole time period (this will increase report creation time)
export report_store_dir=./output                     # Path to past report store if exist
export relpath_from_report_store_dir=false           # Create a link to past reports assuming the current report is created under report_store_dir
export note_text_top=./note_text_top.txt             # Path to setting file
export note_text_bottom=./note_text_bottom.txt       # Path to setting file
export start_strip=120                               # strip time at the start [sec] for analysis
export end_strip=30                                  # strip time at the end [sec] for analysis
export sim_time=false                                # use simulation time (ROS time) or system time
export trace_data=~/.ros/tracing/session-yyyymmddhhmmss  # Path to CARET trace data (CTF file)
sh ${script_path}/make_report.sh
```

## Validation report

- [./report_validation](./report_validation)
- This report contains the following analysis
  - validate_callback
  - validate_topic
  - trace_validation_failure
  - analyze_path
  - track_path
- Run the following commands
  - Make sure to modify settings for your usage and environment
  - Make sure to prepare setting files
- `output/val_{dir_name_of_trace_data}` is created
  - Open `index.html` to see a report

```sh
script_path=<path-to-caret_report>/report/report_validation   # Path to CARET_report
export component_list_json=./component_list.json     # Path to setting file
export target_path_json=./target_path.json           # Path to setting file
export max_node_depth=20                             # The number of depth to search path. Increase it in case path is not found
export timeout=120                                   # Timeout[sec] to search path. Increase it in case path is not found
export draw_all_message_flow=false                   # Flag to a create message flow graph for a whole time period (this will increase report creation time)
export report_store_dir=./output                     # Path to past report store if exist
export relpath_from_report_store_dir=false           # Create a link to past reports assuming the current report is created under report_store_dir
export callback_list_csv=./callback_list.csv         # Path to setting file
export note_text_top=./note_text_top.txt             # Path to setting file
export note_text_bottom=./note_text_bottom.txt       # Path to setting file
export start_strip=120                               # strip time at the start [sec] for analysis
export end_strip=30                                  # strip time at the end [sec] for analysis
export sim_time=false                                # use simulation time (ROS time) or system time
export trace_data=~/.ros/tracing/session-yyyymmddhhmmss  # Path to CARET trace data (CTF file)
sh ${script_path}/make_report.sh
```

## Setting files

- Note
  - Please refer to [sample_autoware](../sample_autoware) to find sample settings

### component_list.json

- This file contains basic settings for analysis
- Scripts using this file
  - analyze_node
  - check_callback_sub
  - check_callback_sub
  - report_validation
  - validate_callback
  - validate_topic

```py
{
  # Component name information
  # Pairs of "component_name" and "regular expression for nodes belonging to the component"
  "component_dict": {
    "sensing": "^/sensing",
    "localization": "^/localization",
    "perception": "^/perception",
    "planning": "^/planning",
    "control": "^/control",
    "system": "^/system",
    "vehicle": "(^/vehicle|^/pacmod|^/raw_vehicle_cmd_converter)"
  },

  # External input topic information
  # Pairs of "regular expression for topics" and "regular expression for nodes"
  "external_in_topic_list": [
    ["^/sensing/.*/velodyne_packets", ""],
    ["^/pacmod/from_can_bus", "^/pacmod/pacmod$"]
  ],

  # External output topic information
  # Pairs of "regular expression for topics" and "regular expression for nodes"
  "external_out_topic_list": [
    ["^/pacmod/to_can_bus", "^/pacmod/pacmod$"]
  ],

  # Ignore node list
  # List of "Regular expression for nodes to be ignored"
  "ignore_list": [
    "container"
  ]
}
```

### note_text_top.txt, note_text_bottom.txt

- The html text in the files are added on the top/bottom of the report index page
- Scripts using this file
  - report_analysis
  - report_validation

### target_path.json

- Path analysis report will show results for paths described in this JSON file
  - The script tries to search paths including the described nodes (and topics) in the JSON file
  - In case the path is not found, the path is not shown in the report
  - If several paths are found, the path name will be displayed as `"{path_name}_0"`, `"{path_name}_1"`, ... in the report
- Scripts using this file
  - analyze_path
- `"path"`
  - Node list of the path
  - Regular expression is supported, but the first and the last entry should not include a regular expression
  - Intermediate nodes can be omitted, but it may cause searching path failure or increase the time to search path
  - `[node_name, topic_name]` can be used instead of `node_name`
    - In this case, node whose name is `node_name` and who publishes or subscribes `topic_name` will be found
    - It is useful when two nodes are connected via multiple topics
  - `path_blocks` can be used instead of `path` so that path can be divided
    - It is useful when the path is complicated and is not found or searching the path takes too many time
    - example. <https://github.com/tier4/CARET_report/blob/f13b70c1bb2fdb16651f9535537d279822958733/sample_autoware/target_path.json#L63>
- `"include_first_callback"` , `"include_last_callback"` (optional)
  - The latency in the first/last callback is added to the path
  - If these parameters are not set, `true` is used as default

```py
{
  # List of topics to be ignored while searching paths
  "ignore_topic_list": [
    "/tf",
    "/tf_static"
  ],

  # List of nodes to be ignored while searching paths
  "ignore_node_list": [
    "/_ros2cli_/*",
    "/launch_ros_*"
  ],

  # List of path description
  "target_path_list": [
    {
      # Name of the path
      "name": "component_sensing",

      # Node list of the path
      "path": [
        "/sensing/lidar/top/velodyne_driver",
        "/sensing/lidar/top/velodyne_convert_node",
        "/sensing/lidar/top/crop_box_filter_self",
        "/sensing/lidar/top/crop_box_filter_mirror",
        "/sensing/lidar/top/distortion_corrector_node",
        "/sensing/lidar/top/ring_outlier_filter",
        "/sensing/lidar/concatenate_data"
      ],
      "include_first_callback": false,
      "include_last_callback": true
    }
  ]
}
```

#### Easy way to create target_path.json

- Install [Dear RosNodeViewer](https://github.com/takeshi-iwanari/dear_ros_node_viewer)
- Open graph ( e.g.: `dear_ros_node_viewer architecture.yaml` )
- Select nodes in the path which you want to analyze
  - ctrl + click
- Press C to export node name list to clip board
- Paste the exported node name list to json file

#### Why regular expression is helpful?

- In case a node name varies for each execution, you can write node name in JSON like the following
  - Before: `/node_name_xyz_abc1234567_1234567_1234567891234567891`
  - After: `/node_name_xyz.*`

### callback_list.csv

- This file contains expected callback frequency for validation
- Scripts using this file
  - validate_callback
- The following files are generated in the created report directory, and they are helpful to update this file
  - callback_list_new.csv
    - The list of callbacks which are not described in callback_list.csv, but are actually used
  - callback_list_deleted.csv
    - The list of callbacks which are described in callback_list.csv, but are actually not used

```csv
# "node name" , "callback type" , "trigger" , "expected Hz"
/sensing/lidar/top/velodyne_convert_node,subscription_callback,/sensing/lidar/top/velodyne_packets,10
/planning/scenario_planning/lane_driving/behavior_planning/behavior_path_planner,timer_callback,100000000,10
```

## Others

### Find the valid start/end of the trace data

- [./find_valid_duration](./find_valid_duration)
- This script finds the duration from all the path begin to min(specified_duration, data end)
- The result is written to `start_strip.txt` and `end_strip.txt`

```sh
script_path=<path-to-caret_report>/report/find_valid_duration   # Path to CARET_report
export component_list_json=./component_list.json                # Path to setting file
export target_path_json=./target_path.json                      # Path to setting file
export duration=60                                              # duration to load trace data
export trace_data=~/.ros/tracing/session-yyyymmddhhmmss         # Path to CARET trace data (CTF file)
sh ${script_path}/find_valid_duration.sh
```
