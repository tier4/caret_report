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
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph
from common.utils import Metrics, ResultStatus, ComponentManager

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def get_comm_plot(comm: Communication, metrics: Metrics):
    # todo: create_communication_frequency_plot doesn't work (it's stuck and consumes too much memory)
    if metrics == Metrics.FREQUENCY:
        return Plot.create_publish_subscription_frequency_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.PERIOD:
        return Plot.create_publish_subscription_period_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.LATENCY:
        return Plot.create_communication_latency_plot(comm)


class Expectation():
    id = 0
    def __init__(self,
        topic_name: str, publish_node_name: str, pubilsh_component_name: str, subscribe_node_name: str, subscribe_component_name: str,
        value: float, lower_limit: Optional[float] = None, upper_limit: Optional[float] = None, ratio: Optional[float] = None, burst_num: Optional[int] = None):
        self.id = Expectation.id
        Expectation.id += 1
        self.topic_name = topic_name
        self.publish_node_name = publish_node_name
        self.pubilsh_component_name = pubilsh_component_name
        self.subscribe_node_name = subscribe_node_name
        self.subscribe_component_name = subscribe_component_name
        self.value = value
        self.lower_limit = lower_limit or self.value * 0.8
        self.upper_limit = upper_limit or self.value * 1.2
        self.ratio = ratio or 0.2
        self.burst_num = burst_num or 2

    @staticmethod
    def find_expectation(expectation_list: list, comm: Communication):
        for expectation in expectation_list:
            if expectation.topic_name == comm.topic_name and \
                expectation.publish_node_name == comm.publish_node_name and expectation.subscribe_node_name == comm.subscribe_node_name:
                return expectation
        return None

    @staticmethod
    def from_csv(expectation_csv_filename: str, pubilsh_component_name: Optional[str], subscribe_component_name: Optional[str]) -> List:
        expectation_list: list[Expectation] = []
        if not os.path.isfile(expectation_csv_filename):
            return []
        with open(expectation_csv_filename, 'r', encoding='utf-8') as csvfile:
            for row in csv.DictReader(csvfile, ['topic_name', 'publish_node_name', 'pubilsh_component_name', 'subscribe_node_name', 'subscribe_component_name', 'value', 'lower_limit', 'upper_limit', 'ratio', 'burst_num']):
                try:
                    if (pubilsh_component_name is not None and row['pubilsh_component_name'] != pubilsh_component_name) \
                        or (subscribe_component_name is not None and row['subscribe_component_name'] != subscribe_component_name):
                        continue
                    expectation = Expectation(row['topic_name'], row['publish_node_name'], row['pubilsh_component_name'],
                        row['subscribe_node_name'], row['subscribe_component_name'], float(row['value']), float(row['lower_limit']), float(row['upper_limit']), float(row['ratio']), int(row['burst_num']))
                except:
                    _logger.error(f"Error at reading: {row['topic_name']}")
                    return None
                expectation_list.append(expectation)
        return expectation_list

class Stats():
    def __init__(self):
        self.topic_name = ''
        self.publish_node_name = ''
        self.pubilsh_component_name = ''
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
    def from_df(component_pair: tuple[str], comm: Communication, metrics: Metrics, graph_filename: str, df_comm: pd.DataFrame):
        stats = Stats()
        stats.topic_name = comm.topic_name
        stats.publish_node_name = comm.publish_node_name
        stats.pubilsh_component_name = component_pair[0]
        stats.subscribe_node_name = comm.subscribe_node_name
        stats.subscribe_component_name = component_pair[1]
        stats.metrics = metrics.name
        stats.graph_filename = graph_filename

        df_comm = df_comm.dropna()
        df_comm = df_comm.iloc[:-1, 1]    # remove the last data because freq becomes small, get freq only
        if len(df_comm) >= 2:
            stats.avg = float(df_comm.mean())
            stats.std = float(df_comm.std())
            stats.min = float(df_comm.min())
            stats.max = float(df_comm.max())
            stats.percentile5_min = float(df_comm.quantile(0.05))
            stats.percentile5_max = float(df_comm.quantile(0.95))
            df_percentile5 = df_comm[(df_comm >= stats.percentile5_min) & (df_comm <= stats.percentile5_max)]
            stats.percentile5_avg = float(df_percentile5.mean()) if len(df_percentile5) > 2 else stats.avg
        return stats

    @staticmethod
    def from_expectation(expectation: Expectation, metrics: Metrics):
        stats = Stats()
        stats.topic_name = expectation.topic_name
        stats.publish_node_name = expectation.publish_node_name
        stats.pubilsh_component_name = expectation.pubilsh_component_name
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
        df_topic = df_topic.dropna()
        df_topic = df_topic.iloc[:-1, 1]    # remove the last data because freq becomes small, get freq only
        if len(df_topic) >= 2:
            self.result_status = ResultStatus.PASS.name
            self.ratio_lower_limit = float((df_topic <= expectation.lower_limit).sum() / len(df_topic))
            self.ratio_upper_limit = float((df_topic >= expectation.upper_limit).sum() / len(df_topic))
            if self.ratio_lower_limit >= expectation.ratio:
                self.result_ratio_lower_limit = ResultStatus.FAILED.name
            if self.ratio_upper_limit >= expectation.ratio:
                self.result_ratio_upper_limit = ResultStatus.FAILED.name

            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_topic, key=lambda x: x < expectation.lower_limit)]
            group = [x[1] for x in flag_group if x[0]]
            self.burst_num_lower_limit = max(group) if len(group) > 0 else 0
            flag_group = [(flag, len(list(group))) for flag, group in groupby(df_topic, key=lambda x: x > expectation.upper_limit)]
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


