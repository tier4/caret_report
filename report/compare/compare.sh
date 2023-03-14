#!/bin/sh

# Compare *.yaml, *.png (exclude *.html)
# apt install -y imagemagick

# shellcheck disable=SC2016,SC2181,SC2154
# cspell:ignore messageflow, PHASH

# set -e

echo "[compare] ========== Result =========="

echo "[compare] 1/3 file existence matches"
diff "${report_dir_1}" "${report_dir_2}" -r \
    --exclude=*.git --exclude=autoware_universe_node_diagram.png --exclude=*_0_messageflow.* --exclude=track_path |
    grep Only >diff_existence.txt

if [ -s diff_existence.txt ]; then
    cat diff_existence.txt
    echo "[ERROR][compare] ERROR. file existence doesn't match"
    return 1
else
    echo "[compare] OK. file existence matches"
fi

echo "[compare] 2/3 yaml files"
diff "${report_dir_1}" "${report_dir_2}" -r \
    --exclude=*.html --exclude=*.git --exclude=*.png \
    -I "filename_messageflow:*" \
    >diff_yaml.txt

if [ -s diff_yaml.txt ]; then
    cat diff_yaml.txt
    echo "[ERROR][compare] ERROR. yaml doesn't match"
    return 1
else
    echo "[compare] OK. yaml matches"
fi

echo "[compare] 3/3 PNG files"
if [ -e png_err ]; then
    rm png_err
fi

# (
#     cd "${report_dir_1}" || exit
#     find ./ -type f -name "*.png" \
#         -not -name "autoware_universe_node_diagram.png" -not -name "*_0_messageflow.png" \
#         -print0
# ) |
#     xargs -0 -I{} sh -c ' \
#         diff=`convert -metric PHASH "${report_dir_1}"/{} "${report_dir_2}"/{} -compare -format "%[distortion]" info:` && \
#         if [ $diff != "inf" ]; then
#             result=`python3 -c "print(${diff} > 50.0)"` && \
#             if [ $result = True ]; then
#                 echo {} ${diff}
#                 touch png_err
#             fi
#         fi'

if [ -e png_err ]; then
    echo "[ERROR][compare] ERROR. PNG doesn't match"
    return 1
else
    echo "[compare] OK. PNG matches"
fi

echo "[compare] ====== ALL OK =============="

# (cd "${report_dir_1}"; find -type f -name "*.png" \
#     -not -name "autoware_universe_node_diagram.png" -not -name "*_0_messageflow.png" \
#     -print0) \
#     | xargs -0 -I{} diff "${report_dir_1}"/{} "${report_dir_2}"/{} \
#     >diff_png.txt
# (cd "${report_dir_1}"; find -type f -name "*.yaml" \
#     -print0) \
#     | xargs -0 -I{} diff "${report_dir_1}"/{} "${report_dir_2}"/{} -I "filename_messageflow:" \
#     >diff_yaml.txt

# (cd "${report_dir_1}"; find -type f -name "*.png" \
#     -not -name "autoware_universe_node_diagram.png" -not -name "*_0_messageflow.png" \
#     -print0) \
#     | xargs -0 -I{} sh -c ' \
#         convert -resize 100x50 "${report_dir_1}"/{} a.png && \
#         convert -resize 100x50 "${report_dir_2}"/{} b.png && \
#         composite -compose difference a.png b.png diff.png && \
#         diff=`identify -format "%[mean]" diff.png` && \
#         result=`echo "$diff > 10" | bc` && \
#         if [ $result -eq 1 ]; then
#             echo {}
#         fi'
