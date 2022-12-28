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
import math
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import Figure, figure
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.node import Node
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df
from common.utils import make_callback_displayname, round_yaml
from common.utils import ComponentManager

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

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
        stats['avg'] = round(float(data.mean()), 3)
        stats['std'] = round(float(data.std()), 3)
    if len(data) > 0:
        stats['min'] = round(float(data.min()), 3)
        stats['max'] = round(float(data.max()), 3)
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
        export_graph(figure_hist, dest_dir_path, filename_hist, _logger)
        callback_stats['filename_hist'] = filename_hist
    else:
        callback_stats['filename_hist'] = ''
    return callback_stats


def analyze_node(node: Node, dest_dir: str) -> dict:
    """Analyze a node"""
    all_metrics_dict = {'Frequency': Plot.create_frequency_timeseries_plot,
                        'Period': Plot.create_period_timeseries_plot,
                        'Latency': Plot.create_latency_timeseries_plot}
    node_stats = {}
    node_stats['filename_timeseries'] = {}
    node_stats['callbacks'] = {}

    for metrics, method in all_metrics_dict.items():
        try:
            p_timeseries = method(node.callbacks)
            measurement = p_timeseries.to_dataframe()
        except:
            _logger.info(f'This node is not called: {node.node_name}')
            return None

        has_valid_data = False
        for key, value in measurement.items():
            callback_name = key[0]
            metrics_str = key[1]
            df_callback = value
            if 'callback_start_timestamp' in metrics_str:
                continue
            callback_displayname = callback_name.split('/')[-1] + ': '
            callback_displayname += make_callback_displayname(node.get_callback(callback_name))
            df_callback = trail_df(df_callback, end_strip_num=2, start_strip_num=1)
            if len(df_callback) > 0:
                has_valid_data = True
            callback_stats = analyze_callback(callback_name, callback_displayname,
                                              metrics_str, df_callback, metrics, dest_dir)
            node_stats['callbacks'].setdefault(callback_name, {})
            node_stats['callbacks'][callback_name][metrics] = callback_stats
            node_stats['callbacks'][callback_name]['displayname'] = callback_displayname

        if has_valid_data:
            try:
                p_timeseries = p_timeseries.figure()
                p_timeseries.frame_width = 1000
                p_timeseries.frame_height = 350
                p_timeseries.y_range.start = 0
                filename_timeseries = metrics + node.node_name.replace('/', '_')[:250]
                export_graph(p_timeseries, dest_dir, filename_timeseries, _logger)
                node_stats['filename_timeseries'][metrics] = filename_timeseries
            except:
                _logger.info(f'Failed to export graph')

    return node_stats


def analyze_component(node_list: list[Node], dest_dir: str):
    """Analyze a component"""
    make_destination_dir(dest_dir, False, _logger)

    stats = {}
    for node in node_list:
        node_stats = analyze_node(node, dest_dir)
        if node_stats:
            stats[node.node_name] = node_stats

    stat_file_path = f"{dest_dir}/stats_node.yaml"
    with open(stat_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)
    round_yaml(stat_file_path)


def get_node_list(lttng: Lttng, app: Application, component_name: str) -> list[Node]:
    """Get node list"""
    target_node_name_list = []
    for node in lttng.get_nodes():
        node_name = node.node_name
        if ComponentManager().check_if_target(component_name, node_name):
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
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Nodes: Start >>>')
    make_destination_dir(dest_dir, args.force, _logger)
    arch.export(dest_dir + '/architecture.yaml', force=True)
    ComponentManager().initialize(args.component_list_json, _logger)

    for component_name, _ in ComponentManager().component_dict.items():
        node_list = get_node_list(lttng, app, component_name)
        analyze_component(node_list, f'{dest_dir}/{component_name}')

    _logger.info('<<< Analyze Nodes: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
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
    _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'start_point: {args.start_point}, duration: {args.duration}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    _logger.debug(f'dest_dir: {dest_dir}')

    lttng = read_trace_data(args.trace_data[0], args.start_point, args.duration, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    analyze(args, lttng, arch, app, dest_dir + '/node')


if __name__ == '__main__':
    main()
