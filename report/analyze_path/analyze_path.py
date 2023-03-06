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
Script to analyze path
"""
from __future__ import annotations
import sys
import os
import datetime
import pathlib
import shutil
import argparse
from distutils.util import strtobool
import logging
import yaml
import numpy as np
from bokeh.plotting import Figure, figure
from bokeh.models import AdaptiveTicker
from caret_analyze.record import RecordsInterface
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.experiment import ResponseTime
from caret_analyze.plot import message_flow
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, round_yaml

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


class Stats():
    def __init__(self, target_path_name: str, node_names: list[str]):
        self.target_path_name = target_path_name
        self.node_names = node_names
        self.best_avg = '---'
        self.best_min = '---'
        self.best_max = '---'
        self.best_p50 = '---'
        self.best_p95 = '---'
        self.best_p99 = '---'
        self.worst_avg = '---'
        self.worst_min = '---'
        self.worst_max = '---'
        self.worst_p50 = '---'
        self.worst_p95 = '---'
        self.worst_p99 = '---'
        self.filename_messageflow = ''
        self.filename_messageflow_short = ''
        self.filename_hist_total = ''
        self.filename_hist_best = ''
        self.filename_timeseries_best = ''
        self.filename_hist_worst = ''
        self.filename_timeseries_worst = ''

    def calc_stats(self, df_best: np.ndarray, df_worst: np.ndarray):
        self.best_avg = round(float(np.average(df_best)), 3)
        self.best_min = round(float(np.min(df_best)), 3)
        self.best_max = round(float(np.max(df_best)), 3)
        self.best_p50 = round(float(np.quantile(df_best, 0.5)), 3)
        self.best_p95 = round(float(np.quantile(df_best, 0.95)), 3)
        self.best_p99 = round(float(np.quantile(df_best, 0.99)), 3)
        self.worst_avg = round(float(np.average(df_worst)), 3)
        self.worst_min = round(float(np.min(df_worst)), 3)
        self.worst_max = round(float(np.max(df_worst)), 3)
        self.worst_p50 = round(float(np.quantile(df_worst, 0.5)), 3)
        self.worst_p95 = round(float(np.quantile(df_worst, 0.95)), 3)
        self.worst_p99 = round(float(np.quantile(df_worst, 0.99)), 3)

    def store_filename(self, target_path_name: str, save_long_graph: bool):
        if save_long_graph:
            self.filename_messageflow = f'{target_path_name}_messageflow'
        self.filename_messageflow_short = f'{target_path_name}_messageflow_short'
        self.filename_hist_best = f'{target_path_name}_hist_best'
        self.filename_timeseries_best = f'{target_path_name}_timeseries_best'
        self.filename_hist_worst = f'{target_path_name}_hist_worst'
        self.filename_timeseries_worst = f'{target_path_name}_timeseries_worst'


def align_timeseries(timeseries: tuple[np.ndarray, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Adjust timeseries graph"""
    x_list = np.zeros(len(timeseries[0]), dtype='float')
    y_list = np.zeros(len(timeseries[1]), dtype='float')
    offset = timeseries[0][0]
    for i in range(len(timeseries[0])):
        x_list[i] = (timeseries[0][i] - offset) * 10**-9  # [sec]
        y_list[i] = timeseries[1][i] * 10**-6  # [msec]
    return x_list, y_list


def draw_response_time(hist: np.ndarray, bin_edges: np.ndarray,
                       timeseries: tuple[np.ndarray, np.ndarray], offset) -> tuple[Figure, Figure]:
    """Draw histogram and timeseries graphs of response time"""
    bin_edges = bin_edges * 10**-6  # nanoseconds to milliseconds
    p_hist = figure(plot_width=600, plot_height=400, active_scroll='wheel_zoom',
                    x_axis_label='Response Time [ms]', y_axis_label='Frequency')
    p_hist.quad(top=hist, bottom=0, left=bin_edges[:-1], right=bin_edges[1:],
                line_color='white', alpha=0.5)

    p_timeseries = None
    if timeseries:
        p_timeseries = figure(plot_width=600, plot_height=400, active_scroll='wheel_zoom',
                       x_axis_label='Time [sec]', y_axis_label='Response Time [ms]')
        p_timeseries.y_range.start = 0
        p_timeseries.line(x=timeseries[0], y=timeseries[1])
        datetime_s = datetime.datetime.fromtimestamp(offset*10**-9).strftime('%Y-%m-%d %H:%M:%S')
        p_timeseries.xaxis.major_label_overrides = {0: datetime_s}
        ticker = AdaptiveTicker(min_interval=0.1, mantissas=[1, 2, 5])
        p_timeseries.xaxis.ticker = ticker

    return p_hist, p_timeseries


