# General analysis report

## What is created with this script?

- Input:
  - CARET trace data (CTF file)
- Output (html pages):
  - [Top page (index.html)](./top):
    - Links to each report page
    - Summary
  - [Node analysis report](./analyze_node):
    - Detailed information of each callback function
    - Node health verification results by [subscription callback problem detector](./check_callback_sub) and [timer callback problem detector](./check_callback_timer)
  - [Path analysis report](./analyze_path):
    - Message flow graph and response time of each target path

<b>Open a [sample report page](https://tier4.github.io/CARET_report/)</b>

## Requirements

[Please refer to the top page](https://github.com/tier4/CARET_report#requirements)

## How to use

- Run the following commands
  - Make sure to modify settings for your usage and environment
  - Make sure to prepare JSON files
- `report_{dir_name_of_trace_data}` is created
- Open `index.html` to see a report

```sh
# Settings: modify for your usage and environment
export script_path=./CARET_report/report            # Path to 'report' directory in this repo cloned
export component_list_json=./component_list.json    # Path to setting file you prepare
export target_path_json=./target_path.json          # Path to setting file you prepare
export trace_data=~/.ros/tracing/caret_sample/      # Path to CARET trace data (CTF file)
export start_time=25                                # start time[sec] for analysis
export duration_time=9999                           # duration time[sec] for analysis
export max_node_depth=10                            # The number of depth to search path
export timeout=60                                   # Timeout[sec] to search path
export draw_all_message_flow=false                  # Flag to a create message flow graph for a whole time period (this will increase report creation time)

# Run script
sh ${script_path}/make_report.sh
```

## Setting JSON files

### component_list.json

- Node analysis report will be created for each `component_name`
- Settings
  - `component_list_json` : path to the JSON file
- Please describe the following information
  - component name information (`component_dict`)
    - Pairs of `component_name` and `regular expression for nodes belonging to the component`
  - Ignore node list (`ignore_list`)
    - List of `Regular expression for nodes to be ignored`

```json:component_list.json
{
    "component_dict": {
        "Component_A" : "^/component_a",
        "Component_B" : "^/component_b",
    },
    "ignore_list": [
        "noisy_node_name_a",
        "^/annoying_component_name",
    ]
}
```

### target_path.json

- Path analysis report will show results for paths described in this JSON file
- Settings
  - `target_path_json` : path to the JSON file
  - `max_node_depth` : In case a target path is not found, increase the number. In case the script stuck, decrease the number
- Please describe the following information
  - Pair of `name` and `path`
  - `path` is a list of `node_name` (note: `path` doesn't mean path as filesystem!)
    - Regular expression is supported
    - You can also set `[node_name, topic_name]` instead of `node_name` . It is useful when two nodes are connected via multiple topics

```json:target_path.json
[
    {
        "name": "path_name",
        "path": [
            "The first node_name in the path",
            "The second node_name in the path",
            ["The third node_name in the path", "The topic name published by the third node"]
            "...",
            "The last node_name in the path",
        ]
    },
    {
        "name": "sample_path",
        "path": [
            "/component_a/node_1",
            "/component_a/node_2",
            ["/component_a/node_3", "/topic_3"],
            "/component_a/node_4_.*"
        ]
    },
]
```

## Tips

### Easy way to create target_path.json

- Install [Dear RosNodeViewer](https://github.com/takeshi-iwanari/dear_ros_node_viewer)
- Open graph ( e.g.: `dear_ros_node_viewer architecture.yaml` )
- Select nodes in the path which you want to analyze
  - ctrl + click
- Press C to export node name list to clip board
- Paste the exported node name list to json file

### Why regular expression is helpful?

- In case a node name varies for each execution, you can write node name in JSON like the following
  - Before: `/node_name_xyz_abc1234567_1234567_1234567891234567891`
  - After: `/node_name_xyz.*`

### About sim_time

The analysis scripts don't support sim_time. So, please be careful when you analyze trace data which have been created with `ros2 bag play` with `-r` option. For instance, "Frequency" will be half when you add `-r 0.5` option.

### About Note

Contents described in `note_text_top.txt` and `note_text_bottom.txt` are added to top page. You can freely add any comment there. e.g. you can add environment information.
