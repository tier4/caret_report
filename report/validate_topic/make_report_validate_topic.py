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
from common.utils_validation import make_stats_dict_topic_pubsub_metrics, summarize_topic_result, make_topic_detail_filename
from common.utils_validation import Metrics, ResultStatus


sub_title_list = ['Frequency [Hz]', 'Period [ms]', 'Latency [ms]']

app = flask.Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def make_report_topic_validation(dest_dir: str, trace_name: str, component_pair: tuple[str], stats_dict_topic_pubsub_metrics: dict, summary_dict_metrics: dict):
    title = f'Topic validation result: {component_pair[0]} -> {component_pair[1]}'
    destination_path = f'{dest_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_topic_validation.html'

    topic_filename_dict = {}
    for topic_name, _ in stats_dict_topic_pubsub_metrics.items():
        topic_filename_dict[topic_name] = make_topic_detail_filename(topic_name)

    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                trace_name=trace_name,
                metrics_list=[Metrics.FREQUENCY.name, Metrics.PERIOD.name, Metrics.LATENCY.name],
                stats_dict_topic_pubsub_metrics=stats_dict_topic_pubsub_metrics,
                summary_dict=summary_dict_metrics[Metrics.FREQUENCY.name],
                topic_filename_dict=topic_filename_dict,
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def make_report_topic_metrics(dest_dir: str, trace_name: str, component_pair: tuple[str], stats_dict_topic_pubsub_metrics: dict, summary_dict_metrics: dict):
    for i, metrics in enumerate(Metrics):
        title = f'Topic validation result ({metrics.name}): {component_pair[0]} -> {component_pair[1]}'
        destination_path = f'{dest_dir}/index_{metrics.name}.html'
        template_path = f'{Path(__file__).resolve().parent}/template_topic_metrics.html'

        topic_filename_dict = {}
        for topic_name, _ in stats_dict_topic_pubsub_metrics.items():
            topic_filename_dict[topic_name] = make_topic_detail_filename(topic_name)

        with app.app_context():
            with open(template_path, 'r', encoding='utf-8') as f_html:
                template_string = f_html.read()
                rendered = flask.render_template_string(
                    template_string,
                    title=title,
                    trace_name=trace_name,
                    metrics_name=metrics.name,
                    sub_title=sub_title_list[i],
                    stats_dict_topic_pubsub_metrics=stats_dict_topic_pubsub_metrics,
                    summary_dict=summary_dict_metrics[metrics.name],
                    topic_filename_dict=topic_filename_dict,
                )

            with open(destination_path, 'w', encoding='utf-8') as f_html:
                f_html.write(rendered)


def make_report_topic_detail(dest_dir: str, trace_name: str, component_pair: tuple[str], stats_dict_topic_pubsub_metrics: dict):
    for topic_name, stats_dict_pubsub_metrics in stats_dict_topic_pubsub_metrics.items():
        title = f'Topic details: {topic_name} ({component_pair[0]} -> {component_pair[1]})'
        destination_path = f'{dest_dir}/{make_topic_detail_filename(topic_name)}'
        template_path = f'{Path(__file__).resolve().parent}/template_topic_detail.html'

        with app.app_context():
            with open(template_path, 'r', encoding='utf-8') as f_html:
                template_string = f_html.read()
                rendered = flask.render_template_string(
                    template_string,
                    title=title,
                    trace_name=trace_name,
                    metrics_list=[Metrics.FREQUENCY.name, Metrics.PERIOD.name, Metrics.LATENCY.name],
                    stats_pubsub_metrics=stats_dict_pubsub_metrics,
                    sub_title_list=sub_title_list,
                )

            with open(destination_path, 'w', encoding='utf-8') as f_html:
                f_html.write(rendered)


def make_report_topic(report_dir: str, component_pair: tuple[str]):
    stats_dict_topic_pubsub_metrics: dict = make_stats_dict_topic_pubsub_metrics(report_dir, component_pair)
    if len(stats_dict_topic_pubsub_metrics)== 0:
        return
    summary_dict_metrics = summarize_topic_result(stats_dict_topic_pubsub_metrics)

    dest_dir = f'{report_dir}/topic/{component_pair[0]}-{component_pair[1]}'
    trace_name = report_dir.split('/')[-1]

    make_report_topic_validation(dest_dir, trace_name, component_pair, stats_dict_topic_pubsub_metrics, summary_dict_metrics)
    make_report_topic_metrics(dest_dir, trace_name, component_pair, stats_dict_topic_pubsub_metrics, summary_dict_metrics)
    make_report_topic_detail(dest_dir, trace_name, component_pair, stats_dict_topic_pubsub_metrics)


def make_report(report_dir: str, component_list_json: str):
    ComponentManager().initialize(component_list_json)

    for component_pair in ComponentManager().get_component_pair_list(with_external=True):
        make_report_topic(report_dir, component_pair)


def make_unused_list(report_dir: str, component_list_json: str):
    ComponentManager().initialize(component_list_json)

    topic_list_new = []
    topic_list_deleted = []

    for component_pair in ComponentManager().get_component_pair_list(with_external=True):
        stats_dict_topic_pubsub_metrics: dict = make_stats_dict_topic_pubsub_metrics(report_dir, component_pair)
        for topic_name, stats_dict_pubsub_metrics in stats_dict_topic_pubsub_metrics.items():
            for pubsub, stats_dict_metrics in stats_dict_pubsub_metrics.items():
                stats = stats_dict_metrics[Metrics.FREQUENCY.name]
                if stats['result_status'] == ResultStatus.OUT_OF_SCOPE.name:
                    if len([x for x in topic_list_new if topic_name in x]) == 0:
                        topic_list_new.append([topic_name, stats['stats']['avg']])
                elif stats['result_status'] == ResultStatus.NOT_MEASURED.name:
                    if len([x for x in topic_list_deleted if topic_name in x]) == 0:
                        topic_list_deleted.append([topic_name])

    with open(f'{report_dir}/topic_list_new.csv', 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(topic_list_new)

    with open(f'{report_dir}/topic_list_deleted.csv', 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(topic_list_deleted)


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
    print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
