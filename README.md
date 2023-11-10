[![Test with Autoware](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml/badge.svg)](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml)

# CARET_report

- This repository contains report creation scripts for CARET
  - [sample report page](https://tier4.github.io/CARET_report/)
- Please refer to [report](./report) to find explanation of how to use the scripts
- Please refer to [sample_autoware](./sample_autoware) to find sample settings and a full explanation of how to analyze Autoware with CARET

## Requirements

- Ubuntu 22.04
  - ROS2 Humble
  - [CARET](https://github.com/tier4/caret) ( Use main/latest )
- The following software is also needed

```sh
pip3 install 'Flask>=3' anytree
```

## FAQ and Troubleshooting

### Process is stuck or PC freezes/crashes

- It uses lots of memory
  - 64GB or more is recommended
  - In case crash happens due to memory shortage, increase swap space

### About sim_time

The analysis scripts don't support sim_time. So, please be careful when you analyze trace data which have been created with `ros2 bag play` with `-r` option. For instance, "Frequency" will be half when you add `-r 0.5` option.

### How to run regression test

```sh
# cd to this repo cloned
sh ./compare/makereport_and_compare.sh
```
