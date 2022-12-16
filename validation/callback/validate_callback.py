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
from typing import Callable, DefaultDict, Dict, List, Optional, Set, Tuple, Union, Type
import sys
import os
from pathlib import Path
import argparse
import logging
from itertools import groupby
import csv
import yaml
import numpy as np
import pandas as pd
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.node import Node
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df
from common.utils import Metrics, ResultStatus, ComponentManager

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def get_node_plot(node: Node, metrics: Metrics):
    if metrics == Metrics.FREQUENCY:
        return Plot.create_callback_frequency_plot(node.callbacks)
    elif metrics == Metrics.PERIOD:
        return Plot.create_callback_period_plot(node.callbacks)
    elif metrics == Metrics.LATENCY:
        return Plot.create_callback_latency_plot(node.callbacks)


class Expectation():
    id = 0
    def __init__(self,
        component_name: str, node_name: str, callback_name: str, callback_type: CallbackType, period_ns: Optional[int], topic_name: Optional[str],
        value: float, lower_limit: Optional[float] = None, upper_limit: Optional[float] = None, ratio: Optional[float] = None, burst_num: Optional[int] = None):
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
        self.burst_num = burst_num or 2

    @staticmethod
    def find_expectation(expectation_list: list, callback: CallbackBase):
        for expectation in expectation_list:
            if expectation.node_name == callback.node_name and expectation.callback_type == callback.callback_type:
                if (callback.callback_type == CallbackType.TIMER and expectation.period_ns == callback.timer.period_ns) \
                    or (callback.callback_type == CallbackType.SUBSCRIPTION and expectation.topic_name == callback.subscription.topic_name):
                        return expectation
        return None

    @staticmethod
    def from_csv(expectation_csv_filename: str, component_name: Optional[str]) -> List:
        expectation_list: list[Expectation] = []
        if not os.path.isfile(expectation_csv_filename):
            _logger.error(f"Unable to read expectation csv: {expectation_csv_filename}")
            return []
        with open(expectation_csv_filename, 'r', encoding='utf-8') as csvfile:
            for row in csv.DictReader(csvfile, ['component_name', 'node_name', 'callback_name', 'callback_type', 'period_ns', 'topic_name', 'value', 'lower_limit', 'upper_limit', 'ratio', 'burst_num']):
                try:
                    if component_name is not None and row['component_name'] != component_name:
                        continue
                    expectation = Expectation(row['component_name'], row['node_name'], row['callback_name'],
                        CallbackType.TIMER if row['callback_type'] == 'timer_callback' else CallbackType.SUBSCRIPTION,
                        int(row['period_ns']), row['topic_name'], float(row['value']), float(row['lower_limit']), float(row['upper_limit']), float(row['ratio']), int(row['burst_num']))
                except:
                    _logger.error(f"Error at reading: {row['callback_name']}")
                    return None
                expectation_list.append(expectation)
        return expectation_list


class Stats():
    def __init__(self):
        self.component_name = ''
        self.node_name = ''
        self.callback_name = ''
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
        stats.callback_type = callback.callback_type.type_name
        stats.period_ns = callback.timer.period_ns if callback.callback_type == CallbackType.TIMER else -1
        stats.subscribe_topic_name = callback.subscribe_topic_name if callback.callback_type == CallbackType.SUBSCRIPTION else ''
        stats.metrics = metrics.name
        stats.graph_filename = graph_filename

        df_callback = df_callback.dropna()
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
        return stats

    @staticmethod
    def from_expectation(component_name: str, expectation: Expectation, metrics: Metrics):
        stats = Stats()
        stats.component_name = component_name
        stats.node_name = expectation.node_name
        stats.callback_name = expectation.callback_name
        stats.callback_type = expectation.callback_type.type_name
        stats.period_ns =  expectation.period_ns if expectation.callback_type == CallbackType.TIMER else -1
        stats.subscribe_topic_name = expectation.topic_name if expectation.callback_type == CallbackType.SUBSCRIPTION else ''
        stats.metrics = metrics.name
        return stats


class Result():
    def __init__(self, stats: Stats, expectation: Optional[Expectation]=None):
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
        df_callback = df_callback.dropna()
        df_callback = df_callback.iloc[:, 1]                  # get metrics value only
        df_callback = trail_df(df_callback, end_strip_num=2)  # remove the last data because freq becomes small

        if len(df_callback) >= 2:
            self.result_status = ResultStatus.PASS.name
            self.ratio_lower_limit = float((df_callback <= expectation.lower_limit).sum() / len(df_callback))
            self.ratio_upper_limit = float((df_callback >= expectation.upper_limit).sum() / len(df_callback))
            if self.ratio_lower_limit >= expectation.ratio:
                self.result_ratio_lower_limit = ResultStatus.FAILED.name
            if self.ratio_upper_limit >= expectation.ratio:
                self.result_ratio_upper_limit = ResultStatus.FAILED.name

            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_callback, key=lambda x: x < expectation.lower_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_lower_limit = max(group) if len(group) > 0 else 0
            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_callback, key=lambda x: x > expectation.upper_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_upper_limit = max(group) if len(group) > 0 else 0
            if self.burst_num_lower_limit >= expectation.burst_num:
                self.result_burst_num_lower_limit = ResultStatus.FAILED.name
            if self.burst_num_upper_limit >= expectation.burst_num:
                self.result_burst_num_upper_limit = ResultStatus.FAILED.name

        if self.result_ratio_lower_limit == ResultStatus.FAILED.name \
            or self.result_ratio_upper_limit == ResultStatus.FAILED.name \
            or self.result_burst_num_lower_limit == ResultStatus.FAILED.name \
            or self.result_burst_num_upper_limit == ResultStatus.FAILED.name:
                self.result_status = ResultStatus.FAILED.name