def create_stats_for_comm(component_pair: tuple[str], comm: Communication, metrics: Metrics, dest_dir: str) -> Stats:
    try:
        timeseries_plot = get_comm_plot(comm, metrics)
        figure = timeseries_plot.show('system_time', export_path='dummy.html')
        figure.y_range.start = 0
        figure.width = 1000
        figure.height = 350
        graph_filename = metrics.name + comm.topic_name.replace('/', '_') + comm.publish_node_name.replace('/', '_') + comm.subscribe_node_name.replace('/', '_')
        graph_filename = graph_filename[:250]
        export_graph(figure, dest_dir, graph_filename, _logger)
        df_comm = timeseries_plot.to_dataframe()
    except:
        _logger.info(f'This comm is invalid: {comm.topic_name}: {comm.publish_node_name} -> {comm.subscribe_node_name}')
        return None

    stats = Stats.from_df(component_pair, comm, metrics, graph_filename, df_comm)
    return stats


def validate_topic(component_pair: tuple[str], target_comm_list: list[Communication], metrics: Metrics, dest_dir: str, expectation_list: List[Expectation] = []) -> list[Result]:

    result_info_list: list[Result] = []
    for comm in target_comm_list:
        _logger.debug(f'Processing ({metrics.name}): {component_pair}, {comm.topic_name}: {comm.publish_node_name} -> {comm.subscribe_node_name}')
        stats = create_stats_for_comm(component_pair, comm, metrics, dest_dir)
        if stats is None:
            continue

        # Measured
        expectation = Expectation.find_expectation(expectation_list, comm)
        result = Result(stats, expectation)
        if expectation:
            # Measured and to be validated
            try:
                timeseries_plot = get_comm_plot(comm, metrics)
                df_comm = timeseries_plot.to_dataframe()
                expectation_list.remove(expectation)
                result.validate(df_comm, expectation)
            except:
                _logger.info(f'This communication is invalid: {comm.topic_name}, {comm.publish_node_name} -> {comm.subscribe_node_name}')

        result_info_list.append(result)

    for expectation in expectation_list:
        # Not measured but should be validated
        result = Result(Stats.from_expectation(expectation, metrics), expectation)
        result_info_list.append(result)

    return result_info_list


def save_stats(result_list: list[Result], metrics_str: str, dest_dir: str):
    result_var_list = []
    for result in result_list:
        result.stats = vars(result.stats)
        result_var_list.append(vars(result))
    result_var_list.sort(key=lambda x: x['stats']['topic_name'])
    result_var_list.sort(key=lambda x: x['expectation_id'] if 'expectation_id' in x else 9999)
    result_file_path = f'{dest_dir}/stats_{metrics_str}.yaml'
    with open(result_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(result_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


def validate_component_pair(app: Application, component_pair: tuple[str], dest_dir: str, force: bool, expectation_csv_filename: str):
    """Validate callback for component pair"""
    dest_dir = f'{dest_dir}/topic/{component_pair[0]}-{component_pair[1]}'

    target_comm_list: list[Communication] = []
    for comm in app.communications:
        if ComponentManager().check_if_ignore(comm.publish_node_name) \
            or ComponentManager().check_if_ignore(comm.subscribe_node_name)\
            or ComponentManager().check_if_ignore(comm.topic_name):
            continue
        pubilsh_component_name = ComponentManager().get_component_name(comm.publish_node_name)
        subscribe_component_name = ComponentManager().get_component_name(comm.subscribe_node_name)
        if pubilsh_component_name == component_pair[0] and subscribe_component_name == component_pair[1]:
            target_comm_list.append(comm)

    if len(target_comm_list) == 0:
        return

    make_destination_dir(dest_dir, force, _logger)

    result_list = validate_topic(component_pair, target_comm_list, Metrics.FREQUENCY, dest_dir, Expectation.from_csv(expectation_csv_filename, component_pair[0], component_pair[1]))
    save_stats(result_list, Metrics.FREQUENCY.name, dest_dir)

    result_list = validate_topic(component_pair, target_comm_list, Metrics.PERIOD, dest_dir)
    save_stats(result_list, Metrics.PERIOD.name, dest_dir)

    result_list = validate_topic(component_pair, target_comm_list, Metrics.LATENCY, dest_dir)
    save_stats(result_list, Metrics.LATENCY.name, dest_dir)


def validate(logger, arch: Architecture, app: Application, dest_dir: str, force: bool,
             component_list_json: str, expectation_csv_filename: str):
    """Validate topic"""
    global _logger
    _logger = logger

    _logger.info(f'<<< Validate topic start >>>')

    ComponentManager().initialize(component_list_json, _logger)

    make_destination_dir(dest_dir + '/topic', force, _logger)

    for component_pair in ComponentManager().get_component_pair_list():
        validate_component_pair(app, component_pair, dest_dir, force, expectation_csv_filename)

    _logger.info(f'<<< Validate topic finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
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
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    logger.debug(f'dest_dir: {dest_dir}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    validate(logger, arch, app, dest_dir, args.force, args.component_list_json, args.expectation_csv_filename)


if __name__ == '__main__':
    main()
