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
from distutils.util import strtobool
import logging
import math
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import figure
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.node import Node
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df
from common.utils import round_yaml, get_callback_legend
from common.utils import ComponentManager

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

# Suppress log for Bokeh "BokehUserWarning: out of range integer may result in loss of precision"
import warnings
warnings.simplefilter("ignore")

_logger: logging.Logger = None


class StatsCallback():
    """Statistics of callback"""
    def __init__(self):
        self.avg = '---'
        self.std = '---'
        self.min = '---'
        self.max = '---'
        self.p50 = '---'
        self.p95 = '---'
        self.p99 = '---'
        self.filename_hist = ''

    def calculate(self, data: pd.DataFrame):
        """Calculate stats"""
        if len(data) > 1:
            self.avg = round(float(data.mean()), 3)
            self.std = round(float(data.std()), 3)
            self.p50 = round(float(np.quantile(data, 0.5)), 3)
            self.p95 = round(float(np.quantile(data, 0.95)), 3)
            self.p99 = round(float(np.quantile(data, 0.99)), 3)
        if len(data) > 0:
            self.min = round(float(data.min()), 3)
            self.max = round(float(data.max()), 3)

    def set_filename_hist(self, filename_hist: str):
        self.filename_hist = filename_hist


class StatsNode():
    """Statistics of node"""
    def __init__(self):
        self.filename_timeseries = {}
        self.callbacks = {}

    def set_filename_timeseries(self, metrics: str, filename_timeseries: str):
        self.filename_timeseries[metrics] = filename_timeseries

    def set_callback(self, callback: CallbackBase, callback_legend: str, metrics: str,
                     callback_stats: StatsCallback):
        self.callbacks.setdefault(callback.callback_name, {})
        self.callbacks[callback.callback_name]['callback_legend'] = callback_legend
        self.callbacks[callback.callback_name]['callback_symbol'] = callback.symbol
        self.callbacks[callback.callback_name]['callback_type'] = callback.callback_type.type_name
        self.callbacks[callback.callback_name]['period_ns'] = callback.timer.period_ns if callback.callback_type == CallbackType.TIMER else -1
        self.callbacks[callback.callback_name]['subscribe_topic_name'] = callback.subscribe_topic_name if callback.callback_type == CallbackType.SUBSCRIPTION else ''
        self.callbacks[callback.callback_name][metrics] = vars(callback_stats)


def analyze_callback(df_callback: pd.DataFrame, node: Node, callback_name: str,
                     metrics: str, dest_dir_path: str, method_hist, xaxis_type: str):
    """Analyze a callback"""
    callback_stats = StatsCallback()
    callback_stats.calculate(df_callback)
    if len(df_callback) > 0:
        callback = node.get_callback(callback_name)
        fig_hist = method_hist(callback).figure(xaxis_type=xaxis_type)
        fig_hist.height = 350
        fig_hist.width = 600
        fig_hist.legend.visible = False
        fig_hist.title = get_callback_legend(node, callback_name)
        filename_hist = f"{metrics}{callback.callback_name.replace('/', '_')}_hist"[:250]
        export_graph(fig_hist, dest_dir_path, filename_hist, with_png=False, logger=_logger)
        callback_stats.set_filename_hist(filename_hist)

    return callback_stats


def analyze_node(node: Node, dest_dir: str, xaxis_type: str, threshold_freq_not_display: int=200) -> dict:
    """Analyze a node"""
    _logger.info(f'Processing {node.node_name}')
    all_metrics_dict = {'Frequency':(Plot.create_frequency_timeseries_plot, Plot.create_frequency_histogram_plot),
                        'Period': (Plot.create_period_timeseries_plot, Plot.create_period_histogram_plot),
                        'Latency': (Plot.create_latency_timeseries_plot, Plot.create_latency_histogram_plot)}
    node_stats = StatsNode()

    callbacks_for_graph = node.callbacks  # callbacks with high frequency is not displayed
    for metrics, method in all_metrics_dict.items():
        try:
            p_timeseries = method[0](node.callbacks)
            measurement = p_timeseries.to_dataframe(xaxis_type=xaxis_type)
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

            df_callback = trail_df(df_callback, end_strip_num=2, start_strip_num=1)
            if len(df_callback) > 0:
                has_valid_data = True
            callback_stats = analyze_callback(df_callback, node, callback_name, metrics, dest_dir, method[1], xaxis_type)
            node_stats.set_callback(node.get_callback(callback_name), get_callback_legend(node, callback_name, False),
                                    metrics, callback_stats)
            if metrics == 'Frequency':
                freq = callback_stats.avg
                if isinstance(freq, int) or isinstance(freq, float):
                    if freq >= threshold_freq_not_display:
                        _logger.info(f'{callback_name} is not displayed in graph')
                        callbacks_for_graph.remove(node.get_callback(callback_name))

        if has_valid_data:
            try:
                if metrics != 'Frequency':
                    p_timeseries = method[0](callbacks_for_graph)
                fig_timeseries = p_timeseries.figure(xaxis_type=xaxis_type)  # note: this API is heavy when callback runs with high frequency
                fig_timeseries.y_range.start = 0
                filename_timeseries = metrics + node.node_name.replace('/', '_')[:250]
                export_graph(fig_timeseries, dest_dir, filename_timeseries, with_png=False, logger=_logger)
                node_stats.set_filename_timeseries(metrics, filename_timeseries)
            except:
                _logger.info(f'Failed to export graph')

    return node_stats


def analyze_component(node_list: list[Node], dest_dir: str, xaxis_type: str):
    """Analyze a component"""
    make_destination_dir(dest_dir, False, _logger)

    stats = {}
    for node in node_list:
        node_stats = analyze_node(node, dest_dir, xaxis_type)
        if node_stats:
            stats[node.node_name] = vars(node_stats)

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
        if node_name in app.node_names:
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
        analyze_component(node_list, f'{dest_dir}/{component_name}', 'sim_time' if args.sim_time else 'system_time')

    _logger.info('<<< Analyze Nodes: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--start_strip', type=float, default=0.0,
                        help='Start strip [sec] to load trace data')
    parser.add_argument('--end_strip', type=float, default=0.0,
                        help='End strip [sec] to load trace data')
    parser.add_argument('--sim_time', type=strtobool, default=False)
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
    _logger.debug(f'dest_dir: {args.dest_dir[0]}')
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    _logger.debug(f'sim_time: {args.sim_time}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    dest_dir = args.dest_dir[0]
    analyze(args, lttng, arch, app, dest_dir + '/analyze_node')


if __name__ == '__main__':
    main()
