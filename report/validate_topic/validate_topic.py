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
from enum import Enum
from pathlib import Path
import argparse
import logging
import re
import copy
from itertools import groupby
import csv
import yaml
import numpy as np
import pandas as pd
from bokeh.plotting import Figure, figure
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.node import Node
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.runtime.communication import Communication, Subscription, Publisher
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df
from common.utils import ComponentManager
from common.utils_validation import Metrics, ResultStatus


# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def get_comm_plot(comm: Communication, metrics: Metrics):
    # todo: create_communication_frequency_plot doesn't work (it's stuck and consumes too much memory)
    if metrics == Metrics.FREQUENCY:
        return Plot.create_frequency_timeseries_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.PERIOD:
        return Plot.create_period_timeseries_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.LATENCY:
        return Plot.create_latency_timeseries_plot(comm)


def get_callback_plot(callback: CallbackBase, metrics: Metrics):
    if metrics == Metrics.FREQUENCY:
        return Plot.create_frequency_timeseries_plot([callback])
    elif metrics == Metrics.PERIOD:
        return Plot.create_period_timeseries_plot([callback])


class Expectation():
    id = 0
    def __init__(self,
        topic_name: str, publish_node_name: str, publish_component_name: str, subscribe_node_name: str, subscribe_component_name: str,
        value: float, lower_limit: Optional[float] = None, upper_limit: Optional[float] = None, ratio: Optional[float] = None, burst_num: Optional[int] = None):
        self.id = Expectation.id
        Expectation.id += 1
        self.topic_name = topic_name
        self.publish_node_name = publish_node_name
        self.publish_component_name = publish_component_name
        self.subscribe_node_name = subscribe_node_name
        self.subscribe_component_name = subscribe_component_name
        self.value = value
        self.lower_limit = lower_limit or self.value * 0.8
        self.upper_limit = upper_limit or self.value * 1.2
        self.ratio = ratio or 0.2
        self.burst_num = burst_num or 5

    @staticmethod
    def find_expectation(expectation_list: list, topic_name, publish_node_name, subscribe_node_name):
        for expectation in expectation_list:
            if expectation.topic_name == topic_name and \
                expectation.publish_node_name == publish_node_name and expectation.subscribe_node_name == subscribe_node_name:
                return expectation
        return None

    @staticmethod
    def from_csv(expectation_csv_filename: str, publish_component_name: Optional[str], subscribe_component_name: Optional[str], lower_limit_scale=0.8, upper_limit_scale=1.2, ratio=0.2, burst_num=5) -> List:
        expectation_list: list[Expectation] = []
        if not os.path.isfile(expectation_csv_filename):
            _logger.error(f"Unable to read expectation csv: {expectation_csv_filename}")
            return []
        with open(expectation_csv_filename, 'r', encoding='utf-8') as csvfile:
            for row in csv.DictReader(csvfile, ['topic_name', 'publish_node_name', 'publish_component_name', 'subscribe_node_name', 'subscribe_component_name', 'value']):
                try:
                    if (publish_component_name is not None and row['publish_component_name'] != publish_component_name) \
                        or (subscribe_component_name is not None and row['subscribe_component_name'] != subscribe_component_name):
                        continue
                    try:
                        value = float(row['value'])
                    except ValueError:
                        value = 0
                    expectation = Expectation(row['topic_name'], row['publish_node_name'], row['publish_component_name'],
                        row['subscribe_node_name'], row['subscribe_component_name'], value, value * lower_limit_scale, value * upper_limit_scale, ratio if value > 1 else 0.5, burst_num)
                except:
                    _logger.error(f"Error at reading: {row['topic_name']}")
                    return None
                expectation_list.append(expectation)
        return expectation_list

