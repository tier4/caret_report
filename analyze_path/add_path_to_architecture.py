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
Script to add path information to architecture file
"""
from __future__ import annotations
import sys
import os
import argparse
import logging
import re
import json
import yaml
from caret_analyze import Architecture
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common import utils

_logger: logging.Logger = None


def find_path(arch: Architecture, target_path: list, max_node_depth: int):
    """Find target path from architecture"""
    def get_node_topic(info) -> tuple[str, str]:
        if isinstance(info, str):
            return info, None
        elif isinstance(info, list) and len(info) == 2:
            return info[0], info[1]
        _logger.error('Invalid description in JSON file')
        sys.exit(-1)

    def comm_filter(topic_name: str) -> bool:
        comm_filters = [
            re.compile(r'/tf'),
            re.compile(r'/tf_static'),
            re.compile(r'/diagnostics'),
        ]
        can_pass = True
        for comm_filter in comm_filters:
            can_pass &= not bool(comm_filter.search(topic_name))
        return can_pass

    def node_filter(node_name: str) -> bool:
        node_filters = [
            re.compile(r'/_ros2cli_/*'),
            re.compile(r'/launch_ros_*'),
        ]
        can_pass = True
        for node_filter in node_filters:
            can_pass &= not bool(node_filter.search(node_name))
        return can_pass

    # 1. Find all candidate paths which have the same start/end node as JSON
    node_src = get_node_topic(target_path[0])[0]
    node_dst = get_node_topic(target_path[-1])[0]
    _logger.info(' search paths: %s to %s', node_src, node_dst)
    path_info_list = arch.search_paths(node_src,
                                       node_dst,
                                       max_node_depth=max_node_depth,
                                       node_filter=node_filter,
                                       communication_filter=comm_filter)

    # 2. Check if all nodes/topics in the canddiate path are the same as JSON
    found_path_list = []
    for path in path_info_list:
        if len(target_path) != len(path.node_names):
            # if the len is diffrent, it's not the target path
            continue

        is_target_path = True
        node_name_list = path.node_names
        topic_name_list = path.topic_names
        for index, _ in enumerate(target_path):
            # if node_name/topic_name is different, it's not the target path
            json_node_name, json_topic_name = get_node_topic(target_path[index])

            ## Check node name
            if not re.fullmatch(json_node_name, node_name_list[index]):
                is_target_path = False
                break

            ## Check topic name when the node is not the last one and topic name is written in JSON
            if index < len(topic_name_list) and json_topic_name:
                if not re.fullmatch(json_topic_name, topic_name_list[index]):
                    is_target_path = False
                    break
        if is_target_path:
            found_path_list.append(path)

    if len(found_path_list) > 0:
        for found_path in found_path_list:
            _logger.debug(found_path.summary)
        return found_path_list
    else:
        _logger.error('Path not found')
        _logger.debug('Candidates:')
        for path in path_info_list:
            for node_name in path.node_names:
                _logger.debug(node_name)
            _logger.debug('---')
        sys.exit(-1)


def convert_context_type_to_use_latest_message(filename_src, filename_dst):
    """Convert context_type from UNDEFINED to use_latest_message"""
    yml = {}
    with open(filename_src, encoding='UTF-8') as f_yaml:
        yml = yaml.safe_load(f_yaml)
        nodes = yml['nodes']
        for node in nodes:
            if 'message_contexts' in node:
                message_contexts = node['message_contexts']
                for message_context in message_contexts:
                    if message_context['context_type'] == 'UNDEFINED':
                        message_context['context_type'] = 'use_latest_message'
    with open(filename_dst, 'w', encoding='UTF-8') as f_yaml:
        yaml.dump(yml, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)


def add_path_to_architecture(args):
    """Add path information to architecture file"""
    # Read target path information from JSON
    try:
        with open(args.target_path_json[0], encoding='UTF-8') as f_json:
            target_path_list = json.load(f_json)
    except:
        _logger.error(f'Unable to read {args.target_path_json[0]}')
        sys.exit(-1)

    # Create architecture object from architecture file or trace data
    if args.architecture_file_src:
        arch = Architecture('yaml', args.architecture_file_src)
    else:
        arch = Architecture('lttng', args.trace_data)
        arch.export('architecture_raw.yaml', force=True)

    # Find path from architecture
    for target_path in target_path_list:
        target_path_name = target_path['name']
        _logger.info(f'Processing: {target_path_name}')
        found_path_list = find_path(arch, target_path['path'], max_node_depth=args.max_node_depth)
        if len(found_path_list) > 0:
            _logger.info(f'Target path found: {target_path_name}')
            for i, found_path in enumerate(found_path_list):
                arch.add_path(target_path_name + '_' + str(i), found_path)
        else:
            _logger.error(f'Target path not found: {target_path_name}')
            sys.exit(-1)

    arch.export(args.architecture_file_dst, force=True)

    if args.use_latest_message:
        convert_context_type_to_use_latest_message(args.architecture_file_dst,
                                                   args.architecture_file_dst)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to add path information to architecture file')
    parser.add_argument('target_path_json', nargs=1, type=str)
    parser.add_argument('--trace_data', type=str, default=None)
    parser.add_argument('--architecture_file_src', type=str, default=None)
    parser.add_argument('--architecture_file_dst', type=str, default='architecture_path.yaml')
    parser.add_argument('--use_latest_message', action='store_true', default=True)
    parser.add_argument('--max_node_depth', type=int, default=20)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()

    global _logger
    if args.verbose:
        _logger = utils.create_logger(__name__, logging.DEBUG)
    else:
        _logger = utils.create_logger(__name__, logging.INFO)

    _logger.debug(f'target_path_json: {args.target_path_json[0]}')
    _logger.debug(f'trace_data: {args.trace_data}')
    _logger.debug(f'architecture_file_src: {args.architecture_file_src}')
    _logger.debug(f'architecture_file_dst: {args.architecture_file_dst}')
    _logger.debug(f'use_latest_message: {args.use_latest_message}')

    if not args.trace_data and not args.architecture_file_src:
        _logger.error('Either trace_data or architecture_file_src must be set')
        sys.exit(-1)

    add_path_to_architecture(args)
    _logger.info('<<< OK. All target paths are found >>>')


if __name__ == '__main__':
    main()