def get_messageflow_durationtime(records: RecordsInterface):
    """Get duration time [sec] of message flow"""
    input_column = records.columns[0]
    output_column = records.columns[-1]

    input_time_min = None
    output_time_max = None

    # Need to check all records because some paths may not be fully connected
    data_list = records.data
    for data in data_list:
        if input_column in data.columns:
            input_time = data.get(input_column)
            input_time_min = min(input_time, input_time_min) if input_time_min else input_time
        if output_column in data.columns:
            output_time = data.get(output_column)
            output_time_max = max(output_time, output_time_max) if output_time_max else output_time

    if input_time_min is None or output_time_max is None:
        duration = None
    else:
        duration = (output_time_max - input_time_min) / 1e9

    return duration


def analyze_path(args, dest_dir: str, arch: Architecture, app: Application, target_path_name: str):
    """Analyze a path"""
    _logger.info(f'Processing: {target_path_name}')
    target_path = app.get_path(target_path_name)
    stats = Stats(target_path_name, arch.get_path(target_path_name).node_names)

    records = target_path.to_records()
    duration = get_messageflow_durationtime(records)
    if duration is None:
        _logger.warning(f'    There are no-traffic communications: {target_path_name}')
        return stats

    _logger.info('  Call message_flow')
    graph_short = message_flow(target_path, granularity='node', treat_drop_as_delay=False,
                lstrip_s=duration / 2,
                rstrip_s=max(duration / 2 - (3 + 0.1), 0),
                export_path='dummy.html')

    graph_short.width = 1400
    graph_short.height = 15 * len(target_path.child_names) + 50
    export_graph(graph_short, dest_dir, f'{target_path_name}_messageflow_short', target_path_name)

    if args.message_flow:
        graph = message_flow(target_path, granularity='node',
                             treat_drop_as_delay=False, export_path='dummy.html')
        graph.width = graph_short.width
        graph.height = graph_short.height
        export_graph(graph, dest_dir, f'{target_path_name}_messageflow', target_path_name)

    _logger.info('  Call ResponseTime')
    response_time = ResponseTime(records)

    _logger.debug('    Draw histogram and timeseries (best)')
    hist, bin_edges = response_time.to_best_case_histogram(10**7)  # binsize = 10ms
    df_best = response_time.to_best_case_timeseries()
    offset = df_best[0][0]
    df_best = align_timeseries(df_best)
    p_hist, p_timeseries = draw_response_time(hist, bin_edges, df_best, offset)
    export_graph(p_hist, dest_dir, target_path_name + '_hist_best', target_path_name)
    export_graph(p_timeseries, dest_dir, target_path_name + '_timeseries_best', target_path_name)

    _logger.debug('    Draw histogram and timeseries (worst)')
    hist, bin_edges = response_time.to_worst_case_histogram(10**7)  # binsize = 10ms
    df_worst = response_time.to_worst_case_timeseries()
    offset = df_worst[0][0]
    df_worst = align_timeseries(df_worst)
    p_hist, p_timeseries = draw_response_time(hist, bin_edges, df_worst, offset)
    export_graph(p_hist, dest_dir, target_path_name + '_hist_worst', target_path_name)
    export_graph(p_timeseries, dest_dir, target_path_name + '_timeseries_worst', target_path_name)

    stats.calc_stats(df_best[1], df_worst[1])
    stats.store_filename(target_path_name, args.message_flow)
    _logger.info(f'---{target_path_name}---')
    _logger.debug(vars(stats))

    return stats


def analyze(args, lttng: Lttng, arch: Architecture, app: Application, dest_dir: str):
    """Analyze paths"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Paths: Start >>>')
    make_destination_dir(dest_dir, args.force, _logger)
    shutil.copy(args.architecture_file_path, dest_dir)

    stats_list = []

    # Verify each path
    for target_path in arch.paths:
        target_path_name = target_path.path_name
        path = arch.get_path(target_path_name)
        ret_verify = path.verify()
        _logger.info(f'path.verify {target_path_name}: {ret_verify}')
        if not ret_verify:
            sys.exit(-1)

    # Analyze each path
    for target_path in arch.paths:
        target_path_name = target_path.path_name
        stats = analyze_path(args, dest_dir, arch, app, target_path_name)
        stats_list.append(vars(stats))

    # Save stats file
    stat_file_path = f'{dest_dir}/stats_path.yaml'
    with open(stat_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)
    round_yaml(stat_file_path)

    _logger.info('<<< Analyze Paths: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze path')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--architecture_file_path', type=str, default='architecture_path.yaml')
    parser.add_argument('-m', '--message_flow', type=strtobool, default=False,
                        help='Output message flow graph')
    parser.add_argument('--start_strip', type=float, default=0.0,
                        help='Start strip [sec] to load trace data')
    parser.add_argument('--end_strip', type=float, default=0.0,
                        help='End strip [sec] to load trace data')
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
    _logger.debug(f'architecture_file_path: {args.architecture_file_path}')
    _logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    args.message_flow = True if args.message_flow == 1 else False
    _logger.debug(f'message_flow: {args.message_flow}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('yaml', args.architecture_file_path)
    app = Application(arch, lttng)

    dest_dir = args.dest_dir[0]
    analyze(args, lttng, arch, app, dest_dir + '/analyze_path')


if __name__ == '__main__':
    main()