class Stats():
    def __init__(self):
        self.topic_name = ''
        self.publish_node_name = ''
        self.publish_component_name = ''
        self.subscribe_node_name = ''
        self.subscribe_component_name = ''
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
    def from_df(component_pair: tuple[str], topic_name, publish_node_name, subscribe_node_name, metrics: Metrics, graph_filename: str, df_comm: pd.DataFrame):
        stats = Stats()
        stats.topic_name = topic_name
        stats.publish_node_name = publish_node_name
        stats.publish_component_name = component_pair[0]
        stats.subscribe_node_name = subscribe_node_name
        stats.subscribe_component_name = component_pair[1]
        stats.metrics = metrics.name
        stats.graph_filename = graph_filename

        df_comm = df_comm.iloc[:, 1]                  # get metrics value only (use value of publish. df=|time|pub|time|sub|)
        df_comm = trail_df(df_comm, end_strip_num=2)  # remove the last data because freq becomes small

        if len(df_comm) >= 2:
            stats.avg = float(df_comm.mean())
            stats.std = float(df_comm.std())
            stats.min = float(df_comm.min())
            stats.max = float(df_comm.max())
            stats.percentile5_min = float(df_comm.quantile(0.05))
            stats.percentile5_max = float(df_comm.quantile(0.95))
            df_percentile5 = df_comm[(df_comm >= stats.percentile5_min) & (df_comm <= stats.percentile5_max)]
            stats.percentile5_avg = float(df_percentile5.mean()) if len(df_percentile5) > 2 else stats.avg
        else:
            return None, None
        return stats, df_comm

    @staticmethod
    def from_expectation(expectation: Expectation, metrics: Metrics):
        stats = Stats()
        stats.topic_name = expectation.topic_name
        stats.publish_node_name = expectation.publish_node_name
        stats.publish_component_name = expectation.publish_component_name
        stats.subscribe_node_name = expectation.subscribe_node_name
        stats.subscribe_component_name = expectation.subscribe_component_name
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

    def validate(self, df_topic: pd.DataFrame, expectation: Expectation):
        if expectation.value <= 0:
            # it's not expected to be tested but don't use OUT_OF_SCOPE
            self.result_status = ResultStatus.DONT_CARE.name
            return
        if len(df_topic) >= 2:
            self.result_status = ResultStatus.PASS.name
            self.ratio_lower_limit = float((df_topic < expectation.lower_limit).sum() / len(df_topic))
            self.ratio_upper_limit = float((df_topic > expectation.upper_limit).sum() / len(df_topic))
            if self.ratio_lower_limit > expectation.ratio:
                self.result_ratio_lower_limit = ResultStatus.FAILED.name
            # if self.ratio_upper_limit > expectation.ratio:
            #     self.result_ratio_upper_limit = ResultStatus.FAILED.name

            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_topic, key=lambda x: x < expectation.lower_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_lower_limit = max(group) if len(group) > 0 else 0
            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_topic, key=lambda x: x > expectation.upper_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_upper_limit = max(group) if len(group) > 0 else 0
            if self.burst_num_lower_limit > expectation.burst_num:
                self.result_burst_num_lower_limit = ResultStatus.FAILED.name
            # if self.burst_num_upper_limit > expectation.burst_num:
            #     self.result_burst_num_upper_limit = ResultStatus.FAILED.name

        if self.result_ratio_lower_limit == ResultStatus.FAILED.name \
            or self.result_ratio_upper_limit == ResultStatus.FAILED.name \
            or self.result_burst_num_lower_limit == ResultStatus.FAILED.name \
            or self.result_burst_num_upper_limit == ResultStatus.FAILED.name:
                self.result_status = ResultStatus.FAILED.name


def create_stats_for_comm(component_pair: tuple[str], comm: Communication, metrics: Metrics, dest_dir: str) -> Tuple[Stats, pd.DataFrame]:
    try:
        timeseries_plot = get_comm_plot(comm, metrics)
        figure = timeseries_plot.figure()
        figure.y_range.start = 0
        figure.width = 1000
        figure.height = 350
        graph_filename = metrics.name + comm.topic_name.replace('/', '_') + comm.publish_node_name.replace('/', '_') + comm.subscribe_node_name.replace('/', '_')
        graph_filename = graph_filename[:250]
        df_comm = timeseries_plot.to_dataframe()
        stats, df = Stats.from_df(component_pair, comm.topic_name, comm.publish_node_name, comm.subscribe_node_name, metrics, graph_filename, df_comm)
        if stats:
            export_graph(figure, dest_dir, graph_filename, with_png=False, logger=_logger)
        else:
            raise Exception()
    except:
        _logger.info(f'This comm is invalid: {comm.topic_name}: {comm.publish_node_name} -> {comm.subscribe_node_name}')
        return None, None

    return stats, df

def create_stats_for_callback_as_topic(app: Application, component_pair: tuple[str], expectation: Expectation, metrics: Metrics, dest_dir: str) -> Tuple[Stats, pd.DataFrame]:
    try:
        callback = None
        for subscription in app.subscriptions:
            if subscription.topic_name == expectation.topic_name:
                callback = app.get_callback(subscription.callback_name)
                break
        if callback:
            timeseries_plot = get_callback_plot(callback, metrics)
            figure = timeseries_plot.figure()
            figure.y_range.start = 0
            figure.width = 1000
            figure.height = 350
            graph_filename = metrics.name + callback.subscribe_topic_name.replace('/', '_') + '_unknown' + callback.node_name.replace('/', '_')
            graph_filename = graph_filename[:250]
            df_comm = timeseries_plot.to_dataframe()

            stats, df = Stats.from_df(component_pair, callback.subscribe_topic_name, expectation.publish_node_name, callback.node_name, metrics, graph_filename, df_comm)
            if stats:
                export_graph(figure, dest_dir, graph_filename, with_png=False, logger=_logger)
            else:
                raise Exception()
        else:
            raise Exception
    except:
        _logger.info(f'This callback is invalid: {expectation.topic_name}')
        return None, None

    return stats, df


