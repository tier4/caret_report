# Copyright 2023 Tier IV, Inc.
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
import glob
import math
import logging
import csv
import yaml
import numpy as np
import pandas as pd
from caret_analyze import Architecture
from anytree import Node, RenderTree
import flask

_logger = logging.Logger(__name__)
app = flask.Flask(__name__)


def render_page(trace_list, destination_path, template_path):
    """Render html page"""
    with app.app_context():
        with open(template_path, 'r', encoding='utf-8') as f_html:
            template_string = f_html.read()
            rendered = flask.render_template_string(
                template_string,
                title='Failure Trace',
                trace_list=trace_list,
            )

        with open(destination_path, 'w', encoding='utf-8') as f_html:
            f_html.write(rendered)


def tree_check_if_contained_as_descendants(name: str, root: Node) -> bool:
    name_list = [descendant.name for descendant in root.descendants]
    for child in root.children:
        name_list.remove(child.name)
    return name in name_list


def tree_check_if_contained_as_children(name: str, root: Node) -> bool:
    name_list = [child.name for child in root.children]
    return name in name_list


def tree_delete_node(name: str, root: Node):
    for child in root.children:
        if child.name == name:
            child.parent = None


def search_publishers(arch: Architecture, topic_name: str, subscribe_node_name: str) -> list[str]:
    # Initialize dict (use dict for speed performance)
    if len(search_publishers.comm_dict) == 0:
        for comm in arch.communications:
            if comm.topic_name not in search_publishers.comm_dict:
                search_publishers.comm_dict[comm.topic_name] = []
            if comm not in search_publishers.comm_dict[comm.topic_name]:
                search_publishers.comm_dict[comm.topic_name].append(comm)
    if topic_name not in search_publishers.comm_dict:
        return []
    publisher_list = [comm.publish_node_name for comm in search_publishers.comm_dict[topic_name] if comm.subscribe_node_name == subscribe_node_name]
    # publisher_list = [comm.publish_node_name for comm in arch.communications
    #     if comm.topic_name == topic_name
    #     and comm.subscribe_node_name == subscribe_node_name]
    return publisher_list
search_publishers.comm_dict = {}


def get_callback_legend(callback_name: str, callback_stats_list: list[dict]) -> tuple[str]:     # return node_name, trigger
    for callback_stats in callback_stats_list:
        if callback_stats['stats']['callback_name'] == callback_name:
            node_name = callback_stats['stats']['node_name']
            period_ns = callback_stats['stats']['period_ns']
            subscribe_topic_name = callback_stats['stats']['subscribe_topic_name']
            if period_ns == -1:
                return node_name, f'subscription cb: {subscribe_topic_name}'
            else:
                return node_name, f'timer cb: {period_ns*1e-6}ms'
    return callback_name, '---'


def get_callback_stats_list(node_name: str, callback_stats_list: list[dict]):
    found_list = [callback_stats for callback_stats in callback_stats_list if callback_stats['stats']['node_name'] == node_name]
    return found_list


def trace_failure_node(parent: Node, arch: Architecture, node_name: str, callback_stats_list: list[dict]):
    found_list = get_callback_stats_list(node_name, callback_stats_list)
    for callback_stats in found_list:
        result_status = callback_stats['result_status']
        if result_status == 'FAILED' or result_status == 'NOT_MEASURED':
            node_name = callback_stats['stats']['node_name']
            callback_name = callback_stats['stats']['callback_name']
            period_ns = callback_stats['stats']['period_ns']
            subscribe_topic_name = callback_stats['stats']['subscribe_topic_name']
            node = Node(callback_name, parent=parent)
            if result_status == 'NOT_MEASURED':
                _logger.warning(f'{callback_name} is not measured but treated as FAILED')
            if node.depth > 100:
                _logger.error(f'Too depth: {parent.name} -> {callback_name}')
                continue
            if period_ns != -1:
                # end
                pass
            else:
                publisher_list = search_publishers(arch, subscribe_topic_name, node_name)
                for publisher in publisher_list:
                    trace_failure_node(node, arch, publisher, callback_stats_list)


