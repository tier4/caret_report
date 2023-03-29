[![Test with Autoware](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml/badge.svg)](https://github.com/tier4/CARET_report/actions/workflows/test_autoware.yaml)

# Report creation scripts for CARET

- [./report/report_analysis](./report/report_analysis)
  - create general analysis report
- [./report/report_validation](./report/report_validation)
  - create validation report

## Sample

- [sample report page](https://tier4.github.io/CARET_report/)
- Please refer to [sample_autoware](./sample_autoware) to find sample settings and a full explanation of how to analyze Autoware with CARET

## Requirements

- Ubuntu 22.04
  - ROS2 Humble
  - [CARET](https://github.com/tier4/caret) ( Use main/latest )
- The following software is also needed

```sh
# Flask 2.1.0 (need to specify version) is required to create html report pages
pip3 install Flask==2.1.0 anytree
```

## FAQ and Troubleshooting

### Process is stuck or PC freezes/crashes

- It uses lots of memory
  - 64GB or more is recommended
  - In case crash happens due to memory shortage, increase swap space

### How to run regression test

```sh
# cd to this repo cloned
sh ./report/compare/makereport_and_compare.sh
```
