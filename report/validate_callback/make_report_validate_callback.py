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
Script to make report page
"""
import os
import sys
import argparse
from pathlib import Path
import csv
import flask
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import ComponentManager
from common.utils_validation import make_stats_dict_node_callback_metrics, summarize_callback_result, make_callback_detail_filename
from common.utils_validation import Metrics, ResultStatus


sub_title_list = ['Frequency [Hz]', 'Period [ms]', 'Latency [ms]']

app = flask.Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def make_report_callback_validation(dest_dir: str, trace_name: str, component_name: str, stats_dict_node_callback_metrics: dict, summary_dict_metrics: dict):
    title = f'Callback validation result: {component_name}'
    destination_path = f'{dest_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_callback_validation.html'

    node_filename_dict = {}
    for node_name, _ in stats_dict_node_callback_metrics.items():
        node_filename_dict[node_name] = make_callback_detail_filename(node_name)

    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                trace_name=trace_name,
                metrics_list=[Metrics.FREQUENCY.name, Metrics.PERIOD.name, Metrics.LATENCY.name],
                stats_node_callback_metrics=stats_dict_node_callback_metrics,
                summary_dict=summary_dict_metrics[Metrics.FREQUENCY.name],
                node_filename_dict=node_filename_dict,
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def make_report_callback_metrics(dest_dir: str, trace_name: str, component_name: str, stats_dict_node_callback_metrics: dict, summary_dict_metrics: dict):
    for i, metrics in enumerate(Metrics):
        title = f'Callback validation result ({metrics.name}): {component_name}'
        destination_path = f'{dest_dir}/index_{metrics.name}.html'
        template_path = f'{Path(__file__).resolve().parent}/template_callback_metrics.html'

        node_filename_dict = {}
        for node_name, _ in stats_dict_node_callback_metrics.items():
            node_filename_dict[node_name] = make_callback_detail_filename(node_name)

        with app.app_context():
            with open(template_path, 'r', encoding='utf-8') as f_html:
                template_string = f_html.read()
                rendered = flask.render_template_string(
                    template_string,
                    title=title,
                    trace_name=trace_name,
                    metrics_name=metrics.name,
                    sub_title=sub_title_list[i],
                    stats_node_callback_metrics=stats_dict_node_callback_metrics,
                    summary_dict=summary_dict_metrics[metrics.name],
                    node_filename_dict=node_filename_dict,
                )

            with open(destination_path, 'w', encoding='utf-8') as f_html:
                f_html.write(rendered)


def make_report_callback_detail(dest_dir: str, trace_name: str, component_name: str, stats_dict_node_callback_metrics: dict):
    for node_name, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
        title = f'Callback details: {node_name}'
        destination_path = f'{dest_dir}/{make_callback_detail_filename(node_name)}'
        template_path = f'{Path(__file__).resolve().parent}/template_callback_detail.html'

        # sort by callback_name
        stats_dict_callback_metrics = sorted(stats_dict_callback_metrics.items())
        stats_dict_callback_metrics = dict((x, y) for x, y in stats_dict_callback_metrics)

        with app.app_context():
            with open(template_path, 'r', encoding='utf-8') as f_html:
                template_string = f_html.read()
                rendered = flask.render_template_string(
                    template_string,
                    title=title,
                    trace_name=trace_name,
                    metrics_list=[Metrics.FREQUENCY.name, Metrics.PERIOD.name, Metrics.LATENCY.name],
                    stats_callback_metrics=stats_dict_callback_metrics,
                    sub_title_list=sub_title_list,
                )

            with open(destination_path, 'w', encoding='utf-8') as f_html:
                f_html.write(rendered)


def make_report_callback(report_dir: str, component_name: str):
    stats_dict_node_callback_metrics: dict = make_stats_dict_node_callback_metrics(report_dir, component_name)
    summary_dict_metrics = summarize_callback_result(stats_dict_node_callback_metrics)

    dest_dir = f'{report_dir}/callback/{component_name}'
    trace_name = report_dir.split('/')[-1]

    make_report_callback_validation(dest_dir, trace_name, component_name, stats_dict_node_callback_metrics, summary_dict_metrics)
    make_report_callback_metrics(dest_dir, trace_name, component_name, stats_dict_node_callback_metrics, summary_dict_metrics)
    make_report_callback_detail(dest_dir, trace_name, component_name, stats_dict_node_callback_metrics)


def make_report(report_dir: str, component_list_json: str):
    ComponentManager().initialize(component_list_json)

    for component_name, _ in ComponentManager().component_dict.items():
        make_report_callback(report_dir, component_name)


def make_unused_list(report_dir: str, component_list_json: str):
    ComponentManager().initialize(component_list_json)

    callback_list_new = []
    callback_list_deleted = []

    for component_name, _ in ComponentManager().component_dict.items():
        stats_dict_node_callback_metrics: dict = make_stats_dict_node_callback_metrics(report_dir, component_name)
        for node_name, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
            for callback_name, stats_dict_metrics in stats_dict_callback_metrics.items():
                stats = stats_dict_metrics[Metrics.FREQUENCY.name]
                info = [stats['stats']['node_name'],
                        stats['stats']['callback_type'] + '_callback',
                        stats['stats']['period_ns'] if stats['stats']['period_ns'] != -1 else stats['stats']['subscribe_topic_name'],
                        stats['stats']['avg']]
                if stats['result_status'] == ResultStatus.OUT_OF_SCOPE.name:
                    callback_list_new.append(info)
                elif stats['result_status'] == ResultStatus.NOT_MEASURED.name:
                    callback_list_deleted.append(info[:-1])

    with open(f'{report_dir}/callback_list_new.csv', 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(callback_list_new)

    with open(f'{report_dir}/callback_list_deleted.csv', 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(callback_list_deleted)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()

    report_dir = args.report_directory[0]
    make_report(report_dir, args.component_list_json)
    make_unused_list(report_dir, args.component_list_json)
    print('<<< OK. report_validate_callback is created >>>')


if __name__ == '__main__':
    main()
