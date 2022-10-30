# Copyright 2022 Tier IV, Inc.
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
Script to analyze node callback functions
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import argparse
import logging
import re
import math
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import Figure, figure
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.node import Node
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common import utils

_logger: logging.Logger = None


def calculate_stats(data: pd.DataFrame) -> dict:
    """Calculate stats"""
    stats = {
        'avg': '-',
        'min': '-',
        'max': '-',
        'std': '-',
    }
    if len(data) > 1:
        stats['avg'] = float(data.mean())
        stats['std'] = float(data.std())
    if len(data) > 0:
        stats['min'] = float(data.min())
        stats['max'] = float(data.max())
    return stats


def draw_histogram(data: pd.DataFrame, title: str, metrics_str: str) -> Figure:
    """Draw histogram graph"""
    def _to_histogram(data: pd.DataFrame, binsize: int, density: bool):
        binsize = max(1, binsize)
        range_min = math.floor(min(data) / binsize) * binsize
        range_max = math.ceil(max(data) / binsize) * binsize + binsize
        bin_num = math.ceil((range_max - range_min) / binsize)
        return np.histogram(
            data, bins=bin_num, range=(range_min, range_max), density=density)

    if len(data) == 0:
        _logger.info(f'len = 0: {title}')
        return None
    hist, bin_edges = _to_histogram(data, (max(data) - min(data)) / 30, False)
    figure_hist = figure(plot_width=600, plot_height=400, active_scroll='wheel_zoom', title=title,
                         x_axis_label=metrics_str, y_axis_label='Count')
    figure_hist.quad(top=hist, bottom=0, left=bin_edges[:-1], right=bin_edges[1:],
                     line_color='white', alpha=0.5)
    return figure_hist


def analyze_callback(callback_name: str, callback_displayname: str, metrics_str: str,
                     data: pd.DataFrame, metrics: str, dest_dir_path: str):
    """Analyze a callback"""
    callback_stats = calculate_stats(data)
    figure_hist = draw_histogram(data, callback_displayname, metrics_str)
    if figure_hist:
        filename_hist = f"{metrics}{callback_name.replace('/', '_')}_hist"[:250]
        utils.export_graph(figure_hist, dest_dir_path, filename_hist, _logger)
        callback_stats['filename_hist'] = filename_hist
    else:
        callback_stats['filename_hist'] = ''
    return callback_stats


def analyze_node(node: Node, dest_dir: str) -> dict:
    """Analyze a node"""
    all_metrics_dict = {'Frequency': Plot.create_callback_frequency_plot,
                        'Period': Plot.create_callback_period_plot,
                        'Latency': Plot.create_callback_latency_plot}
    node_stats = {}
    node_stats['filename_timeseries'] = {}
    node_stats['callbacks'] = {}

    for metrics, method in all_metrics_dict.items():
        p_timeseries = method(node.callbacks)
        filename_timeseries = metrics + node.node_name.replace('/', '_')[:250]
        try:
            measurement = p_timeseries.to_dataframe()
            p_timeseries = p_timeseries.show(export_path='dummy.html')
            p_timeseries.frame_width = 1000
            p_timeseries.frame_height = 350
            p_timeseries.y_range.start = 0
            utils.export_graph(p_timeseries, dest_dir, filename_timeseries, _logger)
            node_stats['filename_timeseries'][metrics] = filename_timeseries
        except:
            _logger.info(f'This node is not called: {node.node_name}')
            return None

        for key, value in measurement.items():
            callback_name = key[0]
            metrics_str = key[1]
            if 'callback_start_timestamp' in metrics_str:
                continue
            callback_displayname = callback_name.split('/')[-1] + ': '
            callback_displayname += utils.make_callback_displayname(node.get_callback(callback_name))
            data = value.dropna()
            data = data.iloc[:-2]    # remove the last data because freq becomes small
            callback_stats = analyze_callback(callback_name, callback_displayname,
                                              metrics_str, data, metrics, dest_dir)
            node_stats['callbacks'].setdefault(callback_name, {})
            node_stats['callbacks'][callback_name][metrics] = callback_stats
            node_stats['callbacks'][callback_name]['displayname'] = callback_displayname

    return node_stats


def analyze_package(node_list: list[Node], dest_dir: str):
    """Analyze a package"""
    utils.make_destination_dir(dest_dir, False, _logger)

    stats = {}
    for node in node_list:
        node_stats = analyze_node(node, dest_dir)
        if node_stats:
            stats[node.node_name] = node_stats

    stat_file_path = f"{dest_dir}/stats_node.yaml"
    with open(stat_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


def get_node_list(lttng: Lttng, app: Application,
                  prefix_regexp: dict, ignore_list: list[str]) -> list[Node]:
    """Get node list"""
    target_node_name_list = []
    for node in lttng.get_nodes():
        node_name = node.node_name
        if re.search(prefix_regexp, node_name):
            is_match = True
            for ignore in ignore_list:
                if re.search(ignore, node_name):
                    is_match = False
                    break
            if is_match:
                target_node_name_list.append(node_name)
    target_node_name_list.sort()
    node_list = []
    for node_name in target_node_name_list:
        node_list.append(app.get_node(node_name))

    return node_list


def analyze(args, lttng: Lttng, arch: Architecture, app: Application, dest_dir: str):
    """Analyze nodes"""
    global _logger
    if _logger is None:
        _logger = utils.create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Nodes: Start >>>')
    utils.make_destination_dir(dest_dir, args.force, _logger)
    arch.export(dest_dir + '/architecture.yaml', force=True)
    package_dict, ignore_list = utils.make_package_list(args.package_list_json, _logger)

    for package_name, regexp in package_dict.items():
        node_list = get_node_list(lttng, app, regexp, ignore_list)
        analyze_package(node_list, f'{dest_dir}/{package_name}')

    _logger.info('<<< Analyze Nodes: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--package_list_json', type=str, default='')
    parser.add_argument('-s', '--start_point', type=float, default=0.0,
                        help='Start point[sec] to load trace data')
    parser.add_argument('-d', '--duration', type=float, default=0.0,
                        help='Duration[sec] to load trace data')
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='Overwrite report directory')
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    global _logger
    args = parse_arg()
    _logger = utils.create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'package_list_json: {args.package_list_json}')
    _logger.debug(f'start_point: {args.start_point}, duration: {args.duration}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    _logger.debug(f'dest_dir: {dest_dir}')

    lttng = utils.read_trace_data(args.trace_data[0], args.start_point, args.duration, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    analyze(args, lttng, arch, app, dest_dir + '/node')


if __name__ == '__main__':
    main()