def create_stats_for_node(node: Node, metrics: Metrics, dest_dir: str, component_name: str) -> dict[str, Stats]:
    stats_list = {}
    try:
        timeseries_plot = get_node_plot(node, metrics)
        figure = timeseries_plot.show('system_time', export_path='dummy.html')
        figure.y_range.start = 0
        figure.width = 1000
        figure.height = 350
        graph_filename = metrics.name + node.node_name.replace('/', '_')
        graph_filename = graph_filename[:250]
        export_graph(figure, dest_dir, graph_filename, _logger)
        df_node = timeseries_plot.to_dataframe()
    except:
        _logger.info(f'This node is not called: {node.node_name}')
        return stats_list

    for callback in node.callbacks:
        df_callback = df_node[callback.callback_name]
        stats = Stats.from_df(component_name, node.node_name, callback, metrics, graph_filename, df_callback)
        stats_list[callback.callback_name] = stats
    return stats_list


def validate_callback(component_name: str, target_node_list: list[Node], metrics: Metrics, dest_dir: str,  expectation_list: List[Expectation] = []) -> list[Result]:
    result_info_list: list[Result] = []
    for node in target_node_list:
        _logger.debug(f'Processing ({metrics.name}): {node.node_name}')
        stats_list = create_stats_for_node(node, metrics, dest_dir, component_name)

        for callback in node.callbacks:
            if callback.callback_name not in stats_list:
                # Not measured
                continue
            # Measured
            expectation = Expectation.find_expectation(expectation_list, callback)
            result = Result(stats_list[callback.callback_name], expectation)
            if expectation:
                # Measured and to be validated
                try:
                    df_node = get_node_plot(node, metrics).to_dataframe()
                    df_callback = df_node[callback.callback_name]
                    expectation_list.remove(expectation)
                    result.validate(df_callback, expectation)
                except:
                    _logger.info(f'This node is not called: {node.node_name}')
            result_info_list.append(result)

    for expectation in expectation_list:
        # Not measured but should be validated
        result = Result(Stats.from_expectation(component_name, expectation, metrics), expectation)
        result_info_list.append(result)
    return result_info_list


def save_stats(result_list: list[Result], component_name: str, dest_dir: str, metrics_str: str):
    result_var_list = []
    for result in result_list:
        result.stats = vars(result.stats)
        result_var_list.append(vars(result))
    result_var_list.sort(key=lambda x: x['stats']['node_name'])
    result_var_list.sort(key=lambda x: x['expectation_id'] if 'expectation_id' in x else 9999)
    result_file_path = f'{dest_dir}/stats_{metrics_str}.yaml'
    with open(result_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(result_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)

def validate_component(app: Application, component_name: str, dest_dir: str, force: bool, expectation_csv_filename: str):
    """Validate callback for each component"""
    dest_dir = f'{dest_dir}/callback/{component_name}'
    make_destination_dir(dest_dir, force, _logger)

    target_node_list: list[Node] = []
    for node in app.nodes:
        # _logger.debug(f'Processing: {node.node_name}')
        if ComponentManager().check_if_target(component_name, node.node_name):
            target_node_list.append(node)

    result_list = validate_callback(component_name, target_node_list, Metrics.FREQUENCY, dest_dir, Expectation.from_csv(expectation_csv_filename, component_name))
    save_stats(result_list, component_name, dest_dir, Metrics.FREQUENCY.name)

    result_list = validate_callback(component_name, target_node_list, Metrics.PERIOD, dest_dir)
    save_stats(result_list, component_name, dest_dir, Metrics.PERIOD.name)

    result_list = validate_callback(component_name, target_node_list, Metrics.LATENCY, dest_dir)
    save_stats(result_list, component_name, dest_dir, Metrics.LATENCY.name)


def validate(logger, arch: Architecture, app: Application, dest_dir: str, force: bool,
             component_list_json: str, expectation_csv_filename: str):
    """Validate callback"""
    global _logger
    _logger = logger

    _logger.info(f'<<< Validate callback start >>>')

    make_destination_dir(dest_dir, force, _logger)
    arch.export(dest_dir + '/architecture.yaml', force=True)
    ComponentManager().initialize(component_list_json, _logger)

    for component_name, _ in ComponentManager().component_dict.items():
        validate_component(app, component_name, dest_dir, force, expectation_csv_filename)

    _logger.info(f'<<< Validate callback finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--expectation_csv_filename', type=str, default='expectation_callback.csv')
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
    args = parse_arg()
    logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    logger.debug(f'trace_data: {args.trace_data[0]}')
    logger.debug(f'component_list_json: {args.component_list_json}')
    logger.debug(f'expectation_csv_filename: {args.expectation_csv_filename}')
    logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    logger.debug(f'dest_dir: {dest_dir}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    validate(logger, arch, app, dest_dir, args.force, args.component_list_json, args.expectation_csv_filename)


if __name__ == '__main__':
    main()
