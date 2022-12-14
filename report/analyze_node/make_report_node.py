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


def render_page(stats, report_name, component_name, destination_path, template_path):
    """Render html page"""
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=f'{component_name}: {report_name}',
                stats=stats,
                metrics_list=['Frequency', 'Period', 'Latency'],
                metrics_unit=['[Hz]', '[ms]', '[ms]']
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)

def make_report(stats_path: str):
    """Make report page"""
    stats = None
    with open(stats_path, 'r', encoding='utf-8') as f_yaml:
        stats = yaml.safe_load(f_yaml)

    stats_dir = Path(stats_path).resolve().parent
    report_name = stats_path.split('/')[-4]
    component_name = stats_path.split('/')[-2]
    destination_path = f'{stats_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_node.html'
    render_page(stats, report_name, component_name, destination_path, template_path)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    args = parser.parse_args()
    return args


def main():
    """main function"""
    args = parse_arg()

    report_dir = args.report_directory[0]
    stats_path_list = glob.glob(f'{report_dir}/**/stats_node.yaml', recursive=True)

    if not stats_path_list:
        print('Warning. No stats file exists.', file=sys.stderr)
    else:
        for stats_path in stats_path_list:
            make_report(stats_path)
        print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
