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
Script to check gap b/w publication and subscription frequency
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import argparse
import logging
import statistics
import yaml
import pandas as pd
from bokeh.plotting import figure
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.runtime.communication import Communication
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph
from common.utils import get_callback_legend, round_yaml
from common.utils import ComponentManager

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def calc_frequency(timestamp_df: pd.DataFrame,
                   timestamp_name: str) -> tuple[list[float], list[int]]:
    """Measure frequency per 1 second"""
    timestamp_list: list[float] = []
    frequency_list: list[int] = []

    timestamp_name = [s for s in timestamp_df.columns if timestamp_name in s][0]
    timestamp_series = timestamp_df[timestamp_name]
    timestamp_series = timestamp_series.sort_values()   # it seems time stamp is not sorted (?)

    if len(timestamp_series) < 2:
        return [], []
    timestamp_series *= 1e-9    # from [nsec] to [sec]
    timestamp_series -= timestamp_series[0]    # treat the first data as 0 [sec]

    timestamp_start_1sec = timestamp_series[0]
    timestamp_list.append(timestamp_start_1sec)
    frequency_list.append(1)

    for timestamp in timestamp_series:
        if (timestamp - timestamp_start_1sec) < 1.0:
            # keep incrementing frequency for the current 1 second term
            frequency_list[-1] += 1
        else:
            # it reaches the next 1 second term
            timestamp_start_1sec = timestamp
            timestamp_list.append(timestamp_start_1sec)
            frequency_list.append(1)

    return timestamp_list, frequency_list


def calc_pub_freq(timestamp_df: pd.DataFrame) -> tuple[list[float], list[int]]:
    """Measure frequency of publication"""
    return calc_frequency(timestamp_df, 'rclcpp_publish_timestamp')


def calc_sub_freq(timestamp_df: pd.DataFrame) -> tuple[list[float], list[int]]:
    """Measure frequency of subscription"""
    return calc_frequency(timestamp_df, 'callback_start_timestamp')


def match_pubsub_freq(pub_freq: tuple[list[float], list[int]],
                      sub_freq: tuple[list[float], list[int]]):
    """
    Make pubsub freq list whose timestamps match

    Parameters
    ----------
    timestamp_df : pd.DataFrame
        pandas data frame retrieved from CARET

    Returns
    -------
    timestamp_list : list[float]
        list of timestamp [sec]
    pub_freq_list : list[float]
        list of publication frequency [Hz]
    sub_freq_list : list[float]
        list of subscription frequency [Hz]

    Note
    ---
    In case there is not correspond subscription(*), the publish event is ignored
    (*: gap between publication timestamp and subscription timestamp > 1 sec)
    """
    timestamp_list = []
    pub_freq_list = []
    sub_freq_list = []
    index_to_start_check = 0
    maximum_gap_time = 1.0  # 1sec
    for index_pub in range(len(pub_freq[0])):
        pub_time = pub_freq[0][index_pub]
        matched_sub_index = -1
        for index_sub in range(index_to_start_check, len(sub_freq[0])):
            gap_time = sub_freq[0][index_sub] - pub_time
            if gap_time < 0:
                continue
            gap_time_next = sub_freq[0][index_sub + 1] - pub_time if index_sub < len(sub_freq[0]) - 1 else -1
            if gap_time_next < 0:
                break    # ignore the last 1 sec because frequency may be calculated incorrectly
            if gap_time < gap_time_next and gap_time < maximum_gap_time:
                matched_sub_index = index_sub
                break
        if matched_sub_index != -1:
            index_to_start_check = matched_sub_index + 1
            timestamp_list.append(pub_time)
            pub_freq_list.append(pub_freq[1][index_pub])
            sub_freq_list.append(sub_freq[1][matched_sub_index])
        elif gap_time_next > 0:
            _logger.warning('Corresponding subscription is not found')

    return timestamp_list, pub_freq_list, sub_freq_list


def make_graph(pub_freq: tuple[list[float], list[int]],
               sub_freq: tuple[list[float], list[int]]) -> figure:
    """Create timeseries graph(pub/sub freq vs time)"""
    graph = figure(x_axis_label="Time [sec]", y_axis_label="Frequency [Hz]",
                   width=1000, height=300, active_scroll='wheel_zoom')
    graph.y_range.start = 0
    graph.line(pub_freq[0], pub_freq[1], legend_label='pub', line_color="blue", line_width=1)
    graph.circle(sub_freq[0], sub_freq[1], legend_label='sub', line_color="green", size=6)
    return graph


def create_stats(title,  graph_filename, topic_name, publisher_name,
                 node_name, callback_name, callback_legend,
                 publication_freq, subscription_freq, num_huge_gap) -> dict:
    """Create stats"""
    stats = {
        'title': title,
        'graph_filename': graph_filename,
        'topic_name': topic_name,
        'publisher_name': publisher_name,
        'node_name': node_name,
        'component_name': ComponentManager().get_component_name(node_name),
        'callback_name': callback_name,
        'callback_legend': callback_legend,
        'publication_freq': publication_freq,
        'subscription_freq': subscription_freq,
        'num_huge_gap': num_huge_gap,
    }
    return stats


