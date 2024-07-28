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
import glob
import argparse
from pathlib import Path
import sys
import yaml
import flask

app = flask.Flask(__name__)


def render_index_page(dest_path: Path, title: str, sub_title: str, topic_name_list: list[str], topic_html_list: list[str]):
    """Render html page"""
    template_path = f'{Path(__file__).resolve().parent}/template_topic_index.html'
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                sub_title=sub_title,
                topic_name_list=topic_name_list,
                topic_html_list=topic_html_list,
            )
        with open(dest_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)



def render_detail_page(dest_path: Path, data_path: str, title: str, sub_title: str, stats_freq: list[dict], stats_period: list[dict], stats_latency: list[dict], node_html_dict: dict[str, Path]):
    """Render html page"""
    template_path = f'{Path(__file__).resolve().parent}/template_topic_detail.html'
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=title,
                sub_title=sub_title,
                data_path=data_path,
                stats_list=[stats_freq, stats_period, stats_latency],
                metrics_list=['Frequency', 'Period', 'Latency'],
                metrics_unit_list=['[Hz]', '[ms]', '[ms]'],
                node_html_dict=node_html_dict,
            )
        with open(dest_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def make_pages_for_component(path_component: Path, report_name: str, node_html_dict: dict[str, Path]):
    topic_path_list = sorted([d for d in path_component.iterdir() if d.is_dir()])
    topic_html_list = [topic_path.name + '.html' for topic_path in topic_path_list]
    topic_name_list = []
    for i, topic_path in enumerate(topic_path_list):
        with open(topic_path.joinpath('stats_FREQUENCY.yaml'), 'r', encoding='utf-8') as f_yaml_freq, \
                open(topic_path.joinpath('stats_PERIOD.yaml'), 'r', encoding='utf-8') as f_yaml_period, \
                open(topic_path.joinpath('stats_LATENCY.yaml'), 'r', encoding='utf-8') as f_yaml_latency:
            stats_freq = yaml.safe_load(f_yaml_freq)
            stats_period = yaml.safe_load(f_yaml_period)
            stats_latency = yaml.safe_load(f_yaml_latency)
            if len(stats_freq) == 0:
                continue
            topic_name = stats_freq[0]['topic_name']
            topic_name_list.append(topic_name)
            render_detail_page(path_component.joinpath(topic_html_list[i]), topic_path.name, f'Topic: {topic_name}', report_name, stats_freq, stats_period, stats_latency, node_html_dict)

    render_index_page(path_component.joinpath('index.html'), f'Topic: {path_component.name}', report_name, topic_name_list, topic_html_list)


def create_node_html_dict(dest_dir: Path) -> dict[str, str]:
    node_dir = dest_dir.parent.joinpath('analyze_node')
    node_html_dict: dict[str, str] = {}
    node_html_path = glob.glob(f'{node_dir}/**/index_*.html', recursive=True)
    for path in node_html_path:
        path = Path(path)
        node_name = path.name.lstrip('index').rstrip('.html')
        node_html_dict[node_name] = Path('../../').joinpath(path.absolute().relative_to(dest_dir.absolute().parent))
    return node_html_dict


def make_report(dest_dir: str):
    """Make report page"""
    dest_dir = Path(dest_dir)
    report_name = dest_dir.parent.name
    node_html_dict = create_node_html_dict(dest_dir)

    path_component_list = [d for d in dest_dir.iterdir() if d.is_dir()]
    for path_component in path_component_list:
        make_pages_for_component(path_component, report_name, node_html_dict)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('dest_dir', nargs=1, type=str)
    args = parser.parse_args()
    return args


def main():
    """main function"""
    args = parse_arg()

    dest_dir = args.dest_dir[0]
    make_report(dest_dir + '/analyze_topic')

if __name__ == '__main__':
    main()