def validate_topic(app: Application, component_pair: tuple[str], target_comm_list: list[Communication], metrics: Metrics, dest_dir: str, expectation_list: List[Expectation] = []) -> list[Result]:
    expectation_validated_list = expectation_list.copy()   # keep original because there may be multiple callbacks with the same parameters in a node
    result_info_list: list[Result] = []

    for comm in target_comm_list:
        _logger.debug(f'Processing ({metrics.name}): {component_pair}, {comm.topic_name}: {comm.publish_node_name} -> {comm.subscribe_node_name}')
        stats, df = create_stats_for_comm(component_pair, comm, metrics, dest_dir)
        if stats is None:
            continue

        # Measured
        expectation = Expectation.find_expectation(expectation_list, comm.topic_name, comm.publish_node_name, comm.subscribe_node_name)
        result = Result(stats, expectation)
        if expectation:
            # Measured and to be validated
            result.validate(df, expectation)
            if expectation in expectation_validated_list:
                expectation_validated_list.remove(expectation)
        result_info_list.append(result)

    for expectation in expectation_validated_list.copy():
        # Comm was invalid. Try to validate using subscription callback
        if metrics != Metrics.FREQUENCY:
            continue
        _logger.debug(f'Processing as callback({metrics.name}): {component_pair}, {expectation.topic_name}: {expectation.publish_node_name} -> {expectation.subscribe_node_name}')
        stats, df = create_stats_for_callback_as_topic(app, component_pair, expectation, metrics, dest_dir)
        if stats is None:
            continue

        # Measured and to be validated
        result = Result(stats, expectation)
        result.validate(df, expectation)
        expectation_validated_list.remove(expectation)
        result_info_list.append(result)

    for expectation in expectation_validated_list:
        if expectation.value > 0:
            # Not measured but should be validated
            result = Result(Stats.from_expectation(expectation, metrics), expectation)
            result_info_list.append(result)

    return result_info_list


def save_stats(result_list: list[Result], metrics_str: str, dest_dir: str, is_append=False):
    result_var_list = []
    result_file_path = f'{dest_dir}/stats_{metrics_str}.yaml'
    if is_append and os.path.isfile(result_file_path):
        with open(result_file_path, 'r', encoding='utf-8') as f_yaml:
            result_var_list = yaml.safe_load(f_yaml)

    for result in result_list:
        result.stats = vars(result.stats)
        result_var_list.append(vars(result))
    result_var_list.sort(key=lambda x: x['stats']['topic_name'])
    result_var_list.sort(key=lambda x: x['expectation_id'] if 'expectation_id' in x else 9999)
    with open(result_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(result_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


def validate_component_pair(app: Application, component_pair: tuple[str], dest_dir: str, force: bool, expectation_csv_filename: str):
    """Validate callback for component pair"""
    dest_dir = f'{dest_dir}/validate_topic/{component_pair[0]}-{component_pair[1]}'

    target_comm_list: list[Communication] = []
    for comm in app.communications:
        if ComponentManager().check_if_ignore(comm.publish_node_name) \
            or ComponentManager().check_if_ignore(comm.subscribe_node_name)\
            or ComponentManager().check_if_ignore(comm.topic_name):
            continue
        publish_component_name = ComponentManager().get_component_name(comm.publish_node_name)
        subscribe_component_name = ComponentManager().get_component_name(comm.subscribe_node_name)
        if ComponentManager().check_if_external_in_topic(comm.topic_name, comm.subscribe_node_name):
            publish_component_name = 'external'
        elif ComponentManager().check_if_external_out_topic(comm.topic_name, comm.publish_node_name):
            subscribe_component_name = 'external'
        if publish_component_name == component_pair[0] and subscribe_component_name == component_pair[1]:
            target_comm_list.append(comm)

    make_destination_dir(dest_dir, force, _logger)

    result_list = validate_topic(app, component_pair, target_comm_list, Metrics.FREQUENCY, dest_dir, Expectation.from_csv(expectation_csv_filename, component_pair[0], component_pair[1]))
    save_stats(result_list, Metrics.FREQUENCY.name, dest_dir)

    result_list = validate_topic(app, component_pair, target_comm_list, Metrics.PERIOD, dest_dir)
    save_stats(result_list, Metrics.PERIOD.name, dest_dir)

    result_list = validate_topic(app, component_pair, target_comm_list, Metrics.LATENCY, dest_dir)
    save_stats(result_list, Metrics.LATENCY.name, dest_dir)


def validate(logger, arch: Architecture, app: Application, dest_dir: str, force: bool,
             component_list_json: str, expectation_csv_filename: str):
    """Validate topic"""
    global _logger
    _logger = logger

    _logger.info(f'<<< Validate topic start >>>')

    ComponentManager().initialize(component_list_json, _logger)

    make_destination_dir(dest_dir + '/validate_topic', force, _logger)

    for component_pair in ComponentManager().get_component_pair_list(with_external=True):
        validate_component_pair(app, component_pair, dest_dir, force, expectation_csv_filename)

    _logger.info(f'<<< Validate topic finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--report_directory', type=str, default='')
    parser.add_argument('--component_list_json', type=str, default='component_list.json')
    parser.add_argument('--expectation_csv_filename', type=str, default='expectation_topic.csv')
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
    dest_dir = args.report_directory if args.report_directory != '' else f'val_{Path(args.trace_data[0]).stem}'
    logger.debug(f'dest_dir: {dest_dir}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    validate(logger, arch, app, dest_dir, args.force, args.component_list_json, args.expectation_csv_filename)


if __name__ == '__main__':
    main()
