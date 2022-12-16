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
from pathlib import Path
import sys
import flask
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import make_stats_dict_node_callback_metrics, summarize_callback_result
from common.utils import make_stats_dict_topic_pubsub_metrics, summarize_topic_result
from common.utils import Metrics, ResultStatus, ComponentManager


app = flask.Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def make_report(report_dir: str, component_list_json: str, note_text_top, note_text_bottom):
    ComponentManager().initialize(component_list_json)

    summary_callback_dict_component_metrics = {}
    for component_name, _ in ComponentManager().component_dict.items():
        stats_dict_node_callback_metrics: dict = make_stats_dict_node_callback_metrics(report_dir, component_name)
        summary_callback_dict_component_metrics[component_name] = summarize_callback_result(stats_dict_node_callback_metrics)

    summary_topic_dict_componentpair_metrics = {}
    for component_pair in ComponentManager().get_component_pair_list():
        stats_dict_node_callback_metrics: dict = make_stats_dict_topic_pubsub_metrics(report_dir, component_pair)
        if len(stats_dict_node_callback_metrics) == 0:
            continue
        summary_topic_dict_componentpair_metrics[component_pair[0] + '-' + component_pair[1]] = summarize_topic_result(stats_dict_node_callback_metrics)

    title = f'Validation result'
    trace_name = report_dir.split('/')[-1]
    destination_path = f'{report_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_index.html'

    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                trace_name=trace_name,
                summary_callback_dict_component_metrics=summary_callback_dict_component_metrics,
                summary_topic_dict_componentpair_metrics=summary_topic_dict_componentpair_metrics,
                note_text_top=note_text_top,
                note_text_bottom=note_text_bottom
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)

    script_path = f'{Path(__file__).resolve().parent}/index.js'
    shutil.copy(script_path, report_dir)


def read_note_text(args) -> tuple[str, str]:
    note_text_top = None
    note_text_bottom = None
    if os.path.exists(args.note_text_top):
        with open(args.note_text_top, encoding='UTF-8') as note:
            note_text_top = note.read()
    if os.path.exists(args.note_text_bottom):
        with open(args.note_text_bottom, encoding='UTF-8') as note:
            note_text_bottom = note.read()
    return note_text_top, note_text_bottom


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--note_text_top', type=str, default='')
    parser.add_argument('--note_text_bottom', type=str, default='')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()

    report_dir = args.report_directory[0]
    note_text_top, note_text_bottom = read_note_text(args)
    make_report(report_dir, args.component_list_json, note_text_top, note_text_bottom)
    print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
