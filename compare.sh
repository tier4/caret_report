#!/bin/sh

# Compare *.yaml, *.png (exclude *.html)

# shellcheck disable=SC2181,SC2154
# cspell:ignore messageflow

# set -e

diff "${report_dir_1}" "${report_dir_2}" -r \
    --exclude=*.html --exclude=*.git --exclude=autoware_universe_node_diagram.png --exclude=*_0_messageflow.png \
    -I "filename_messageflow:*" \
    >diff.txt

echo "[compare] ========== Result =========="
if [ -s diff.txt ]; then
    cat diff.txt
    echo "[ERROR][compare] content doesn't match"
    return 1
else
    echo "[compare] OK"
    return 0
fi
echo "[compare] ============================"

# (cd "${report_dir_1}"; find -type f -name "*.png" \
#     -not -name "autoware_universe_node_diagram.png" -not -name "*_0_messageflow.png" \
#     -print0) \
#     | xargs -0 -I{} diff "${report_dir_1}"/{} "${report_dir_2}"/{} \
#     >diff_png.txt
# (cd "${report_dir_1}"; find -type f -name "*.yaml" \
#     -print0) \
#     | xargs -0 -I{} diff "${report_dir_1}"/{} "${report_dir_2}"/{} -I "filename_messageflow:" \
#     >diff_yaml.txt
