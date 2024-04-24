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
Script to make validation reports
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
from validate_topic import generate_expectation_list, validate_topic
from validate_callback import validate_callback
from analyze_path import add_path_to_architecture, analyze_path
from find_valid_duration import find_valid_duration



def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make validation reports')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('dest_dir', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--start_strip', type=float, default=0.0,
                        help='Start strip [sec] to load trace data')
    parser.add_argument('--end_strip', type=float, default=0.0,
                        help='End strip [sec] to load trace data')
    parser.add_argument('--sim_time', type=strtobool, default=False)
    parser.add_argument('--is_path_analysis_only', type=strtobool, default=False)
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

    # options for validation
    parser.add_argument('--report_directory', type=str, default='')
    parser.add_argument('--callback_list_filename', type=str, default='callback_list.csv')
    parser.add_argument('--topic_list_filename', type=str, default='topic_list.csv')
    parser.add_argument('--expectation_topic_csv_filename', type=str, default='expectation_topic.csv')
    parser.add_argument('--expectation_callback_csv_filename', type=str, default='expectation_callback.csv')

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
    logger.debug(f'is_path_analysis_only: {args.is_path_analysis_only}')
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
    logger.debug(f'report_directory: {args.report_directory}')
    logger.debug(f'callback_list_filename: {args.callback_list_filename}')
    logger.debug(f'topic_list_filename: {args.topic_list_filename}')
    logger.debug(f'expectation_topic_csv_filename: {args.expectation_topic_csv_filename}')
    logger.debug(f'expectation_callback_csv_filename: {args.expectation_callback_csv_filename}')

    # Read trace data
    lttng = read_trace_data(args.trace_data, args.start_strip, args.end_strip, False)
    arch = Architecture('lttng', args.trace_data)

    # Create architecture for path analysis
    arch_path = add_path_to_architecture.add_path_to_architecture(args, arch)
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

    # Analyze and validate
    analyze_path.analyze(args, lttng, arch_path, app, args.dest_dir + '/analyze_path')

    if not args.is_path_analysis_only:
        xaxis_type = 'sim_time' if args.sim_time else 'system_time'
        generate_expectation_list.create_topic_from_callback(args.callback_list_filename, args.report_directory, args.topic_list_filename)
        generate_expectation_list.generate_list(args.verbose, arch, args.report_directory, args.component_list_json, args.topic_list_filename, args.expectation_topic_csv_filename)
        validate_topic.validate(args.verbose, arch, app, args.report_directory, args.force, args.component_list_json, os.path.join(args.report_directory, args.expectation_topic_csv_filename), xaxis_type)
        validate_callback.validate(args.verbose, arch, app, args.report_directory, args.force, args.component_list_json, args.expectation_callback_csv_filename, xaxis_type)


if __name__ == '__main__':
    main()
