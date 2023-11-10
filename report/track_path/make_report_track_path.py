# Copyright 2023 Tier IV, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Script to make report page
"""
import os
import sys
import argparse
from pathlib import Path
import glob
import math
import logging
import csv
import datetime
import re
import subprocess
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import figure, save
from bokeh.models import FixedTicker
from bokeh.resources import CDN
import flask

_logger = logging.Logger(__name__)
app = flask.Flask(__name__)


# value_name_list = ['best_avg', 'best_min', 'best_max', 'best_p50', 'best_p95', 'best_p99',
#               'worst_avg', 'worst_min', 'worst_max', 'worst_p50', 'worst_p95', 'worst_p99']
value_name_list = ['best_max', 'best_p99', 'best_p50', 'best_avg']
value_name_display_list = ['Max', '99%ile', 'Median', 'Avg']
color_list = ['red', 'orange', 'blue', 'green', 'purple', 'black', 'brown', 'pink', 'gray', 'olive', 'cyan']


def make_file_name(target_path_name, dest_dir, with_dir=True):
    """Make file name"""
    if with_dir:
        return f'{dest_dir}/{target_path_name.replace("/", "_")}.html'
    else:
        return f'{target_path_name.replace("/", "_")}.html'


def render_page(reportpath_version_dict, stats_path_dict, filename_path_dict, destination_path, template_path):
    """Render html page"""
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title='Response Time Tracking',
                reportpath_version_dict=reportpath_version_dict,
                stats_path_dict=stats_path_dict,
                filename_path_dict=filename_path_dict,
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def get_datetime_from_report_name(report_dir: str):
    # use the last or the 2nd last dir name for report name
    report_dir_split = report_dir.split('/')
    report_name_list = [report_dir_split[-1], report_dir_split[-2]] if len(report_dir_split) >= 2 else [report_dir_split[-1]]
    trace_datetime = None
    for report_name in report_name_list:
        trace_datetime_re = re.search(r'\d{14}', report_name)
        if trace_datetime_re:
            trace_datetime = datetime.datetime.strptime(trace_datetime_re.group(), '%Y%m%d%H%M%S')
            break
        else:
            trace_datetime_re = re.search(r'\d{8}-\d{6}', report_name)
            if trace_datetime_re:
                trace_datetime = datetime.datetime.strptime(trace_datetime_re.group(), '%Y%m%d-%H%M%S')
                break
    if trace_datetime is None:
        _logger.warning(f"Unable to get datetime for {report_dir}")
        trace_datetime = 'unknown'
    return str(trace_datetime)


def get_trace_data_info_from_yaml(yaml_dir: str):
    caret_record_info_path = Path(yaml_dir).joinpath('caret_record_info.yaml')
    autoware_version, map, route = '', '', ''
    if os.path.exists(caret_record_info_path):
        with open(caret_record_info_path, encoding='UTF-8') as f_yaml:
            caret_record_info = yaml.safe_load(f_yaml)
            if 'autoware_version' in caret_record_info:
                autoware_version = str(caret_record_info['autoware_version']).split('/')[-1]
            if 'map' in caret_record_info:
                map = caret_record_info['map']
            if 'route' in caret_record_info:
                route = caret_record_info['route']
    return autoware_version, map, route


def make_stats_file_dict(dest_dir: str, report_store_dir: str) -> list[tuple[str,str]]:
    """Make file list"""
    stats_file_dict = {}

    current_report_name = dest_dir.split('/')[-2]
    current_report_type = current_report_name[:3]    # rep or val
    report_store_dir = report_store_dir.rstrip('/')
    past_report_list = subprocess.run(['find', report_store_dir, '-maxdepth', '3', '-name', f'{current_report_type}*'], text=True, stdout=subprocess.PIPE).stdout
    past_report_list = past_report_list.strip('\n').split('\n')
    past_report_list = [e for e in past_report_list if 'validate_' not in e and e != '']
    if report_store_dir in past_report_list:
        past_report_list.remove(report_store_dir)

    current_report = str(Path(dest_dir).parent)
    report_list = past_report_list + [current_report]

    for report_dir in report_list:
        report_dir = report_dir.rstrip('/')
        datetime = get_datetime_from_report_name(report_dir)
        autoware_version, map, route = get_trace_data_info_from_yaml(report_dir)
        if autoware_version != '':
            version = autoware_version + ', ' + datetime + ', ' + map + ', ' + route
        else:
            version = datetime
        stats_path = f'{report_dir}/analyze_path/stats_path.yaml'
        if os.path.isfile(stats_path):
            if version in stats_file_dict:
                _logger.warning(f"New report found. version: {version}, report_dir: {report_dir}")
                stats_file_dict.pop(version)
            stats_file_dict[version] = stats_path
        else:
            _logger.error(f"Unable to find stats file for {report_dir}")
        if report_dir == current_report:
            current_version = version

    stats_file_list = sorted(stats_file_dict.items())    # sort by version
    stats_file_dict = {}
    for key, value in stats_file_list:
        stats_file_dict[key] = value
        if key == current_version:          # use until the current version
            break

    return stats_file_dict


def make_stats(dest_dir: str, report_store_dir: str, report_store_mount_name: str):
    """Make stats"""
    stats_file_dict = make_stats_file_dict(dest_dir, report_store_dir)

    reportpath_version_dict = {}   # key: version, value: path to report
    for version, stats_file in stats_file_dict.items():
        path_report_file = Path(stats_file).parent.joinpath('index.html')
        top_report_file = Path(stats_file).parent.parent.joinpath('index.html')
        if path_report_file.exists() or True:    # Always create link
            path_report_file = os.path.relpath(path_report_file, Path(dest_dir).resolve())
            top_report_file = os.path.relpath(top_report_file, Path(dest_dir).resolve())
            if report_store_mount_name != '' and report_store_mount_name in top_report_file:
                # Create a new relpath assuming the current report is created under report_store_mount_name
                path_report_file = '../../../..' + path_report_file.split(report_store_mount_name)[-1]
                top_report_file = '../../../..' + top_report_file.split(report_store_mount_name)[-1]
        else:
            path_report_file = ''
            top_report_file = ''
        reportpath_version_dict[version] = (path_report_file, top_report_file)

    stats_version_dict = {}  # key: version, value: stats
    for version, stats_file in stats_file_dict.items():
        with open(stats_file, 'r', encoding='utf-8') as f_yaml:
            stats_version_dict[version] = yaml.safe_load(f_yaml)

    target_path_name_list = []
    if len(stats_version_dict)> 0:
        current_version = next(reversed(stats_version_dict))
        curent_stats = stats_version_dict[current_version]
        target_path_name_list = [target_path_info['target_path_name'] for target_path_info in curent_stats]

    # Create dataframe for each target path (index=version, column=avg, max, min, etc.)
    df_per_path = pd.DataFrame(columns=pd.MultiIndex.from_product([target_path_name_list, value_name_list]), dtype=float)
    for version, stats in stats_version_dict.items():
        if len(target_path_name_list) > 0:
            df_per_path.loc[version] = np.nan
        for target_path_name in target_path_name_list:
            for target_path_info in stats:
                if target_path_info['target_path_name'] == target_path_name:
                    df_per_path.loc[version][target_path_name] = [
                        target_path_info[val] if type(target_path_info[val]) is float else np.nan for val in value_name_list]
                    break

    # Create figure for each target path
    filename_path_dict = {}
    for target_path_name in target_path_name_list:
        df = df_per_path[target_path_name]
        fig = figure(width=1000, height=400, active_scroll='wheel_zoom',
                     x_axis_label='Version', y_axis_label='Response Time [ms]')
        for index, value_name in enumerate(value_name_list):
            fig.line(x=list(range(len(df.index))), y=df[value_name], legend_label=value_name_display_list[index], color=color_list[index], line_width=2)
            fig.circle(x=list(range(len(df.index))), y=df[value_name], legend_label=value_name_display_list[index], color=color_list[index], size=5)
        fig.y_range.start = 0
        fig.xaxis.major_label_overrides = {i: df.index[i].replace(', ', '\n', 2) for i in range(len(df.index))}
        fig.xaxis.major_label_orientation = -math.pi/2
        fig.xaxis.ticker = FixedTicker(ticks=list(range(len(df.index))))
        fig.add_layout(fig.legend[0], "right")
        save(fig, filename=make_file_name(target_path_name, dest_dir) , title=target_path_name, resources=CDN)
        filename_path_dict[target_path_name] = make_file_name(target_path_name, dest_dir, False)

    # Create stats for each target path
    stats_path_dict = {}
    for target_path_name in target_path_name_list:
        stats = {}
        df = df_per_path[target_path_name]
        for index, value_name in enumerate(value_name_list):
            df_row = df.loc[:, value_name]
            stats[value_name_display_list[index]] = {
                version: df_row.iloc[version_index] for version_index, version in enumerate(reportpath_version_dict.keys())}
        stats_path_dict[target_path_name] = stats

    return reportpath_version_dict, stats_path_dict, filename_path_dict


def make_report(dest_dir: str, report_store_dir: str, report_store_mount_name: str):
    """Make report page"""
    reportpath_version_dict, stats_path_dict, filename_path_dict = make_stats(dest_dir, report_store_dir, report_store_mount_name)
    destination_path = f'{dest_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_track_path.html'
    render_page(reportpath_version_dict, stats_path_dict, filename_path_dict, destination_path, template_path)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('report_store_dir', nargs=1, type=str)
    parser.add_argument('--report_store_mount_name', type=str, default='')
    args = parser.parse_args()
    return args


def main():
    """main function"""
    args = parse_arg()

    dest_dir = args.dest_dir[0] + '/track_path'
    report_store_dir = args.report_store_dir[0]
    report_store_mount_name = args.report_store_mount_name
    _logger.info(f'dest_dir: {dest_dir}')
    _logger.info(f'report_store_dir: {report_store_dir}')
    _logger.info(f'report_store_mount_name: {report_store_mount_name}')
    os.makedirs(dest_dir, exist_ok=True)

    make_report(dest_dir, report_store_dir, report_store_mount_name)
    print('<<< OK. report_track_path is created >>>')


if __name__ == '__main__':
    main()
