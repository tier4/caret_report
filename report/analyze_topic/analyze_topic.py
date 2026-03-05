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
Script to analyze topics
"""
from __future__ import annotations
from enum import Enum
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
from caret_analyze.runtime.communication import Communication
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.plot import Plot, PlotBase
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


class Metrics(Enum):
    FREQUENCY = 1
    PERIOD = 2
    LATENCY = 3


def get_comm_plot(comm: Communication, metrics: Metrics):
    # todo: create_communication_frequency_plot doesn't work (it's stuck and consumes too much memory)
    if metrics == Metrics.FREQUENCY:
        return Plot.create_frequency_timeseries_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.PERIOD:
        return Plot.create_period_timeseries_plot([comm.publisher, comm.subscription])
    elif metrics == Metrics.LATENCY:
        return Plot.create_latency_timeseries_plot(comm)


class StatsComm():
    """Statistics of comm"""
    def __init__(self, topic_name, publish_node_name, subscribe_node_name):
        self.topic_name = topic_name
        self.publish_node_name = publish_node_name
        self.subscribe_node_name = subscribe_node_name
        self.filename = ''
        self.avg = '---'
        self.std = '---'
        self.min = '---'
        self.max = '---'
        self.p50 = '---'
        self.p95 = '---'
        self.p99 = '---'

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


def create_stats_for_comm(comm: Communication, index: int, metrics: Metrics, dest_dir: str, xaxis_type: str, with_graph: bool) -> StatsComm:
    stats_comm = StatsComm(comm.topic_name, comm.publish_node_name, comm.subscribe_node_name)
    try:
        timeseries_plot = get_comm_plot(comm, metrics)
        if with_graph:
            figure = timeseries_plot.figure(xaxis_type=xaxis_type)
            figure.y_range.start = 0
            graph_filename = metrics.name + comm.topic_name.replace('/', '_') + '_' + str(index)
            graph_filefilename_suffix = comm.subscribe_node_name.replace('/', '_')
            graph_filename = graph_filename + graph_filefilename_suffix[:120-len(graph_filename)]  # avoid too long file name
            stats_comm.filename = graph_filename
            export_graph(figure, dest_dir, graph_filename, with_png=False, logger=_logger)
        df_comm = timeseries_plot.to_dataframe(xaxis_type=xaxis_type)
        df_comm = df_comm.iloc[:, 1]                  # get metrics value only (use value of publish. df=|time|pub|time|sub|)
        df_comm = trail_df(df_comm, end_strip_num=2)  # remove the last data because freq becomes small
        stats_comm.calculate(df_comm)
    except:
        _logger.info(f'This comm is invalid: {comm.topic_name}: {comm.publish_node_name} -> {comm.subscribe_node_name}')
        return None
    return stats_comm


def analyze_comms(topic_name: str, comm_list: list[Communication], dest_dir: str, xaxis_type: str, threshold_freq_not_display: int=300) -> dict[str, list[StatsComm]]:
    """Analyze topic (communications)"""
    _logger.info(f'Processing {topic_name}')

    stats_dict: dict[str, list[StatsComm]] = {}
    skip_list = []

    for metrics in Metrics:
        for index, comm in enumerate(comm_list):
            with_graph = True
            if comm in skip_list and metrics != Metrics.FREQUENCY:
                with_graph = False
            stats_comm = create_stats_for_comm(comm, index, metrics, dest_dir, xaxis_type, with_graph)
            if stats_comm is None:
                continue
            if metrics == Metrics.FREQUENCY:
                freq = stats_comm.avg
                if isinstance(freq, int) or isinstance(freq, float):
                    if freq >= threshold_freq_not_display:
                        _logger.info(f'{comm.topic_name} is not displayed in graph')
                        skip_list.append(comm)
            stats_dict.setdefault(metrics.name, [])
            stats_dict[metrics.name].append(stats_comm)
    return stats_dict


def analyze_topic(app: Application, topic_name: str, dest_dir: str, xaxis_type: str):
    """Analyze a topic"""
    try:
        comm_list: list[Communication] = app.get_communications(topic_name)
    except:
        _logger.info(f'No communication for {topic_name}')
        return
    if not comm_list:
        return

    make_destination_dir(dest_dir, False, _logger)
    stats_dict = analyze_comms(topic_name, comm_list, dest_dir, xaxis_type)
    if not stats_dict:
        return
    for metrics_name, stats_list in stats_dict.items():
        stats_var_list = []
        for stats in stats_list:
            stats_var_list.append(vars(stats))
        stat_file_path = f"{dest_dir}/stats_{metrics_name}.yaml"
        with open(stat_file_path, 'w', encoding='utf-8') as f_yaml:
            yaml.safe_dump(stats_var_list, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)
        round_yaml(stat_file_path)


def analyze_component(app: Application, topic_name_list: list[str], dest_dir: str, xaxis_type: str):
    """Analyze a component"""
    make_destination_dir(dest_dir, False, _logger)
    for topic_name in topic_name_list:
        topic_dest_dir = f"{dest_dir}/{topic_name.replace('/', '_').lstrip('_')}"
        analyze_topic(app, topic_name, topic_dest_dir, xaxis_type)


def create_component_topic_dict(arch: Architecture) -> dict[str, list[str]]:
    dict_component_name_topic: dict[str, list[str]] = {}
    for topic_name in arch.topic_names:
        is_match = False
        for component_name, _ in ComponentManager().component_dict.items():
            if ComponentManager().check_if_target(component_name, topic_name):
                dict_component_name_topic.setdefault(component_name, [])
                dict_component_name_topic[component_name].append(topic_name)
                is_match = True
                break
        if not is_match:
            dict_component_name_topic.setdefault('other', [])
            dict_component_name_topic['other'].append(topic_name)
    return dict_component_name_topic


def analyze(args, lttng: Lttng, arch: Architecture, app: Application, dest_dir: str):
    """Analyze topics"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Topic: Start >>>')
    make_destination_dir(dest_dir, args.force, _logger)
    arch.export(dest_dir + '/architecture.yaml', force=True)
    ComponentManager().initialize(args.component_list_json, _logger)
    dict_component_name_topic = create_component_topic_dict(arch)

    for component_name, topic_name_list in dict_component_name_topic.items():
        analyze_component(app, topic_name_list, f'{dest_dir}/{component_name}', 'sim_time' if args.sim_time else 'system_time')

    _logger.info('<<< Analyze Topic: Finish >>>')


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
    analyze(args, lttng, arch, app, dest_dir + '/analyze_topic')


if __name__ == '__main__':
    main()
