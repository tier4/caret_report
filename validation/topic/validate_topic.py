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
from common import utils

_logger: logging.Logger = None


class Metrics(Enum):
    FREQUENCY = 1
    PERIOD = 2
    LATENCY = 3

metrics_dict = {Metrics.FREQUENCY: Plot.create_publish_subscription_frequency_plot,
                Metrics.PERIOD: Plot.create_publish_subscription_frequency_plot,
                Metrics.LATENCY: Plot.create_communication_latency_plot}

class ResultStatus(Enum):
    PASS = 1
    FAILED = 2
    OUT_OF_SCOPE = 3
    NOT_MEASURED = 4
    NOT_MEASURED_OUT_OF_SCOPE = 5


class ComponentManager:
    def __new__(cls, *args, **kargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(ComponentManager, cls).__new__(cls)
            cls.package_dict = kargs['package_dict']
            cls.ignore_list = kargs['ignore_list']
        return cls._instance

    def get_component_name(self, node_name: str) -> str:
        for package_name, regexp in self.package_dict.items():
            if re.search(regexp, node_name):
                return package_name
        return 'other'

    def check_if_ignore(self, node_name: str) -> bool:
        for ignore in self.ignore_list:
            if re.search(ignore, node_name):
                return True
        return False


# todo
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
    def find_expectation():
        # todo
        return None

    @staticmethod
    def from_csv(expectation_csv_filename: str) -> List:
        expectation_list: list[Expectation] = []
        # todo
        return expectation_list


class Stats():
    def __init__(self):
        self.topic_name = ''
        self.publish_node_name = ''
        self.pubilsh_component_name = ''
        self.subscribe_node_name = ''
        self.subscribe_component_name = ''
        self.comm_id = -1
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
    def from_df(comm: Communication, metrics: Metrics, graph_filename: str, df_comm: pd.DataFrame, id: int):
        stats = Stats()
        stats.topic_name = comm.topic_name
        stats.publish_node_name = comm.publish_node_name
        stats.pubilsh_component_name = ComponentManager().get_component_name(stats.publish_node_name)
        stats.subscribe_node_name = comm.subscribe_node_name
        stats.subscribe_component_name = ComponentManager().get_component_name(stats.subscribe_node_name)
        stats.comm_id = id
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
            stats.percentile5_avg = float(df_comm[(df_comm > stats.percentile5_min) & (df_comm < stats.percentile5_max)].mean())
        return stats

    @staticmethod
    def from_expectation():
        stats = Stats()
        # todo
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
            pass
        # todo


def create_stats_for_topic(topic_name: str, comms: list[Communication], metrics: Metrics, dest_dir: str) -> list[Stats]:
    stats_list = []

    graph_filename = metrics.name + topic_name.replace('/', '_')[:250]
    pub_list = []
    sub_list = []
    comm_list = []
    for id, comm in enumerate(comms):
        if ComponentManager().check_if_ignore(comm.publish_node_name) or ComponentManager().check_if_ignore(comm.subscribe_node_name):
            continue

        try:
            if metrics == Metrics.LATENCY:
                timeseries_plot = metrics_dict[metrics](comm)
            else:
                timeseries_plot = metrics_dict[metrics](comm.publisher)
            df_comm = timeseries_plot.to_dataframe()
        except:
            _logger.info(f'This communication is invalid: {comm.topic_name}, {comm.publish_node_name} -> {comm.subscribe_node_name}')
            continue

        stats = Stats.from_df(comm, metrics, graph_filename, df_comm, id)
        stats_list.append(stats)

        pub_list.append(comm.publisher)
        sub_list.append(comm.subscription)
        comm_list.append(comm)

    if len(comm_list) > 0 and len(pub_list) > 0:
        if metrics == Metrics.LATENCY:
            timeseries_plot = metrics_dict[metrics](comm_list)
        else:
            timeseries_plot = metrics_dict[metrics](pub_list + sub_list)
        figure = timeseries_plot.show(export_path='dummy.html')
        figure.y_range.start = 0
        figure.width = 1000
        figure.height = 350

        utils.export_graph(figure, dest_dir + '/topic/', graph_filename, _logger)

    return stats_list


def validate_topic(topic_name: str, comms: list[Communication], metrics: Metrics, dest_dir: str, expectation_list: List[Expectation] = []) -> list[Result]:
    _logger.debug(f'Processing ({metrics.name}): {topic_name}')

    result_info_list: List[Result] = []
    stats_list = create_stats_for_topic(topic_name, comms, metrics, dest_dir)

    for stats in stats_list:
        # Measured
        expectation = Expectation.find_expectation()
        result = Result(stats, expectation)
        if expectation:
            # Measured and to be validated
            comm = [comm for comm in comms if comm.topic_name == stats.topic_name
                                              and comm.publish_node_name == stats.publish_node_name
                                              and comm.subscribe_node_name == stats.subscribe_node_name]
            if len(comm) > 0:
                comm = comm[0]
                try:
                    if metrics == Metrics.LATENCY:
                        timeseries_plot = metrics_dict[metrics](comm)
                    else:
                        timeseries_plot = metrics_dict[metrics](comm.publisher)
                    df_comm = timeseries_plot.to_dataframe()
                    expectation_list.remove(expectation)
                    result.validate(df_comm, expectation)
                except:
                    _logger.info(f'This communication is invalid: {comm.topic_name}, {comm.publish_node_name} -> {comm.subscribe_node_name}')

        result_info_list.append(result)

    for expectation in expectation_list:
        # Not measured but should be validated
        result = Result(Stats.from_expectation(), expectation)
        result_info_list.append(result)

    return result_info_list


def save_stats(result_list: list[Result], dest_dir: str, metrics_str: str):
    result_var_list = []
    for result in result_list:
        result.stats = vars(result.stats)
        result_var_list.append(vars(result))
    result_var_list.sort(key=lambda x: x['stats']['comm_id'])
    result_var_list.sort(key=lambda x: x['stats']['topic_name'])
    result_var_list.sort(key=lambda x: x['expectation_id'] if 'expectation_id' in x else 9999)
    result_file_path = f'{dest_dir}/topic/stats_{metrics_str}.yaml'
    with open(result_file_path, 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(result_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


# def save_stats_for_all_(result_list: list[Result], dest_dir: str, metrics_str: str):
#     inter_component_matrix = []
#     for component_name_src, _ in ComponentManager.package_dict.items():
#         for component_name_dst, _ in ComponentManager.package_dict.items():
#             inter_component_matrix.append((component_name_src, component_name_dst))

#     for inter_component in inter_component_matrix:
#         src2dst = inter_component[0] + '2' + inter_component[1]

#         result_list_for_inter_component = []
#         for result in result_list:
#             if result.stats.pubilsh_component_name == inter_component[0] and result.stats.subscribe_component_name == inter_component[1]:
#                 result_list_for_inter_component.append(copy.deepcopy(result))

#         if len(result_list_for_inter_component) > 0:
#             save_stats(result_list_for_inter_component, dest_dir, metrics_str, src2dst)


def validate(logger, arch: Architecture, app: Application, dest_dir: str, force: bool,
             package_list_json: str, expectation_csv_filename: str):
    """Validate topic"""
    global _logger
    _logger = logger

    _logger.info(f'<<< Validate topic start >>>')

    utils.make_destination_dir(dest_dir + '/topic', force, _logger)
    package_dict, ignore_list = utils.make_package_list(package_list_json, _logger)
    _ = ComponentManager(package_dict=package_dict, ignore_list=ignore_list)

    frequency_result_list: list[Result] = []
    period_result_list: list[Result] = []
    latency_result_list: list[Result] = []

    all_communications = app.communications
    for topic_name in app.topic_names:
        comms = [comms for comms in all_communications if comms.topic_name == topic_name]
        frequency_result_list.extend(validate_topic(topic_name, comms, Metrics.FREQUENCY, dest_dir, Expectation.from_csv(expectation_csv_filename)))
        period_result_list.extend(validate_topic(topic_name, comms, Metrics.PERIOD, dest_dir))
        latency_result_list.extend(validate_topic(topic_name, comms, Metrics.LATENCY, dest_dir))

    save_stats(frequency_result_list, dest_dir, Metrics.FREQUENCY.name)
    save_stats(period_result_list, dest_dir, Metrics.PERIOD.name)
    save_stats(latency_result_list, dest_dir, Metrics.LATENCY.name)

    _logger.info(f'<<< Validate topic finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze node callback functions')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--package_list_json', type=str, default='')
    parser.add_argument('--expectation_csv_filename', type=str, default='expectation_topic.csv')
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
    args = parse_arg()
    logger = utils.create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    logger.debug(f'trace_data: {args.trace_data[0]}')
    logger.debug(f'package_list_json: {args.package_list_json}')
    logger.debug(f'expectation_csv_filename: {args.expectation_csv_filename}')
    logger.debug(f'start_point: {args.start_point}, duration: {args.duration}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    logger.debug(f'dest_dir: {dest_dir}')

    lttng = utils.read_trace_data(args.trace_data[0], args.start_point, args.duration, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    validate(logger, arch, app, dest_dir, args.force, args.package_list_json, args.expectation_csv_filename)


if __name__ == '__main__':
    main()
