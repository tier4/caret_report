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
Script to validate callback functions
"""
from typing import List, Optional, Tuple
import sys
import os
from pathlib import Path
import argparse
from distutils.util import strtobool
import logging
import re
from itertools import groupby
import csv
import yaml
import pandas as pd
from caret_analyze import Architecture, Application
from caret_analyze.runtime.node import Node
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df, get_callback_legend
from common.utils import ComponentManager
from common.utils_validation import Metrics, ResultStatus

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

# Suppress log for Bokeh "BokehUserWarning: out of range integer may result in loss of precision"
import warnings
warnings.simplefilter("ignore")

_logger: logging.Logger = None


def get_node_plot(callbacks: list[CallbackBase], metrics: Metrics):
    if metrics == Metrics.FREQUENCY:
        return Plot.create_frequency_timeseries_plot(callbacks)
    elif metrics == Metrics.PERIOD:
        return Plot.create_period_timeseries_plot(callbacks)
    elif metrics == Metrics.LATENCY:
        return Plot.create_latency_timeseries_plot(callbacks)


class Expectation():
    id = 0

    def __init__(self, component_name: str, node_name: str, callback_name: str, callback_type: CallbackType,
                 period_ns: Optional[int], topic_name: Optional[str], value: float, lower_limit: Optional[float] = None,
                 upper_limit: Optional[float] = None, ratio: Optional[float] = None, burst_num: Optional[int] = None):
        if callback_type == CallbackType.TIMER and period_ns is not None:
            pass
        elif callback_type == CallbackType.SUBSCRIPTION and topic_name is not None:
            pass
        else:
            msg = f'Invalid callback_type or parameter. callback_type: {callback_type.type_name}, period_ns: {period_ns}, topic_name: {topic_name}'
            raise Exception(msg)
        self.id = Expectation.id
        Expectation.id += 1
        self.component_name = component_name
        self.node_name = node_name
        self.callback_name = callback_name
        self.callback_type = callback_type
        self.period_ns = period_ns
        self.topic_name = topic_name
        self.value = value
        self.lower_limit = lower_limit or self.value * 0.8
        self.upper_limit = upper_limit or self.value * 1.2
        self.ratio = ratio or 0.2
        self.burst_num = burst_num or 5

    @staticmethod
    def find_expectation(expectation_list: list, callback: CallbackBase):
        for expectation in expectation_list:
            if re.search(expectation.node_name, callback.node_name) and expectation.callback_type == callback.callback_type:
                if (callback.callback_type == CallbackType.TIMER and expectation.period_ns == callback.timer.period_ns) or \
                   (callback.callback_type == CallbackType.SUBSCRIPTION and expectation.topic_name == callback.subscription.topic_name):
                    return expectation
        return None

    @staticmethod
    def _read_expectation_csv(expectation_csv_filename: str) -> List[dict]:
        if not os.path.isfile(expectation_csv_filename):
            _logger.error(f"Unable to read expectation csv: {expectation_csv_filename}")
            return []
        with open(expectation_csv_filename, 'r', encoding='utf-8') as csv_file:
            HEADERS = ['node_name', 'callback_type', 'trigger', 'value']
            expectation_csv_rows = list(csv.DictReader(csv_file, HEADERS))

        # Convert string value to float
        for idx in range(len(expectation_csv_rows)):
            try:
                expectation_csv_rows[idx]['value'] = float(expectation_csv_rows[idx]['value'])
            except ValueError:
                expectation_csv_rows[idx]['value'] = 0

        return expectation_csv_rows

    @staticmethod
    def read_frequency_expectations(expectation_csv_filename: str, component_name: Optional[str],
                                    lower_limit_scale=0.8, upper_limit_scale=1.2, ratio=0.2, burst_num=5) -> List:
        expectation_csv_rows = Expectation._read_expectation_csv(expectation_csv_filename)
        expectation_list: list[Expectation] = []
        for row in expectation_csv_rows:
            try:
                read_node_name = row['node_name']
                read_component_name = ComponentManager().get_component_name(read_node_name)
                if component_name is not None and read_component_name != component_name:
                    continue
                value = row['value']
                lower_limit_value = value * lower_limit_scale
                upper_limit_value = value * upper_limit_scale

                if row['callback_type'] == 'timer_callback':
                    expectation = Expectation(
                        read_component_name, read_node_name, '', CallbackType.TIMER, int(row['trigger']),
                        None, value, lower_limit_value, upper_limit_value, ratio, burst_num
                    )
                else:
                    expectation = Expectation(
                        read_component_name, read_node_name, '', CallbackType.SUBSCRIPTION, None,
                        row['trigger'], value, lower_limit_value, upper_limit_value, ratio, burst_num
                    )
            except Exception as e:
                _logger.error(f"Error at reading: {row} {e}")
                return None
            expectation_list.append(expectation)
        return expectation_list


class Stats():

    def __init__(self):
        self.component_name = ''
        self.node_name = ''
        self.callback_name = ''
        self.callback_symbol = ''
        self.callback_type = ''
        self.period_ns = ''
        self.subscribe_topic_name = ''
        self.metrics = ''
        self.graph_filename = ''
        self.avg = -1
        self.std = -1
        self.min = -1
        self.max = -1
        self.percentile5_min = -1
        self.percentile5_max = -1
        self.percentile5_avg = -1

    @staticmethod
    def from_df(component_name: str, node_name: str, callback: CallbackBase,
                metrics: Metrics, graph_filename: str, df_callback: pd.DataFrame):
        stats = Stats()
        stats.component_name = component_name
        stats.node_name = node_name
        stats.callback_name = callback.callback_name
        stats.callback_symbol = callback.symbol
        stats.callback_type = callback.callback_type.type_name
        stats.period_ns = callback.timer.period_ns if callback.callback_type == CallbackType.TIMER else -1
        stats.subscribe_topic_name = callback.subscribe_topic_name if callback.callback_type == CallbackType.SUBSCRIPTION else ''
        stats.metrics = metrics.name
        stats.graph_filename = graph_filename

        df_callback = df_callback.iloc[:, 1]                  # get metrics value only
        df_callback = trail_df(df_callback, end_strip_num=2)  # remove the last data because freq becomes small

        if len(df_callback) >= 2:
            stats.avg = float(df_callback.mean())
            stats.std = float(df_callback.std())
            stats.min = float(df_callback.min())
            stats.max = float(df_callback.max())
            stats.percentile5_min = float(df_callback.quantile(0.05))
            stats.percentile5_max = float(df_callback.quantile(0.95))
            df_percentile5 = df_callback[(df_callback >= stats.percentile5_min) & (df_callback <= stats.percentile5_max)]
            stats.percentile5_avg = float(df_percentile5.mean()) if len(df_percentile5) > 2 else stats.avg
        else:
            _logger.info(f'This callback is not called: {node_name}: {callback.callback_name}')
            return None, None
        return stats, df_callback

    @staticmethod
    def from_expectation(component_name: str, expectation: Expectation, metrics: Metrics):
        stats = Stats()
        stats.component_name = component_name
        stats.node_name = expectation.node_name
        stats.callback_name = expectation.callback_name
        stats.callback_type = expectation.callback_type.type_name
        stats.period_ns = expectation.period_ns if expectation.callback_type == CallbackType.TIMER else -1
        stats.subscribe_topic_name = expectation.topic_name if expectation.callback_type == CallbackType.SUBSCRIPTION else ''
        stats.metrics = metrics.name
        return stats


class Result():

    def __init__(self, stats: Stats, expectation: Optional[Expectation] = None):
        self.stats = stats
        self.result_status = ResultStatus.OUT_OF_SCOPE.name
        self.expectation_value = -1
        self.expectation_lower_limit = -1
        self.expectation_upper_limit = -1
        self.expectation_ratio = -1
        self.expectation_burst_num = -1
        self.ratio_lower_limit = -1
        self.ratio_upper_limit = -1
        self.burst_num_lower_limit = -1
        self.burst_num_upper_limit = -1
        self.result_ratio_lower_limit = ResultStatus.PASS.name
        self.result_ratio_upper_limit = ResultStatus.PASS.name
        self.result_burst_num_lower_limit = ResultStatus.PASS.name
        self.result_burst_num_upper_limit = ResultStatus.PASS.name

        if expectation:
            self.result_status = ResultStatus.NOT_MEASURED.name
            self.expectation_id = expectation.id
            self.expectation_value = expectation.value
            self.expectation_lower_limit = expectation.lower_limit
            self.expectation_upper_limit = expectation.upper_limit
            self.expectation_ratio = expectation.ratio
            self.expectation_burst_num = expectation.burst_num

    def validate(self, df_callback: pd.DataFrame, expectation: Expectation):
        if expectation.value <= 0:
            # it's not expected to be tested but don't use OUT_OF_SCOPE
            self.result_status = ResultStatus.DONT_CARE.name
            return
        if len(df_callback) >= 2:
            self.result_status = ResultStatus.PASS.name
            self.ratio_lower_limit = float((df_callback < expectation.lower_limit).sum() / len(df_callback))
            self.ratio_upper_limit = float((df_callback > expectation.upper_limit).sum() / len(df_callback))
            if self.ratio_lower_limit > expectation.ratio:
                self.result_ratio_lower_limit = ResultStatus.FAILED.name
            # if self.ratio_upper_limit > expectation.ratio:
            #     self.result_ratio_upper_limit = ResultStatus.FAILED.name

            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_callback, key=lambda x: x < expectation.lower_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_lower_limit = max(group) if len(group) > 0 else 0
            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_callback, key=lambda x: x > expectation.upper_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_upper_limit = max(group) if len(group) > 0 else 0
            if self.burst_num_lower_limit > expectation.burst_num:
                self.result_burst_num_lower_limit = ResultStatus.FAILED.name
            # if self.burst_num_upper_limit > expectation.burst_num:
            #     self.result_burst_num_upper_limit = ResultStatus.FAILED.name

        if self.result_ratio_lower_limit == ResultStatus.FAILED.name or \
           self.result_ratio_upper_limit == ResultStatus.FAILED.name or \
           self.result_burst_num_lower_limit == ResultStatus.FAILED.name or\
           self.result_burst_num_upper_limit == ResultStatus.FAILED.name:
            self.result_status = ResultStatus.FAILED.name


def create_stats_for_node(node: Node, metrics: Metrics, dest_dir: str, component_name: str, xaxis_type: str,
                          not_display_callback_list=[]) -> dict[str, Tuple[Stats, pd.DataFrame]]:
    stats_list = {}
    try:
        timeseries_plot = get_node_plot(node.callbacks, metrics)
        df_node = timeseries_plot.to_dataframe(xaxis_type=xaxis_type)
    except:
        _logger.info(f'This node is not called: {node.node_name}')
        return stats_list

    graph_filename = metrics.name + node.node_name.replace('/', '_')
    graph_filename = graph_filename[:250]
    has_valid_data = False
    for callback in node.callbacks:
        df_callback = df_node[callback.callback_name]
        stats, df = Stats.from_df(component_name, node.node_name, callback, metrics, graph_filename, df_callback)
        if stats:
            has_valid_data = True
            stats_list[callback.callback_name] = stats, df

    if has_valid_data:
        try:
            # Don't display callbacks with high frequency because it takes very long time
            callbacks = node.callbacks
            for not_display_callback in not_display_callback_list:
                if not_display_callback in node.callback_names:
                    _logger.info(f'{not_display_callback} is not displayed in graph')
                    callbacks.remove(node.get_callback(not_display_callback))
            timeseries_plot = get_node_plot(callbacks, metrics)
            figure = timeseries_plot.figure(xaxis_type=xaxis_type)  # note: this API is heavy when callback runs with high frequency
            figure.y_range.start = 0
            export_graph(figure, dest_dir, graph_filename, with_png=False, logger=_logger)
        except:
            _logger.info('Failed to export graph')

    return stats_list


def validate_callback(component_name: str, target_node_list: list[Node], metrics: Metrics, dest_dir: str,
                      xaxis_type: str, expectation_list: List[Expectation] = [], not_display_callback_list=[]) -> list[Result]:
    expectation_validated_list = expectation_list.copy()   # keep original because there may be multiple callbacks with the same parameters in a node
    result_info_list: list[Result] = []
    for node in target_node_list:
        _logger.debug(f'Processing ({metrics.name}): {node.node_name}')
        stats_list = create_stats_for_node(node, metrics, dest_dir, component_name, xaxis_type, not_display_callback_list)

        for callback in node.callbacks:
            if callback.callback_name not in stats_list:
                # Not measured
                continue
            # Measured
            expectation = Expectation.find_expectation(expectation_list, callback)
            stats = stats_list[callback.callback_name][0]
            df_callback = stats_list[callback.callback_name][1]
            result = Result(stats, expectation)
            if expectation:
                # Measured and to be validated
                result.validate(df_callback, expectation)
                if expectation in expectation_validated_list:
                    expectation_validated_list.remove(expectation)
            result_info_list.append(result)

    for expectation in expectation_validated_list:
        if expectation.value > 0:
            # Not measured but should be validated
            result = Result(Stats.from_expectation(component_name, expectation, metrics), expectation)
            result_info_list.append(result)
    return result_info_list


def save_stats(app: Application, result_list: list[Result], component_name: str, dest_dir: str, metrics_str: str):
    result_var_list = []
    for result in result_list:
        if result.stats.node_name in app.node_names:
            callback_legend = get_callback_legend(app.get_node(result.stats.node_name), result.stats.callback_name, False)
        else:
            _logger.warning(f'Failed to get legend name. {result.stats.node_name}, {result.stats.callback_name}')
            callback_legend = result.stats.callback_name
        result.stats = vars(result.stats)
        result.stats['callback_legend'] = callback_legend
        result_var_list.append(vars(result))
    result_var_list.sort(key=lambda x: x['stats']['node_name'])
    result_var_list.sort(key=lambda x: x['expectation_id'] if 'expectation_id' in x else 9999)
    result_file_path = f'{dest_dir}/stats_{metrics_str}.yaml'
    with open(result_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(result_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


def validate_component(app: Application, component_name: str, dest_dir: str, force: bool, expectation_csv_filename: str, xaxis_type: str):
    """Validate callback for each component"""
    dest_dir = f'{dest_dir}/validate_callback/{component_name}'
    make_destination_dir(dest_dir, force, _logger)

    target_node_list: list[Node] = []
    for node in app.nodes:
        if ComponentManager().check_if_target(component_name, node.node_name):
            target_node_list.append(node)

    # validate callback frequency
    expectation_list = Expectation.read_frequency_expectations(expectation_csv_filename, component_name)
    result_list = validate_callback(component_name, target_node_list, Metrics.FREQUENCY, dest_dir, xaxis_type,
                                    expectation_list=expectation_list)
    save_stats(app, result_list, component_name, dest_dir, Metrics.FREQUENCY.name)

    # callbacks with high frequency is not displayed
    THRESHOLD_FREQ_NOT_DISPLAY = 200
    not_display_callback_list = []
    for result in result_list:
        average_freq = result.stats['avg']
        is_numeric = isinstance(average_freq, int) or isinstance(average_freq, float)
        if is_numeric and average_freq >= THRESHOLD_FREQ_NOT_DISPLAY:
            not_display_callback_list.append(result.stats['callback_name'])

    # validate callback period
    result_list = validate_callback(component_name, target_node_list, Metrics.PERIOD, dest_dir, xaxis_type,
                                    not_display_callback_list=not_display_callback_list)
    save_stats(app, result_list, component_name, dest_dir, Metrics.PERIOD.name)

    # validate callback latency
    result_list = validate_callback(component_name, target_node_list, Metrics.LATENCY, dest_dir, xaxis_type,
                                    not_display_callback_list=not_display_callback_list)
    save_stats(app, result_list, component_name, dest_dir, Metrics.LATENCY.name)


def validate(verbose, arch: Architecture, app: Application, dest_dir: str, force: bool,
             component_list_json: str, expectation_csv_filename: str, xaxis_type: str):
    """Validate callback"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if verbose else logging.INFO)

    _logger.info('<<< Validate callback start >>>')

    make_destination_dir(dest_dir + '/validate_callback', force, _logger)
    arch.export(dest_dir + '/architecture.yaml', force=True)
    ComponentManager().initialize(component_list_json, _logger)

    for component_name, _ in ComponentManager().component_dict.items():
        validate_component(app, component_name, dest_dir, force, expectation_csv_filename, xaxis_type)

    _logger.info('<<< Validate callback finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--report_directory', type=str, default='')
    parser.add_argument('--component_list_json', type=str, default='component_list.json')
    parser.add_argument('--expectation_csv_filename', type=str, default='expectation_callback.csv')
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
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'expectation_csv_filename: {args.expectation_csv_filename}')
    _logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    _logger.debug(f'sim_time: {args.sim_time}')
    dest_dir = args.report_directory if args.report_directory != '' else f'val_{Path(args.trace_data[0]).stem}'
    _logger.debug(f'dest_dir: {dest_dir}')
    xaxis_type = 'sim_time' if args.sim_time else 'system_time'

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    validate(args.verbose, arch, app, dest_dir, args.force, args.component_list_json, args.expectation_csv_filename, xaxis_type)


if __name__ == '__main__':
    main()
