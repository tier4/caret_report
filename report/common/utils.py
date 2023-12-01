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
Utility functions
"""
from __future__ import annotations
import datetime
import os
import sys
import shutil
import logging
import re
import json
import itertools
import pandas as pd
import subprocess
import yaml
from caret_analyze import Application, Lttng, LttngEventFilter
from caret_analyze.runtime.callback import CallbackBase, CallbackType
from caret_analyze.runtime.node import Node
from bokeh.plotting import figure, save
from bokeh.resources import CDN
from bokeh.io import export_png


def create_logger(name, level: int=logging.DEBUG, log_filename: str=None) -> logging.Logger:
    """Create logger"""
    handler_format = logging.Formatter(
        '[%(asctime)s][%(levelname)-7s][%(filename)s:%(lineno)s] %(message)s')
    stream_handler = logging .StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(handler_format)
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(level)
    logger.addHandler(stream_handler)
    if log_filename:
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(level)
        file_handler.setFormatter(handler_format)
        logger.addHandler(file_handler)
    return logger


def make_destination_dir(dest_dir: str, force: bool=False, logger: logging.Logger=None):
    """Make directory"""
    if not os.path.isdir(dest_dir):
        os.makedirs(dest_dir)
    else:
        if force:
            shutil.rmtree(dest_dir)
            os.makedirs(dest_dir)
        else:
            pass
            # if logger:
            #     logger.error('Destination has already existed')
            # sys.exit(-1)


def read_trace_data(trace_data: str, start_strip: float, end_strip: float,
                    force_conversion=False) -> Lttng:
    """Read LTTng trace data"""
    return Lttng(trace_data, force_conversion=force_conversion, event_filters=[
        LttngEventFilter.strip_filter(start_strip, end_strip)
    ])


def read_trace_data_duration(trace_data: str, start_point: float, duration: float,
                    force_conversion=False) -> Lttng:
    """Read LTTng trace data"""
    if start_point > 0 and duration == 0:
        return Lttng(trace_data, force_conversion=force_conversion, event_filters=[
            LttngEventFilter.strip_filter(start_point, None)
        ])
    elif start_point >= 0 and duration > 0:
        return Lttng(trace_data, force_conversion=force_conversion, event_filters=[
            LttngEventFilter.duration_filter(duration, start_point)
        ])
    else:
        return Lttng(trace_data, force_conversion=force_conversion)


def get_callback_legend(node: Node, callback_name: str, with_trigger: bool=True) -> str:
    callback_legend_dict = {}
    cnt_timer = 0
    cnt_subscription = 0
    for callback in node.callbacks:
        if callback.callback_type == CallbackType.TIMER:
            period_ms = callback.timer.period_ns * 1e-6
            legend = f'timer_{cnt_timer}'
            if with_trigger:
                legend += f': {period_ms}ms'
            callback_legend_dict[callback.callback_name] = legend
            cnt_timer += 1
        else:
            legend = f'subscription_{cnt_subscription}'
            if with_trigger:
                legend += f': {callback.subscribe_topic_name}'
            callback_legend_dict[callback.callback_name] = legend
            cnt_subscription += 1

    if callback_name in callback_legend_dict:
        callback_legend = callback_legend_dict[callback_name]
    else:
        callback_legend = callback_name

    return callback_legend


def export_graph(figure: figure, dest_dir: str, filename: str, title='graph',
                 with_png=True, logger: logging.Logger = None) -> None:
    """Export graph as html and image"""
    save(figure, filename=f'{dest_dir}/{filename}.html', title=title, resources=CDN)
    try:
        if with_png:
            export_png(figure, filename=f'{dest_dir}/{filename}.png')
    except:
        if logger:
            logger.warning('Unable to export png')


def trail_df(df: pd.DataFrame, trail_val=0, start_strip_num=0, end_strip_num=0) -> pd.DataFrame:
    df = df.dropna()
    cnt_trail = start_strip_num
    for val in df:
        if val == trail_val:
            cnt_trail += 1
        else:
            break
    if cnt_trail > 0:
        df = df.iloc[cnt_trail:]

    cnt_trail = end_strip_num
    for val in df.iloc[::-1]:
        if val == trail_val:
            cnt_trail += 1
        else:
            break
    if cnt_trail > 0:
        df = df.iloc[:-cnt_trail]

    return df


def round_yaml(filename):
    '''Round float value in yaml file'''
    with open(filename, 'r', encoding='utf-8') as f_yaml:
        lines = f_yaml.readlines()
        for i, line in enumerate(lines):
            line_split = line.split()
            for val in line_split:
                try:
                    new_val = float(val)
                    new_val = f'{round(new_val, 3): .03f}'.strip()
                    lines[i] = line.replace(val, new_val)
                except:
                    pass
    new_yaml = ''.join(lines)
    with open(filename, 'w', encoding='utf-8') as f_yaml:
        f_yaml.write(new_yaml)


class ComponentManager:
    def __new__(cls, *args, **kargs):
        if not hasattr(cls, "_instance"):
            cls._instance = super(ComponentManager, cls).__new__(cls)
            cls.component_dict = {}  # pairs of component name and regular_exp
            cls.external_in_topic_list = []
            cls.external_out_topic_list = []
            cls.ignore_list = []
        return cls._instance

    def initialize(self, component_list_json_path: str, logger: logging.Logger = None):
        """make component list"""
        component_list_json = ''
        if component_list_json_path != '':
            try:
                with open(component_list_json_path, encoding='UTF-8') as f_json:
                    component_list_json = json.load(f_json)
            except:
                if logger:
                    logger.error(f'Unable to read {component_list_json_path}')
                else:
                    print(f'Unable to read {component_list_json_path}')

        if component_list_json == '':
            self.component_dict = {
                'all': r'.*'
            }
        else:
            if 'component_dict' in component_list_json:
                self.component_dict = component_list_json['component_dict']
            if 'external_in_topic_list' in component_list_json:
                self.external_in_topic_list = component_list_json['external_in_topic_list']
            if 'external_out_topic_list' in component_list_json:
                self.external_out_topic_list = component_list_json['external_out_topic_list']
            if 'ignore_list' in component_list_json:
                self.ignore_list = component_list_json['ignore_list']

        if logger:
            logger.debug(f'component_dict = {self.component_dict}')
            logger.debug(f'external_in_topic_list = {self.external_in_topic_list}')
            logger.debug(f'external_out_topic_list = {self.external_out_topic_list}')
            logger.debug(f'ignore_list = {self.ignore_list}')

    def get_component_name(self, node_name: str) -> str:
        for component_name, regexp in self.component_dict.items():
            if re.search(regexp, node_name):
                return component_name
        return 'other'

    def check_if_external_in_topic(self, topic_name: str, sub_node_name: str='') -> bool:
        for topic_regexp, node_regexp in self.external_in_topic_list:
            if re.search(topic_regexp, topic_name):
                if (sub_node_name != '') and (node_regexp != '') and (not re.search(node_regexp, sub_node_name)):
                    continue
                return True
        return False

    def check_if_external_out_topic(self, topic_name: str, pub_node_name: str='') -> bool:
        for topic_regexp, node_regexp in self.external_out_topic_list:
            if re.search(topic_regexp, topic_name):
                if (pub_node_name != '') and (node_regexp != '') and (not re.search(node_regexp, pub_node_name)):
                    continue
                return True
        return False

    def get_component_pair_list(self, with_external: bool=False) -> list[str, str]:
        component_name_list = list(self.component_dict.keys())
        if with_external:
            component_name_list.append('external')
        component_pair_list = itertools.product(component_name_list, component_name_list)
        component_pair_list = [component_pair for component_pair in component_pair_list
                                if component_pair[0] != component_pair[1]]
        return component_pair_list

    def check_if_ignore(self, node_name: str) -> bool:
        for ignore in self.ignore_list:
            if re.search(ignore, node_name):
                return True
        return False

    def check_if_target(self, component_name: str, node_name: str) -> bool:
        if node_name is None:
            return False
        if self.check_if_ignore(node_name):
            return False
        if component_name == self.get_component_name(node_name):
            return True
        return False


def read_note_text(trace_data_dir, dest_dir, note_text_top_path, note_text_bottom_path) -> tuple[str, str]:
    note_text_top = ''
    note_text_bottom = ''
    if os.path.exists(note_text_top_path):
        with open(note_text_top_path, encoding='UTF-8') as note:
            note_text_top = note.read()
    if os.path.exists(note_text_bottom_path):
        with open(note_text_bottom_path, encoding='UTF-8') as note:
            note_text_bottom = note.read()

    note_text_top += '<ul>\n'
    # trace data info
    trace_data_name = trace_data_dir.split('/')[-1]
    trace_datetime = re.search(r'\d{14}', trace_data_name)
    if trace_datetime:
        trace_datetime = datetime.datetime.strptime(trace_datetime.group(), '%Y%m%d%H%M%S')
    else:
        trace_datetime = re.search(r'\d{8}-\d{6}', trace_data_name)
        if trace_datetime:
            trace_datetime = datetime.datetime.strptime(trace_datetime.group(), '%Y%m%d-%H%M%S')
        else:
            trace_datetime = 'unknown'
    note_text_top += f'<li>trace_data: {trace_data_name}</li>\n'
    note_text_top += f'<li>trace_start_datetime: {trace_datetime}</li>\n'

    # version info
    try:
        caret_analysis_version = subprocess.run(['ros2', 'caret', 'version'], text=True, stdout=subprocess.PIPE).stdout
    except:
        caret_analysis_version = 'unknown'
    note_text_top += f'<li>caret_analysis_version: {caret_analysis_version}</li>\n'

    try:
        repo_url_lines = subprocess.run(['git', 'remote', '-v'], text=True, stdout=subprocess.PIPE).stdout
        repo_url_line = repo_url_lines.split('\n')[0]
        repo_name = 'unknown'
        for repo_url in repo_url_line.split():
            if ('https://' in repo_url or 'git@' in repo_url) and '.git' in repo_url:
                repo_url = repo_url.split('/')[-1]
                repo_name = repo_url.split('.git')[0]
        report_setting_version = subprocess.run(['git', 'log', '-n 1', '--format=%H'], text=True, stdout=subprocess.PIPE).stdout
    except:
        repo_name = 'unknown'
        report_setting_version = 'unknown'
    note_text_top += f'<li>report_setting_repo: {repo_name}</li>\n'
    note_text_top += f'<li>report_setting_version: {report_setting_version}</li>\n'
    note_text_top += '</ul>\n'

    # overwrite note_text_top if caret_record_info.yaml exists
    caret_record_info_path = f'{dest_dir}/caret_record_info.yaml'
    if os.path.exists(caret_record_info_path):
        with open(caret_record_info_path, encoding='UTF-8') as f_yaml:
            note_text_top = '<ul>\n'
            note_text_top += f'<li>trace_data: {trace_data_name}</li>\n'
            note_text_top += f'<li>trace_start_datetime: {trace_datetime}</li>\n'
            caret_record_info = yaml.safe_load(f_yaml)
            if 'caret_version' in caret_record_info:
                caret_record_info['caret_version'] = caret_record_info.pop('caret_version')
            for key, value in caret_record_info.items():
                note_text_top += f'<li>{key}: {value}</li>\n'
            note_text_top += f'<li>caret_analysis_version: {caret_analysis_version}</li>\n'
            note_text_top += f'<li>report_setting_repo: {repo_name}</li>\n'
            note_text_top += f'<li>report_setting_version: {report_setting_version}</li>\n'
            note_text_top += '</ul>\n'

    return note_text_top, note_text_bottom