def analyze_communication(args, dest_dir, app: Application, communication: Communication) -> tuple(dict, bool):
    """Analyze a subscription callback function"""
    title = f'{communication.topic_name} : {communication.publish_node_name} -> {communication.subscribe_node_name}'
    graph_filename = communication.topic_name.replace('/', '_')[1:] + communication.subscribe_node_name.replace('/', '_')
    graph_filename = graph_filename[:250]
    node = app.get_node(communication.callback_subscription.node_name)
    callback_name = communication.callback_subscription.callback_name
    callback_legend = get_callback_legend(node, callback_name)
    _logger.debug(f'Processing {title}')

    try:
        pub_df = communication.publisher.to_dataframe()
        sub_df = communication.subscription.to_dataframe()
        pub_freq = calc_pub_freq(pub_df)
        sub_freq = calc_sub_freq(sub_df)
    except:
        _logger.warning(f'Failed to get pub/sub data: {title}')
        return None, None

    if len(pub_freq[0]) < 2 or len(sub_freq[0]) < 2:
        _logger.warning(f'Not enough data {title}')
        _logger.warning('  # of pub_freq = ' + str(len(pub_freq[0])) + ', # of sub_freq = ' + str(len(sub_freq[0])))
        return None, None

    # Check gap between pub/sub freq
    matched_pubsub_freq = match_pubsub_freq(pub_freq, sub_freq)
    if len(matched_pubsub_freq[0]) < 2:
        _logger.warning(f'Not enough matching {title}')
        _logger.warning('  # of matched_pubsub_freq = ' + str(len(pub_freq[0])))
        return None, None

    # Save graph file
    graph = make_graph(pub_freq, sub_freq)
    export_graph(graph, dest_dir, graph_filename, title, _logger)


    # Check if sub freq is lower than pub freq
    mean_pub_freq = round(float(statistics.mean(matched_pubsub_freq[1])), 3)
    mean_sub_freq = round(float(statistics.mean(matched_pubsub_freq[2])), 3)
    freq_threshold = mean_pub_freq * (1 - args.gap_threshold_ratio)
    num_huge_gap = int(sum(freq_callback <= freq_threshold for freq_callback in matched_pubsub_freq[2]))

    stats = create_stats(title, graph_filename, communication.topic_name,
                         communication.publish_node_name, communication.subscribe_node_name,
                         callback_name, callback_legend, mean_pub_freq, mean_sub_freq, num_huge_gap)

    is_warning = False
    if num_huge_gap >= args.count_threshold:
        is_warning = True
    return stats, is_warning

def analyze(args, lttng: Lttng, arch: Architecture, app: Application, dest_dir: str):
    """Analyze Subscription Callbacks"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Subscription Callbacks: Start >>>')
    make_destination_dir(dest_dir, args.force, _logger)
    ComponentManager().initialize(args.component_list_json, _logger)

    stats_all_list = []
    stats_warning_list = []

    topic_name_list = []
    for item in lttng.get_count(['topic_name']).iterrows():
        topic_name_list.append(item[0])

    for topic_name in topic_name_list:
        try:
            communication_list = app.get_communications(topic_name)
        except:
            _logger.info(f' No topic communication: {topic_name}')
            continue

        for communication in communication_list:
            if ComponentManager().check_if_ignore(communication.callback_subscription.callback_name):
                continue
            stats, is_warning = analyze_communication(args, dest_dir, app, communication)
            if stats:
                stats_all_list.append(stats)
            if is_warning:
                stats_warning_list.append(stats)

    stats_all_list = sorted(stats_all_list, key=lambda x: x['callback_name'])
    stats_warning_list = sorted(stats_warning_list, key=lambda x: x['callback_name'])

    with open(f'{dest_dir}/stats_callback_subscription.yaml', 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats_all_list, f_yaml, encoding='utf-8',
                       allow_unicode=True, sort_keys=False)
    round_yaml(f'{dest_dir}/stats_callback_subscription.yaml')
    with open(f'{dest_dir}/stats_callback_subscription_warning.yaml', 'w', encoding='utf-8') as f_yaml:
        yaml.safe_dump(stats_warning_list, f_yaml, encoding='utf-8',
                       allow_unicode=True, sort_keys=False)
    round_yaml(f'{dest_dir}/stats_callback_subscription_warning.yaml')

    _logger.info('<<< Analyze Subscription Callbacks: Finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to check gap b/w publication and subscription frequency')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
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
    _logger.debug(f'dest_dir: {args.dest_dir[0]}')
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    _logger.debug(f'gap_threshold_ratio: {args.gap_threshold_ratio}')
    _logger.debug(f'count_threshold: {args.count_threshold}')

    lttng = read_trace_data(args.trace_data[0], args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    dest_dir = args.dest_dir[0]
    analyze(args, lttng, arch, app, dest_dir + '/check_callback_sub')


if __name__ == '__main__':
    main()
