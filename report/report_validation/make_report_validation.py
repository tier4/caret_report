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
from common.utils import read_note_text
from common.utils import ComponentManager
from common.utils_validation import make_stats_dict_node_callback_metrics, summarize_callback_result
from common.utils_validation import make_stats_dict_topic_pubsub_metrics, summarize_topic_result
from common.utils_validation import Metrics, ResultStatus


app = flask.Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')


def make_report(report_dir: str, component_list_json: str, note_text_top, note_text_bottom, link_back: str):
    ComponentManager().initialize(component_list_json)

    summary_callback_dict = {
        'cnt_pass': 0,
        'cnt_failed': 0,
    }
    summary_callback_dict_component_metrics = {}
    for component_name, _ in ComponentManager().component_dict.items():
        stats_dict_node_callback_metrics: dict = make_stats_dict_node_callback_metrics(report_dir, component_name)
        summary = summarize_callback_result(stats_dict_node_callback_metrics)
        summary_callback_dict_component_metrics[component_name] = summary
        summary_callback_dict['cnt_pass'] += summary[Metrics.FREQUENCY.name]['cnt_pass']
        summary_callback_dict['cnt_failed'] += summary[Metrics.FREQUENCY.name]['cnt_failed']

    summary_topic_dict = {
        'cnt_pass': 0,
        'cnt_failed': 0,
    }
    summary_topic_dict_component_pair_metrics = {}
    for component_pair in ComponentManager().get_component_pair_list(with_external=True):
        stats_dict_node_callback_metrics: dict = make_stats_dict_topic_pubsub_metrics(report_dir, component_pair)
        if len(stats_dict_node_callback_metrics) == 0:
            continue
        summary = summarize_topic_result(stats_dict_node_callback_metrics)
        summary_topic_dict_component_pair_metrics[component_pair[0] + '-' + component_pair[1]] = summary
        summary_topic_dict['cnt_pass'] += summary[Metrics.FREQUENCY.name]['cnt_pass']
        summary_topic_dict['cnt_failed'] += summary[Metrics.FREQUENCY.name]['cnt_failed']

    title = f'Validation report'
    destination_path = f'{report_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_report_validation.html'

    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                summary_callback_dict_component_metrics=summary_callback_dict_component_metrics,
                summary_topic_dict_component_pair_metrics=summary_topic_dict_component_pair_metrics,
                summary_callback_dict=summary_callback_dict,
                summary_topic_dict=summary_topic_dict,
                note_text_top=note_text_top,
                note_text_bottom=note_text_bottom,
                link_back=link_back
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)

    script_path = f'{Path(__file__).resolve().parent}/index.js'
    shutil.copy(script_path, report_dir)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--note_text_top', type=str, default='')
    parser.add_argument('--note_text_bottom', type=str, default='')
    parser.add_argument('--link_back', type=str, default='Back')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()

    trace_data_dir = args.trace_data[0].rstrip('/')
    dest_dir = args.dest_dir[0].rstrip('/')
    note_text_top, note_text_bottom = read_note_text(trace_data_dir, dest_dir, args.note_text_top, args.note_text_bottom)
    make_report(dest_dir, args.component_list_json, note_text_top, note_text_bottom, args.link_back)
    print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
