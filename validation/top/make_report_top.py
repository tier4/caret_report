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
import shutil
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
        for _, stats_dict_callback_metrics in stats_dict_node_callback_metrics.items():
            for _, stats_dict_metrics in stats_dict_callback_metrics.items():
                stats = stats_dict_metrics[metrics.name]
                if stats['result_status'] == 'PASS':
                    summary_dict_metrics[metrics.name]['cnt_pass'] += 1
                elif stats['result_status'] == 'FAILED':
                    summary_dict_metrics[metrics.name]['cnt_failed'] += 1
                elif stats['result_status'] == 'NOT_MEASURED':
                    summary_dict_metrics[metrics.name]['cnt_not_measured'] += 1
                else:
                    summary_dict_metrics[metrics.name]['cnt_out_of_scope'] += 1
    return summary_dict_metrics


def summarize_callback_result(report_dir: str, component_name: str):
    stats_dict_node_callback_metrics: dict = {}
    for metrics in Metrics:
        with open(f'{report_dir}/callback/{component_name}/stats_{metrics.name}.yaml', 'r', encoding='utf-8') as f_yaml:
            stats_list = yaml.safe_load(f_yaml)
            for stats in stats_list:
                stats['stats']['callback_name'] = stats['stats']['callback_name'].split('/')[-1]
                stats['stats']['callback_type'] = stats['stats']['callback_type'].split('_')[0]
                node_name = stats['stats']['node_name']
                callback_name = stats['stats']['callback_name']
                if node_name not in stats_dict_node_callback_metrics:
                    stats_dict_node_callback_metrics[node_name] = {}
                if callback_name not in stats_dict_node_callback_metrics[node_name]:
                    stats_dict_node_callback_metrics[node_name][callback_name] = {}
                stats_dict_node_callback_metrics[node_name][callback_name][metrics.name] = stats

    summary_dict_metrics = summarize_result(stats_dict_node_callback_metrics)
    return summary_dict_metrics


def make_report(report_dir: str, package_list_json: str):
    summary_callback_dict_component_metrics = {}

    package_dict, _ = utils.make_package_list(package_list_json)
    for component_name, _ in package_dict.items():
        summary_callback_dict_component_metrics[component_name] = summarize_callback_result(report_dir, component_name)


    title = f'Validation result'
    trace_name = report_dir.split('/')[-1]
    destination_path = f'{report_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_top.html'

    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                trace_name=trace_name,
                summary_callback_dict_component_metrics=summary_callback_dict_component_metrics,
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)

    script_path = f'{Path(__file__).resolve().parent}/top.js'
    shutil.copy(script_path, report_dir)


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
