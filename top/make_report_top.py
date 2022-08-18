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
import os
import argparse
from pathlib import Path
import yaml
import flask

app = flask.Flask(__name__)


def render_page(destination_path, template_path, report_name, package_list, stats_path):
    """Render html page"""
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title=report_name,
                package_list=package_list,
                stats_path=stats_path
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def get_package_list(report_dir: str) -> list[str]:
    """Create package name list in node analysis"""
    package_list = os.listdir(report_dir + '/node')
    package_list.sort()
    return package_list

def get_stats_path(report_dir: str):
    """Read stats"""
    with open(report_dir + '/path/stats_path.yaml', 'r', encoding='utf-8') as f_yaml:
        stats_path = yaml.safe_load(f_yaml)
    return stats_path


def make_report(report_dir: str, index_filename: str='index'):
    """Make report page"""
    package_list = get_package_list(report_dir)
    report_name = report_dir.split('/')[-1]

    stats_path = get_stats_path(report_dir)

    destination_path = f'{report_dir}/{index_filename}.html'
    template_path = f'{Path(__file__).resolve().parent}/template_report_top.html'
    render_page(destination_path, template_path, report_name, package_list, stats_path)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make report page')
    parser.add_argument('report_directory', nargs=1, type=str)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()
    report_dir = str(Path(args.report_directory[0]))
    make_report(report_dir, 'index')
    print('<<< OK. report page is created >>>')


if __name__ == '__main__':
    main()
