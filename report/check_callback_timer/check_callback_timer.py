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
Script to check gap b/w timer frequency and callback function wake-up frequency
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import argparse
import logging
import statistics
import yaml
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.callback import CallbackBase
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph
from common.utils import get_callback_legend, round_yaml
from common.utils import ComponentManager

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def create_stats(app: Application, callback: CallbackBase, freq_timer,
                 freq_callback, num_huge_gap, graph_filename) -> dict:
    """Create stats"""
    stats = {
        'node_name': callback.node_name,
        'component_name': ComponentManager().get_component_name(callback.node_name),
        'callback_name': callback.callback_name,
        'callback_displayname': get_callback_legend(app.get_node(callback.node_name), callback.callback_name),
        'freq_timer': freq_timer,
        'freq_callback': freq_callback,
        'num_huge_gap': num_huge_gap,
        'graph_filename': graph_filename
    }
    return stats


def analyze_callback(args, dest_dir, app: Application, callback: CallbackBase) -> tuple(dict, bool):
    """Analyze a timer callback function"""
    _logger.debug(f'Processing: {callback.callback_name}')
    freq_timer = 1e9 / float(callback.timer.period_ns)
    freq_threshold = freq_timer * (1 - args.gap_threshold_ratio)

    try:
        p_timeseries = Plot.create_frequency_timeseries_plot([callback])
        figure = p_timeseries.figure()
    except:
        _logger.warning(f'This callback is not called: {callback.callback_name}')
        return None, False
    figure.y_range.start = 0
    graph_filename = callback.callback_name.replace("/", "_")[1:]
    graph_filename = graph_filename[:250]

    measurement = p_timeseries.to_dataframe().dropna()
    freq_callback_list = measurement.iloc[:, 1]
    freq_callback_list = freq_callback_list[freq_callback_list != 0]    # Ignore data when the node is not running
    freq_callback_list = freq_callback_list.iloc[1:-2]  # remove the first and last data because freq becomes small
    if len(freq_callback_list) < 2:
        _logger.warning(f'Not enough data: {callback.callback_name}')
        return None, False
    freq_callback_avg = round(float(statistics.mean(freq_callback_list)), 3)
    num_huge_gap = int(sum(freq_callback <= freq_threshold for freq_callback in freq_callback_list))

    export_graph(figure, dest_dir, graph_filename, _logger)
    stats = create_stats(app, callback, freq_timer, freq_callback_avg, num_huge_gap, graph_filename)

    is_warning = False
    if num_huge_gap >= args.count_threshold:
        is_warning = True
    return stats, is_warning


def analyze(args, lttng: Lttng, arch: Architecture, app: Application, dest_dir: str):
    """Analyze Timer Callbacks"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Timer Callbacks: Start >>>')
    make_destination_dir(dest_dir, args.force, _logger)
    ComponentManager().initialize(args.component_list_json, _logger)

    stats_all_list = []
    stats_warning_list = []

    callbacks = app.callbacks
    for callback in callbacks:
        if ComponentManager().check_if_ignore(callback.callback_name):
            continue
        if 'timer_callback' == callback.callback_type.type_name:
            stats, is_warning = analyze_callback(args, dest_dir, app, callback)
            if stats:
                stats_all_list.append(stats)
            if is_warning:
                stats_warning_list.append(stats)

    stats_all_list = sorted(stats_all_list, key=lambda x: x['callback_name'])
    stats_warning_list = sorted(stats_warning_list, key=lambda x: x['callback_name'])

    with open(f'{dest_dir}/stats_callback_timer.yaml', 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats_all_list, f_yaml, encoding='utf-8',
                       allow_unicode=True, sort_keys=False)
    round_yaml(f'{dest_dir}/stats_callback_timer.yaml')
    with open(f'{dest_dir}/stats_callback_timer_warning.yaml', 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats_warning_list, f_yaml, encoding='utf-8',
                       allow_unicode=True, sort_keys=False)
    round_yaml(f'{dest_dir}/stats_callback_timer_warning.yaml')

    _logger.info('<<< Analyze Timer Callbacks: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to check gap b/w timer frequency and callback function wake-up frequency')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--start_strip', type=float, default=0.0,
                        help='Start strip [sec] to load trace data')
    parser.add_argument('--end_strip', type=float, default=0.0,
                        help='End strip [sec] to load trace data')
    parser.add_argument('-r', '--gap_threshold_ratio', type=float, default=0.2,
                        help='Warning when callback_freq is less than "gap_threshold_ratio" * timer_period for "count_threshold" times')
    parser.add_argument('-n', '--count_threshold', type=int, default=10,
                        help='Warning when callback_freq is less than "gap_threshold_ratio" * timer_period for "count_threshold" times')
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='Overwrite report directory')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    global _logger
    args = parse_arg()
    _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    _logger.debug(f'dest_dir: {dest_dir}')
    _logger.debug(f'gap_threshold_ratio: {args.gap_threshold_ratio}')
    _logger.debug(f'count_threshold: {args.count_threshold}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    analyze(args, lttng, arch, app, dest_dir + '/check_callback_timer')


if __name__ == '__main__':
    main()
