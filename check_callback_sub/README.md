# Scripts to check subscription callback health

## What is created

- Verification result:
  - This report shows gap between topic publishment and subscription callback frequency
  - This report also outputs warnings when the gap is huge, which means the callback function doesn't run appropriately
  - It is useful to find out nodes which may have a problem. Please use this result as subsidiary data
- Artifacts
  - `report_ooo/check_callback_sub/`
    - `index.html` : report main page
    - `index_warning.html` : report main page (callbacks with warning only)
    - `ooo.html` : graph file as html
    - `ooo.png` : graph file as image
    - `stats_callback_subscription.yaml` : statistics file
    - `stats_callback_subscription_warning.yaml` : statistics file (callbacks with warning only)

## Scripts

### `check_callback_sub.py`

```sh:usage
usage: check_callback_sub.py [-h] [--package_list_json PACKAGE_LIST_JSON] [-s START_POINT] [-d DURATION]
                             [-r GAP_THRESHOLD_RATIO] [-n COUNT_THRESHOLD] [-v] [-f]
                             trace_data
```

- This script checks gap between topic publishment and subscription callback frequency
- The condition of warning:
  - `subscription callback frequency` is less than `GAP_THRESHOLD_RATIO * topic frequency` for `COUNT_THRESHOLD` times)

### `make_report_sub.py`

```sh:usage
usage: make_report_sub.py [-h] report_directory
```

- This script creates a report html page
