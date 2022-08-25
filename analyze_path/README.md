# Scripts to create path analysis reports

## What is created

- Path analysis report
    - This report shows a message flow graph and response time for each target path
    - It is useful to check if the response time meets constraints
    - In case you find a problem, you can see the message flow graph and the node analysis report to investigate more details
- Artifacts
    - `report_ooo/path/`
        - `index.html` : report main page
        - `ooo.html` : graph file as html
        - `ooo.png` : graph file as image
        - `stats_path.yaml` : statistics file

## Scripts

### `add_path_to_architecture.py`

```sh:usage
usage: add_path_to_architecture.py [-h] [--trace_data TRACE_DATA]
                                   [--architecture_file_src ARCHITECTURE_FILE_SRC]
                                   [--architecture_file_dst ARCHITECTURE_FILE_DST] [--use_latest_message]
                                   [--max_node_depth MAX_NODE_DEPTH] [-v]
                                   target_path_json
```

- This script creates a new `architecture_path.yaml` which contains path information
- To get the original architecture file, you need to set either `trace_data` or `architecture_file_src`
    - Using `architecture_file_src` saves your time

### `analyze_path.py`

```sh:usage
usage: analyze_path.py [-h] [-m MESSAGE_FLOW] [-s START_POINT] [-d DURATION] [-f] [-v]
                       trace_data [architecture_file]
```

- This script creates message flow graph (html and image files) and statistics file (`stats_path.yaml`) for each target path
- When `MESSAGE_FLOW` is yes, message flow graph is created for a whole time period. It will increase report creation time and the created graph file is very heavy

### `make_report_path.py`

```sh:usage
usage: make_report_path.py [-h] report_directory
```

- This script creates a report html page
