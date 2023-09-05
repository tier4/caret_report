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
from __future__ import annotations
import sys
import os
import argparse
from pathlib import Path
import yaml
import flask
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import ComponentManager
from common.utils import read_note_text

app = flask.Flask(__name__)


def render_page(trace_data_dir, destination_path, template_path, component_list, stats_node_dict,
                stats_path, note_text_top, note_text_bottom):
    """Render html page"""
    title = f'Analysis report'
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                component_list=component_list,
                stats_node_dict=stats_node_dict,
                stats_path=stats_path,
                note_text_top=note_text_top,
                note_text_bottom=note_text_bottom
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def get_component_list(report_dir: str) -> list[str]:
    """Create component name list in node analysis"""
    node_report_dir= report_dir + '/analyze_node'

    component_list = []
    for component_name, _ in ComponentManager().component_dict.items():
        if os.path.isdir(os.path.join(node_report_dir, component_name)):
            component_list.append(component_name)
    return component_list


def get_stats_node(report_dir: str) -> dict:
    """Read stats"""
    stats_dict = {}
    component_list = get_component_list(report_dir)
    for component_name in component_list:
        with open(report_dir + '/analyze_node/' + component_name + '/stats_node.yaml', 'r', encoding='utf-8') as f_yaml:
            stats = yaml.safe_load(f_yaml)
            stats_dict[component_name] = stats
    return stats_dict


def get_stats_path(report_dir: str):
    """Read stats"""
    with open(report_dir + '/analyze_path/stats_path.yaml', 'r', encoding='utf-8') as f_yaml:
        stats = yaml.safe_load(f_yaml)
    return stats


def find_latency_topk(component_name, stats_node, numk=20) -> None:
    """Find callback functions whose latency time is the longest(top5), and add this information into stats"""
    callback_latency_list = []
    for node_name, node_info in stats_node.items():
        callbacks = node_info['callbacks']
        for _, callback_info in callbacks.items():
            trigger = callback_info['subscribe_topic_name'] if callback_info['period_ns'] == -1 else f'{float(callback_info["period_ns"]) / 1e6} [ms]'
            callback_latency_list.append({
                'link': f'analyze_node/{component_name}/index{node_name.replace("/", "_")}.html',
                'displayname': flask.Markup(node_name + '<br>' + callback_info['callback_legend'] + ': ' + trigger),
                'avg': callback_info['Latency']['avg'] if isinstance(callback_info['Latency']['avg'], (int, float)) else 0,
                'min': callback_info['Latency']['min'] if isinstance(callback_info['Latency']['min'], (int, float)) else 0,
                'max': callback_info['Latency']['max'] if isinstance(callback_info['Latency']['max'], (int, float)) else 0,
                'p50': callback_info['Latency']['p50'] if isinstance(callback_info['Latency']['p50'], (int, float)) else 0,
                'p95': callback_info['Latency']['p95'] if isinstance(callback_info['Latency']['p95'], (int, float)) else 0,
                'p99': callback_info['Latency']['p99'] if isinstance(callback_info['Latency']['p99'], (int, float)) else 0,
            })

    callback_latency_list = sorted(callback_latency_list, reverse=True, key=lambda x: x['p50'])
    callback_latency_list = callback_latency_list[:numk]
    stats_node['latency_topk'] = callback_latency_list


def make_report(args, index_filename: str='index'):
    """Make report page"""
    trace_data_dir = args.trace_data[0].rstrip('/')
    dest_dir = args.dest_dir[0].rstrip('/')
    ComponentManager().initialize('component_list.json')

    component_list = get_component_list(dest_dir)
    stats_node_dict = get_stats_node(dest_dir)
    for component_name in component_list:
        find_latency_topk(component_name, stats_node_dict[component_name])

    stats_path = get_stats_path(dest_dir)

    note_text_top, note_text_bottom = read_note_text(trace_data_dir, args.note_text_top, args.note_text_bottom)

    destination_path = f'{dest_dir}/{index_filename}.html'
    template_path = f'{Path(__file__).resolve().parent}/template_report_analysis.html'
    render_page(trace_data_dir, destination_path, template_path, component_list, stats_node_dict,
                stats_path, note_text_top, note_text_bottom)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--note_text_top', type=str, default='')
    parser.add_argument('--note_text_bottom', type=str, default='')
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()
    make_report(args, 'index')
    print('<<< OK. report_analysis is created >>>')


if __name__ == '__main__':
    main()
