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
Utility functions
"""
from __future__ import annotations
import os
from enum import Enum
import glob
import yaml


class Metrics(Enum):
    FREQUENCY = 1
    PERIOD = 2
    LATENCY = 3


class ResultStatus(Enum):
    PASS = 1
    FAILED = 2
    OUT_OF_SCOPE = 3
    NOT_MEASURED = 4
    DONT_CARE = 5


def make_callback_detail_filename(node_name: str):
    return node_name.replace('/', '_')[1:] + '.html'


def make_topic_detail_filename(topic_name: str):
    return topic_name.replace('/', '_')[1:] + '.html'


def make_stats_dict_node_callback_metrics(report_dir: str, component_name: str):
    stats_dict_node_callback_metrics: dict = {}
    for metrics in Metrics:
        stats_filename = f'{report_dir}/callback/{component_name}/stats_{metrics.name}.yaml'
        if not os.path.isfile(stats_filename):
            continue
        with open(stats_filename, 'r', encoding='utf-8') as f_yaml:
            stats_list = yaml.safe_load(f_yaml)
            for stats in stats_list:
                # stats['stats']['node_name'] = stats['stats']['node_name'].replace('_', '_<wbr>')
                stats['stats']['callback_name'] = stats['stats']['callback_name'].split('/')[-1]
                stats['stats']['callback_type'] = stats['stats']['callback_type'].split('_')[0]
                # stats['stats']['subscribe_topic_name'] = stats['stats']['subscribe_topic_name'].replace('_', '_<wbr>')
                for key, value in stats.items():
                    if type(value) == float or type(value) == int:
                        rounded_value = value if 'num' in key else f'{round(value, 3): .01f}'.strip()
                        stats[key] = '---' if value == -1 else rounded_value
                for key, value in stats['stats'].items():
                    if key != 'period_ns' and (type(value) == float or type(value) == int):
                        rounded_value = value if 'num' in key else f'{round(value, 3): .01f}'.strip()
                        stats['stats'][key] = '---' if value == -1 else rounded_value

                if stats['stats']['avg'] == '---' and stats['expectation_value'] == '---':
                    # not measured(but added to stats file) and OUT_OF_SCOPE
                    continue

                stats['stats']['subscribe_topic_html'] = ''
                if stats['stats']['subscribe_topic_name'] != '':
                    topic_html = make_topic_detail_filename(stats['stats']['subscribe_topic_name'])
                    topic_html_list = glob.glob(f'{report_dir}/topic/*/{topic_html}', recursive=False)
                    topic_html = [html for html in topic_html_list if '-' + stats['stats']['component_name'] in html]
                    if len(topic_html) > 0:
                        topic_html = topic_html[0]
                        topic_html = topic_html.split('/')
                        topic_html = '/'.join(topic_html[1:])
                        stats['stats']['subscribe_topic_html'] = '../../' + topic_html

                node_name = stats['stats']['node_name']
                callback_name = stats['stats']['callback_name']
                if metrics == Metrics.FREQUENCY:
                    if node_name not in stats_dict_node_callback_metrics:
                        stats_dict_node_callback_metrics[node_name] = {}
                    if callback_name not in stats_dict_node_callback_metrics[node_name]:
                        stats_dict_node_callback_metrics[node_name][callback_name] = {}
                    stats_dict_node_callback_metrics[node_name][callback_name][metrics.name] = stats
                else :
                    if node_name in stats_dict_node_callback_metrics \
                        and callback_name in stats_dict_node_callback_metrics[node_name]:
                        stats_dict_node_callback_metrics[node_name][callback_name][metrics.name] = stats

    return stats_dict_node_callback_metrics


def summarize_callback_result(stats_dict_node_callback_metrics: dict) -> dict:
    summary_dict_metrics = {}
    for metrics in Metrics:
        summary_dict_metrics[metrics.name] = {
            'cnt_pass': 0,
            'cnt_failed': 0,
            'cnt_not_measured': 0,
            'cnt_out_of_scope': 0,
            'cnt_dont_care': 0,
        }

    for metrics in Metrics:
        for node_name, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
            for callback_name, stats_dict_metrics in stats_dict_callback_metrics.items():
                try:
                    stats = stats_dict_metrics[metrics.name]
                except:
                    # print('This metrics is not measured: ', node_name, callback_name, metrics.name)
                    continue

                if stats['result_status'] == ResultStatus.PASS.name:
                    summary_dict_metrics[metrics.name]['cnt_pass'] += 1
                elif stats['result_status'] == ResultStatus.FAILED.name:
                    summary_dict_metrics[metrics.name]['cnt_failed'] += 1
                elif stats['result_status'] == ResultStatus.NOT_MEASURED.name:
                    summary_dict_metrics[metrics.name]['cnt_not_measured'] += 1
                elif stats['result_status'] == ResultStatus.OUT_OF_SCOPE.name:
                    summary_dict_metrics[metrics.name]['cnt_out_of_scope'] += 1
                elif stats['result_status'] == ResultStatus.DONT_CARE.name:
                    summary_dict_metrics[metrics.name]['cnt_dont_care'] += 1
    return summary_dict_metrics


def make_stats_dict_topic_pubsub_metrics(report_dir: str, component_pair: tuple[str]):
    stats_dict_topic_pubsub_metrics: dict = {}
    for metrics in Metrics:
        stats_filename = f'{report_dir}/topic/{component_pair[0]}-{component_pair[1]}/stats_{metrics.name}.yaml'
        if not os.path.isfile(stats_filename):
            continue
        with open(stats_filename, 'r', encoding='utf-8') as f_yaml:
            stats_list = yaml.safe_load(f_yaml)
            for stats in stats_list:
                for key, value in stats.items():
                    if type(value) == float or type(value) == int:
                        rounded_value = value if 'num' in key else f'{round(value, 3): .01f}'.strip()
                        stats[key] = '---' if value == -1 else rounded_value
                for key, value in stats['stats'].items():
                    if key != 'period_ns' and (type(value) == float or type(value) == int):
                        rounded_value = value if 'num' in key else f'{round(value, 3): .01f}'.strip()
                        stats['stats'][key] = '---' if value == -1 else rounded_value

                if stats['stats']['avg'] == '---' and stats['expectation_value'] == '---':
                    # not measured(but added to stats file) and OUT_OF_SCOPE
                    continue

                stats['stats']['publish_node_html'] = ''
                if stats['stats']['pubilsh_component_name'] != 'external':
                    stats['stats']['publish_node_html'] = '../../callback/' + \
                        stats['stats']['pubilsh_component_name'] + '/' + \
                        make_callback_detail_filename(stats['stats']['publish_node_name'])

                stats['stats']['subscribe_node_html'] = ''
                if stats['stats']['subscribe_component_name'] != 'external':
                    stats['stats']['subscribe_node_html'] = '../../callback/' + \
                        stats['stats']['subscribe_component_name'] + '/' + \
                        make_callback_detail_filename(stats['stats']['subscribe_node_name'])

                topic_name = stats['stats']['topic_name']
                pubsub = (stats['stats']['publish_node_name'], stats['stats']['subscribe_node_name'])
                if metrics == Metrics.FREQUENCY:
                    if topic_name not in stats_dict_topic_pubsub_metrics:
                        stats_dict_topic_pubsub_metrics[topic_name] = {}
                    if pubsub not in stats_dict_topic_pubsub_metrics[topic_name]:
                        stats_dict_topic_pubsub_metrics[topic_name][pubsub] = {}
                    stats_dict_topic_pubsub_metrics[topic_name][pubsub][metrics.name] = stats
                else :
                    if topic_name in stats_dict_topic_pubsub_metrics \
                        and pubsub in stats_dict_topic_pubsub_metrics[topic_name]:
                        stats_dict_topic_pubsub_metrics[topic_name][pubsub][metrics.name] = stats

    return stats_dict_topic_pubsub_metrics


def summarize_topic_result(stats_dict_topic_pubsub_metrics: dict) -> dict:
    summary_dict_metrics = {}
    for metrics in Metrics:
        summary_dict_metrics[metrics.name] = {
            'cnt_pass': 0,
            'cnt_failed': 0,
            'cnt_not_measured': 0,
            'cnt_out_of_scope': 0,
            'cnt_dont_care': 0,
        }

    for metrics in Metrics:
        for topic_name, stats_dict_pubsub_metrics in stats_dict_topic_pubsub_metrics.items():
            for pubsub, stats_dict_metrics in stats_dict_pubsub_metrics.items():
                try:
                    stats = stats_dict_metrics[metrics.name]
                except:
                    # print('This metrics is not measured: ', node_name, callback_name, metrics.name)
                    continue

                if stats['result_status'] == ResultStatus.PASS.name:
                    summary_dict_metrics[metrics.name]['cnt_pass'] += 1
                elif stats['result_status'] == ResultStatus.FAILED.name:
                    summary_dict_metrics[metrics.name]['cnt_failed'] += 1
                elif stats['result_status'] == ResultStatus.NOT_MEASURED.name:
                    summary_dict_metrics[metrics.name]['cnt_not_measured'] += 1
                elif stats['result_status'] == ResultStatus.OUT_OF_SCOPE.name:
                    summary_dict_metrics[metrics.name]['cnt_out_of_scope'] += 1
                elif stats['result_status'] == ResultStatus.DONT_CARE.name:
                    summary_dict_metrics[metrics.name]['cnt_dont_care'] += 1
    return summary_dict_metrics
