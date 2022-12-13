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
import glob
import argparse
from enum import Enum
from pathlib import Path
import sys
import yaml
import flask
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common import utils


class Metrics(Enum):
    FREQUENCY = 1
    PERIOD = 2
    LATENCY = 3

sub_title_list = ['Frequency [Hz]', 'Period [ms]', 'Latency [ms]']

app = flask.Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def summarize_result(stats_dict_node_callback_metrics: dict) -> dict:
    summary_dict_metrics = {}
    for metrics in Metrics:
        summary_dict_metrics[metrics.name] = {
            'cnt_pass': 0,
            'cnt_failed': 0,
            'cnt_not_measured': 0,
            'cnt_out_of_scope': 0,
        }

    for metrics in Metrics:
        for node_name, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
            for callback_name, stats_dict_metrics in stats_dict_callback_metrics.items():
                try:
                    stats = stats_dict_metrics[metrics.name]
                except:
                    print('This metrics is not measured: ', node_name, callback_name, metrics.name)
                    continue

                if stats['result_status'] == 'PASS':
                    summary_dict_metrics[metrics.name]['cnt_pass'] += 1
                elif stats['result_status'] == 'FAILED':
                    summary_dict_metrics[metrics.name]['cnt_failed'] += 1
                elif stats['result_status'] == 'NOT_MEASURED':
                    summary_dict_metrics[metrics.name]['cnt_not_measured'] += 1
                else:
                    summary_dict_metrics[metrics.name]['cnt_out_of_scope'] += 1
    return summary_dict_metrics


def make_callback_detail_filename(node_name: str):
    return node_name.replace('/', '_')[1:]


def make_report_callback_validation(report_dir: str, component_name: str, stats_dict_node_callback_metrics: dict, summary_dict_metrics: dict):
    title = f'Callback validation result: {component_name}'
    trace_name = report_dir.split('/')[-1]
    destination_path = f'{report_dir}/callback/{component_name}/index.html'
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


def make_report_callback_metrics(report_dir: str, component_name: str, stats_dict_node_callback_metrics: dict, summary_dict_metrics: dict):
    for i, metrics in enumerate(Metrics):
        title = f'Callback validation result ({metrics.name}): {component_name}'
        trace_name = report_dir.split('/')[-1]
        destination_path = f'{report_dir}/callback/{component_name}/index_{metrics.name}.html'
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


def make_report_callback_detail(report_dir: str, component_name: str, stats_dict_node_callback_metrics: dict, summary_dict_metrics: dict):
    for node_name, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
        title = f'Callback details: {node_name}'
        trace_name = report_dir.split('/')[-1]
        destination_path = f'{report_dir}/callback/{component_name}/{make_callback_detail_filename(node_name)}.html'
        template_path = f'{Path(__file__).resolve().parent}/template_callback_detail.html'

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
    stats_dict_node_callback_metrics: dict = {}
    for metrics in Metrics:
        with open(f'{report_dir}/callback/{component_name}/stats_{metrics.name}.yaml', 'r', encoding='utf-8') as f_yaml:
            stats_list = yaml.safe_load(f_yaml)
            for stats in stats_list:
                stats['stats']['callback_name'] = stats['stats']['callback_name'].split('/')[-1]
                stats['stats']['callback_type'] = stats['stats']['callback_type'].split('_')[0]
                for key, value in stats.items():
                    if type(value) == float or type(value) == int:
                        stats[key] = '---' if value == -1 else f'{round(value, 3): .03f}'.strip()
                for key, value in stats['stats'].items():
                    if key != 'period_ns' and (type(value) == float or type(value) == int):
                        stats['stats'][key] = '---' if value == -1 else f'{round(value, 3): .03f}'.strip()

                if stats['stats']['avg'] == '---' and stats['expectation_value'] == '---':
                    # not measured(but added to stats file) and OUT_OF_SCOPE
                    continue

                node_name = stats['stats']['node_name']
                callback_name = stats['stats']['callback_name']
                if node_name not in stats_dict_node_callback_metrics:
                    stats_dict_node_callback_metrics[node_name] = {}
                if callback_name not in stats_dict_node_callback_metrics[node_name]:
                    stats_dict_node_callback_metrics[node_name][callback_name] = {}
                stats_dict_node_callback_metrics[node_name][callback_name][metrics.name] = stats

    summary_dict_metrics = summarize_result(stats_dict_node_callback_metrics)

    make_report_callback_validation(report_dir, component_name, stats_dict_node_callback_metrics, summary_dict_metrics)
    make_report_callback_metrics(report_dir, component_name, stats_dict_node_callback_metrics, summary_dict_metrics)
    make_report_callback_detail(report_dir, component_name, stats_dict_node_callback_metrics, summary_dict_metrics)


def make_report(report_dir: str, package_list_json: str):
    package_dict, _ = utils.make_package_list(package_list_json)

    for component_name, _ in package_dict.items():
        make_report_callback(report_dir, component_name)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    parser.add_argument('--package_list_json', type=str, default='')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()

    report_dir = args.report_directory[0]
    make_report(report_dir, args.package_list_json)
    print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
