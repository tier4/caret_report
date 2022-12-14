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
import os
import sys
import shutil
import logging
import re
import json
from caret_analyze import Lttng, LttngEventFilter
from caret_analyze.runtime.callback import CallbackBase
from bokeh.plotting import Figure, save
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
            if logger:
                logger.error('Destination has already existed')
            sys.exit(-1)


def read_trace_data(trace_data: str, start_point: float, duration: float,
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


def make_callback_displayname(callback: CallbackBase) -> str:
    """Make callback name to be displayed"""
    displayname = callback.callback_name.split('/')[-1]
    callback_type = callback.callback_type.type_name
    if 'timer' in callback_type:
        period_ms = callback.timer.period_ns * 1e-6
        displayname = f'Timer_{period_ms}ms'
    elif 'subscription' in callback_type:
        displayname = 'Sub_' + str(callback.subscribe_topic_name)
    return displayname


def export_graph(figure: Figure, dest_dir: str, filename: str, title='graph',
                 logger: logging.Logger = None) -> None:
    """Export graph as html and image"""
    save(figure, filename=f'{dest_dir}/{filename}.html', title=title, resources=CDN)
    try:
        export_png(figure, filename=f'{dest_dir}/{filename}.png')
    except:
        if logger:
            logger.warning('Unable to export png')


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
            self.component_dict = component_list_json['component_dict']
            self.ignore_list = component_list_json['ignore_list']

        if logger:
            logger.debug(f'component_dict = {self.component_dict}')
            logger.debug(f'ignore_list = {self.ignore_list}')

    def get_component_name(self, node_name: str) -> str:
        for component_name, regexp in self.component_dict.items():
            if re.search(regexp, node_name):
                return component_name
        return ''

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

        regexp = self.component_dict[component_name]
        if re.search(regexp, node_name):
            return True
        return False
