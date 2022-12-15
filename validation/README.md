```sh
docker image build --network host -t caret/caret_autoware_validation --build-arg CARET_VERSION="v0.3.3" ./docker
```

```sh
work_dir=`pwd`
docker run -it --rm \
    --user $(id -u):$(id -g) \
    --net host \
    -v ${work_dir}:/work \
    -v /etc/localtime:/etc/localtime:ro \
    caret/caret_autoware_validation
```

```sh
# Settings: modify for your usage and environment
export script_path=./CARET_report/validation        # Path to 'validation' directory in this repo cloned
export component_list_json=./component_list.json    # Path to setting file you prepare
export trace_data=~/.ros/tracing/caret_sample/      # Path to CARET trace data (CTF file)
export start_time=20                                # start time[sec] for analysis
export duration_time=9999                           # duration time[sec] for analysis
export expectation_callback_csv_filename=${script_path}/experiment/expectation_callback.csv
export expectation_topic_csv_filename=${script_path}/experiment/expectation_topic.csv

# Run script
sh ${script_path}/make_report.sh
```
