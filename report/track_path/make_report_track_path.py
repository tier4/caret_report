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
import math
import logging
import csv
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import Figure, figure, show, save
from bokeh.models import FixedTicker
from bokeh.resources import CDN
import flask

_logger = logging.Logger(__name__)
app = flask.Flask(__name__)


# value_name_list = ['best_avg', 'best_min', 'best_max', 'best_p50', 'best_p95', 'best_p99',
#               'worst_avg', 'worst_min', 'worst_max', 'worst_p50', 'worst_p95', 'worst_p99']
value_name_list = ['best_max', 'best_p99', 'best_avg', 'best_p50']
value_name_display_list = ['max', '99%ile', 'avg', 'median']
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


def make_stats_file_list(dest_dir: str, stats_list_file: str) -> list[tuple[str,str]]:
    """Make file list"""
    stats_file_list = []
    if not os.path.isfile(stats_list_file):
        _logger.error(f"Unable to read csv: {stats_list_file}")
        return []
    with open(stats_list_file, 'r', encoding='utf-8') as f_csv:
        for row in csv.DictReader(f_csv, ['version', 'stats_file']):
            stats_file = row['stats_file']
            stats_file_abs = Path(stats_file).expanduser()
            stats_file_from_current = Path(stats_file).resolve()
            stats_file_from_csv = Path.joinpath(Path(os.path.dirname(stats_list_file)).resolve(), stats_file)
            stats_file_from_dest = Path.joinpath(Path(os.path.dirname(dest_dir)).resolve(), stats_file)
            stats_file_from_dest_parent = Path.joinpath(Path(os.path.dirname(dest_dir)).resolve().parent, stats_file)
            if os.path.isfile(stats_file_abs):
                stats_file_list.append((row['version'], stats_file_abs))
            elif os.path.isfile(stats_file_from_current):
                stats_file_list.append((row['version'], stats_file_from_current))
            elif os.path.isfile(stats_file_from_csv):
                stats_file_list.append((row['version'], stats_file_from_csv))
            elif os.path.isfile(stats_file_from_dest):
                stats_file_list.append((row['version'], stats_file_from_dest))
            elif os.path.isfile(stats_file_from_dest_parent):
                stats_file_list.append((row['version'], stats_file_from_dest_parent))
            else:
                _logger.error(f"Unable to read stats file: {row}")
                continue
    return stats_file_list


def make_stats(dest_dir: str, stats_list_file: str):
    """Make stats"""
    stats_file_list = make_stats_file_list(dest_dir, stats_list_file)

    reportpath_version_dict = {}   # key: version, value: path to report
    for version, stats_file in stats_file_list:
        report_path = os.path.relpath(os.path.dirname(stats_file), Path(dest_dir).resolve()) + '/index.html'
        if os.path.isfile(os.path.dirname(stats_file) + '/index.html'):
            reportpath_version_dict[version] = report_path
        else:
            reportpath_version_dict[version] = ''

    stats_version_dict = {}  # key: version, value: stats
    for version, stats_file in stats_file_list:
        with open(stats_file, 'r', encoding='utf-8') as f_yaml:
            stats_version_dict[version] = yaml.safe_load(f_yaml)

    target_path_name_list = []
    if len(stats_file_list)> 0:
        target_path_name_list = [
            target_path_info['target_path_name'] for target_path_info in stats_version_dict[stats_file_list[0][0]]]

    # Create dataframe for each target path (index=version, column=avg, max, min, etc.)
    df_per_path = pd.DataFrame(columns=pd.MultiIndex.from_product([target_path_name_list, value_name_list]), dtype=float)
    for version, stats in stats_version_dict.items():
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
        fig = figure(plot_width=1000, plot_height=400, active_scroll='wheel_zoom',
                     x_axis_label='Version', y_axis_label='Response Time [ms]')
        for index, value_name in enumerate(value_name_list):
            fig.line(x=range(len(df.index)), y=df[value_name], legend_label=value_name_display_list[index], color=color_list[index], line_width=2)
            fig.circle(x=range(len(df.index)), y=df[value_name], legend_label=value_name_display_list[index], color=color_list[index], size=5)
        fig.y_range.start = 0
        fig.xaxis.major_label_overrides = {i: df.index[i] for i in range(len(df.index))}
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
            stats[value_name_display_list[index]] = {
                version: df[value_name][version_index] for version_index, version in enumerate(reportpath_version_dict.keys())}
        stats_path_dict[target_path_name] = stats

    return reportpath_version_dict, stats_path_dict, filename_path_dict


def make_report(dest_dir: str, stats_list_file: str):
    """Make report page"""
    reportpath_version_dict, stats_path_dict, filename_path_dict = make_stats(dest_dir, stats_list_file)
    destination_path = f'{dest_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_track_path.html'
    render_page(reportpath_version_dict, stats_path_dict, filename_path_dict, destination_path, template_path)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    parser.add_argument('stats_list_file', nargs=1, type=str)
    args = parser.parse_args()
    return args


def main():
    """main function"""
    args = parse_arg()

    dest_dir = args.report_directory[0] + '/track_path'
    stats_list_file = args.stats_list_file[0]
    _logger.info(f'dest_dir: {dest_dir}')
    _logger.info(f'stats_list_file: {stats_list_file}')
    os.makedirs(dest_dir, exist_ok=True)

    make_report(dest_dir, stats_list_file)
    print('<<< OK. report_track_path is created >>>')


if __name__ == '__main__':
    main()