def trace_failure(callback_stats_list: list[dict], arch: Architecture):
    tree_root = Node('root')
    for callback_stats in callback_stats_list:
        result_status = callback_stats['result_status']
        if result_status == 'FAILED':
            node_name = callback_stats['stats']['node_name']
            callback_name = callback_stats['stats']['callback_name']
            period_ns = callback_stats['stats']['period_ns']
            subscribe_topic_name = callback_stats['stats']['subscribe_topic_name']
            if not tree_check_if_contained_as_descendants(callback_name, tree_root):
                # check if the current callback is already contained in the tree
                tree_new_node = Node(callback_name, Node('temp_root'))
                if period_ns == -1:
                    publisher_list = search_publishers(arch, subscribe_topic_name, node_name)
                    for publisher in publisher_list:
                        trace_failure_node(tree_new_node, arch, publisher, callback_stats_list)
                for descendant in tree_new_node.descendants:
                    # check if the temp tree contains the callback already added as child. If so, delete the child
                    if tree_check_if_contained_as_children(descendant.name, tree_root):
                        tree_delete_node(descendant.name, tree_root)
                tree_new_node.parent = tree_root
    return tree_root


def create_stats_list(stats_file_list: list[str]) -> list[dict]:
    '''Create stats list from stats files'''
    stats_list = []
    for stats_file in stats_file_list:
        with open(stats_file, 'r') as f:
            read_stats = yaml.load(f, Loader=yaml.SafeLoader)
            stats_list.extend(read_stats)
    return stats_list


def get_color_for_callback(callback_name: str):
    color_list = ['blue', 'red', 'green', 'purple', 'orange', 'brown', 'pink', 'olive', 'cyan', 'fuchsia', 'lime', 'teal', 'aqua', 'maroon', 'navy', 'silver', 'yellow', 'gray']
    if callback_name not in get_color_for_callback.color_index_dict:
        get_color_for_callback.color_index_dict[callback_name] = len(get_color_for_callback.color_index_dict) % len(color_list)
    color_index = get_color_for_callback.color_index_dict[callback_name]
    return color_list[color_index]
get_color_for_callback.color_index_dict = {}


def create_trace_list(dest_dir: str, report_dir: str):
    callback_stats_file_list = glob.glob(f'{report_dir}/validate_callback/**/stats_FREQUENCY.yaml', recursive=True)
    callback_stats_list = create_stats_list(callback_stats_file_list)
    # topic_stats_file_list = glob.glob(f'{report_dir}/validate_topic/**/stats_FREQUENCY.yaml', recursive=True)
    # topic_stats_list = create_stats_list(topic_stats_file_list)

    arch = Architecture('yaml', report_dir + '/architecture.yaml')
    tree_root = trace_failure(callback_stats_list, arch)

    # for pre, fill, node in RenderTree(tree_root):
    #     print("%s%s" % (pre, get_callback_legend(node.name, callback_stats_list)))

    # tree -> list
    trace_list = []
    for last_callback in tree_root.children:
        trace = []
        for pre, fill, tree_node in RenderTree(last_callback):
            callback_name = tree_node.name
            node_name, trigger = get_callback_legend(callback_name, callback_stats_list)
            node_html_name = node_name.replace('/', '_')[1:] + '.html'
            node_html = glob.glob(f'{report_dir}/validate_callback/**/{node_html_name}', recursive=True)
            if len(node_html) > 0 and os.path.isfile(node_html[0]):
                node_html = os.path.relpath(node_html[0], Path(dest_dir).resolve())
            else:
                node_html = ''
            color = 'black'
            if tree_node.is_leaf:
                color = get_color_for_callback(callback_name)
            line = {
                'pre': pre,
                'callback_name': callback_name,
                'node_name': node_name,
                'trigger': trigger,
                'node_html': node_html,
                'color': color,
            }
            trace.append(line)
        trace_list.append(trace)

    return trace_list


def make_report(dest_dir: str, report_dir: str):
    """Make report page"""
    trace_list = create_trace_list(dest_dir, report_dir)

    destination_path = f'{dest_dir}/index.html'
    template_path = f'{Path(__file__).resolve().parent}/template_trace_validation_failure.html'
    render_page(trace_list, destination_path, template_path)


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
    dest_dir = report_dir + '/trace_validation_failure'
    _logger.info(f'dest_dir: {dest_dir}')
    os.makedirs(dest_dir, exist_ok=True)

    make_report(dest_dir, report_dir)

    print('<<< OK. report_trace_validation_failure is created >>>')


if __name__ == '__main__':
    main()
