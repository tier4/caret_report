# Scripts to check timer callback health

## What is created

- Verification result:
  - This report shows gap between timer frequency and timer callback frequency
  - This report also outputs warnings when the gap is huge, which means the callback function doesn't run appropriately
  - It is useful to find out nodes which may have a problem. Please use this result as subsidiary data
- Artifacts
  - `report_ooo/check_callback_timer/`
    - `index.html` : report main page
    - `index_warning.html` : report main page (callbacks with warning only)
    - `ooo.html` : graph file as html
    - `ooo.png` : graph file as image
    - `stats_callback_timer.yaml` : statistics file
    - `stats_callback_timer_warning.yaml` : statistics file (callbacks with warning only)

## Scripts

### `check_callback_timer.py`

```sh:usage
usage: check_callback_timer.py [-h] [--component_list_json COMPONENT_LIST_JSON] [-s START_POINT] [-d DURATION]
                               [-r GAP_THRESHOLD_RATIO] [-n COUNT_THRESHOLD] [-v] [-f]
                               trace_data
```

- This script checks gap between timer frequency and timer callback frequency
- The condition of warning:
  - `timer callback frequency` is less than `GAP_THRESHOLD_RATIO * timer_frequency` for `COUNT_THRESHOLD` times)

### `make_report_timer.py`

```sh:usage
usage: make_report_timer.py [-h] report_directory
```

- This script creates a report html page
