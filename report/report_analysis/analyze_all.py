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
Script to make analysis reports
"""
from __future__ import annotations
import sys
import os
from pathlib import Path
import argparse
from distutils.util import strtobool
import logging
from caret_analyze import Architecture, Application, Lttng
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, read_trace_data
from analyze_node import analyze_node
from analyze_path import add_path_to_architecture, analyze_path
from find_valid_duration import find_valid_duration



def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make analysis reports')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--start_strip', type=float, default=0.0,
                        help='Start strip [sec] to load trace data')
    parser.add_argument('--end_strip', type=float, default=0.0,
                        help='End strip [sec] to load trace data')
    parser.add_argument('--sim_time', type=strtobool, default=False)
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='Overwrite report directory')
    parser.add_argument('-v', '--verbose', action='store_true', default=False)

    # options for add_path
    parser.add_argument('--target_path_json', type=str, default='target_path.json')
    parser.add_argument('--architecture_file_path', type=str, default='architecture_path.yaml')
    parser.add_argument('--use_latest_message', action='store_true', default=True)
    parser.add_argument('--max_node_depth', type=int, default=15)
    parser.add_argument('--timeout', type=int, default=120)

    # options for path analysis
    parser.add_argument('-m', '--message_flow', type=strtobool, default=False,
                        help='Output message flow graph')

    # options for find_valid_duration
    parser.add_argument('--find_valid_duration', type=strtobool, default=False)
    parser.add_argument('--duration', type=float, default=1200.0,
                        help='Duration [sec] to load trace data')
    parser.add_argument('--skip_first_num', type=int, default=1,
                        help='The number to skip the first n-th trace data')

    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()
    logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    args.trace_data = args.trace_data[0]
    logger.debug(f'trace_data: {args.trace_data}')
    args.dest_dir = args.dest_dir[0]
    logger.debug(f'dest_dir: {args.dest_dir}')
    logger.debug(f'component_list_json: {args.component_list_json}')
    logger.debug(f'start_strip: {args.start_strip}, end_strip: {args.end_strip}')
    logger.debug(f'sim_time: {args.sim_time}')
    logger.debug(f'target_path_json: {args.target_path_json}')
    logger.debug(f'architecture_file_path: {args.architecture_file_path}')
    logger.debug(f'use_latest_message: {args.use_latest_message}')
    logger.debug(f'max_node_depth: {args.max_node_depth}')
    logger.debug(f'timeout: {args.timeout}')
    args.message_flow = True if args.message_flow == 1 else False
    logger.debug(f'message_flow: {args.message_flow}')
    logger.debug(f'find_valid_duration: {args.find_valid_duration}')
    logger.debug(f'duration: {args.duration}')
    logger.debug(f'skip_first_num: {args.skip_first_num}')

    # Read trace data
    lttng = read_trace_data(args.trace_data, args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', args.trace_data)

    # Create architecture for path analysis
    add_path_to_architecture.add_path_to_architecture(args, arch)
    arch_path = Architecture('yaml', args.architecture_file_path)
    app = Application(arch_path, lttng)

    # Find duration to be analyzed
    #  Run path analysis and find start point(sec) where the topic runs in the paths
    if args.find_valid_duration:
        start_strip, end_strip = find_valid_duration.analyze(args, lttng, arch_path, app)
        args.start_strip = start_strip
        args.end_strip = end_strip
        logger.info(f'Find valid duration. start_strip: {args.start_strip}, end_strip: {args.end_strip}')
        logger.info(f'Reload trace data')
        lttng = read_trace_data(args.trace_data, args.start_strip, args.end_strip, False)
        app = Application(arch_path, lttng)

    # Analyze
    analyze_path.analyze(args, lttng, arch_path, app, args.dest_dir + '/analyze_path')
    analyze_node.analyze(args, lttng, arch, app, args.dest_dir + '/analyze_node')


if __name__ == '__main__':
    main()
