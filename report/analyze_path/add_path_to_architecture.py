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
import threading
import re
import json
import yaml
from caret_analyze import Architecture
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def find_path(arch: Architecture, target_path_json: list, max_node_depth: int, timeout: int):
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

    def search_paths_with_timeout(arch, node_names, max_node_depth, timeout) -> list:
        def search_paths(arch, node_names, max_node_depth, result_obj):
            try:
                result_obj['result'] = arch.search_paths(*node_names, max_node_depth=max_node_depth,
                                                        node_filter=node_filter, communication_filter=comm_filter)
            except:
                _logger.error(f'path not found: {node_names}')
                result_obj['result'] = []

        result_obj = {}
        thread = threading.Thread(target=search_paths, args=(arch, node_names, max_node_depth, result_obj), daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        if thread.is_alive():
            return None
        return result_obj['result']

    # Find all candidate paths which have the same nodes as JSON
    found_path_list = []
    node_name_list = []
    for node_topic in target_path_json:
        node_name = get_node_topic(node_topic)[0]
        if '[' not in node_name and '.' not in node_name and '*' not in node_name:
            # collect node name which doesn't contain regular expressions
            node_name_list.append(node_name)
    for depth in range(3, max_node_depth):
        found_path_list = search_paths_with_timeout(arch, node_name_list, max_node_depth=depth, timeout=timeout)
        if found_path_list is None:
            _logger.warning('Timeout happens. Please specify more details for the path')
            break
        _logger.info(f'found path num = {len(found_path_list)}')

        # remove path which contains loop
        for found_path in found_path_list.copy():
            node_list = [node for node in found_path.node_names]
            if len(node_list) != len(set(node_list)):
                found_path_list.remove(found_path)

        # check node name and topic name(if available)
        for found_path in found_path_list.copy():
            node_name_list = found_path.node_names
            topic_name_list = found_path.topic_names
            for index, _ in enumerate(target_path_json):
                json_node_name, json_topic_name = get_node_topic(target_path_json[index])
                is_ok = False
                for index, node_name in enumerate(node_name_list):
                    if re.fullmatch(json_node_name, node_name):
                        is_ok =True
                        if json_topic_name:
                            # check topic name (sub or pub) if available
                            if index > 0:
                                # check sub topic name
                                is_ok = re.fullmatch(json_topic_name, topic_name_list[index-1])
                            if index < len(topic_name_list):
                                # check pub topic name
                                is_ok = is_ok or re.fullmatch(json_topic_name, topic_name_list[index])
                    if is_ok:
                        break
                if not is_ok:
                    found_path_list.remove(found_path)
                    break

        _logger.info(f'checked path num = {len(found_path_list)}')
        if len(found_path_list) > 0:
            break

    if found_path_list is not None and len(found_path_list) > 0:
        for found_path in found_path_list:
            _logger.debug(found_path.summary)
        return found_path_list
    else:
        _logger.error('Path not found. Check target_path.json, or consider to increase max_node_depth and timeout.')
        return []


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


def add_path_to_architecture(args, arch: Architecture):
    """Add path information to architecture file"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Add Path: Start >>>')
    # Read target path information from JSON
    try:
        with open(args.target_path_json[0], encoding='UTF-8') as f_json:
            target_path_list = json.load(f_json)
    except:
        _logger.error(f'Unable to read {args.target_path_json[0]}')
        sys.exit(-1)

    # arch.export('architecture_raw.yaml', force=True)

    # Find path from architecture
    for target_path in target_path_list:
        target_path_name = target_path['name']
        _logger.info(f'Processing: {target_path_name}')
        found_path_list = find_path(arch, target_path['path'], max_node_depth=args.max_node_depth, timeout=args.timeout)
        if len(found_path_list) > 0:
            _logger.info(f'Target path found: {target_path_name}')
            for i, found_path in enumerate(found_path_list):
                arch.add_path(target_path_name + '_' + str(i), found_path)
        else:
            _logger.error(f'Target path not found: {target_path_name}')
            # sys.exit(-1)

    arch.export(args.architecture_file_path, force=True)

    if args.use_latest_message:
        convert_context_type_to_use_latest_message(args.architecture_file_path,
                                                   args.architecture_file_path)

    _logger.info('<<< Add Path: Finish >>>')

def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to add path information to architecture file')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('target_path_json', nargs=1, type=str)
    parser.add_argument('--architecture_file_path', type=str, default='architecture_path.yaml')
    parser.add_argument('--use_latest_message', action='store_true', default=True)
    parser.add_argument('--max_node_depth', type=int, default=15)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    global _logger
    args = parse_arg()
    _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'target_path_json: {args.target_path_json[0]}')
    _logger.debug(f'architecture_file_path: {args.architecture_file_path}')
    _logger.debug(f'use_latest_message: {args.use_latest_message}')
    _logger.debug(f'max_node_depth: {args.max_node_depth}')
    _logger.debug(f'timeout: {args.timeout}')

    arch = Architecture('lttng', str(args.trace_data[0]))

    add_path_to_architecture(args, arch)


if __name__ == '__main__':
    main()
