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
from common import utils
from analyze_node import analyze_node
from analyze_path import add_path_to_architecture, analyze_path
from check_callback_sub import check_callback_sub
from check_callback_timer import check_callback_timer

_logger: logging.Logger = None


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to make analysis reports')

    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('target_path_json', nargs=1, type=str)
    parser.add_argument('-s', '--start_point', type=float, default=0.0,
                        help='Start point[sec] to load trace data')
    parser.add_argument('-d', '--duration', type=float, default=0.0,
                        help='Duration[sec] to load trace data')
    parser.add_argument('-f', '--force', action='store_true', default=False,
                        help='Overwrite report directory')
    parser.add_argument('--component_list_json', type=str, default='')
    parser.add_argument('--architecture_file_path', type=str, default='architecture_path.yaml')
    parser.add_argument('--use_latest_message', action='store_true', default=True)
    parser.add_argument('--max_node_depth', type=int, default=2)
    parser.add_argument('-m', '--message_flow', type=strtobool, default=False,
                        help='Output message flow graph')
    parser.add_argument('-r', '--gap_threshold_ratio', type=float, default=0.2,
                        help='Warning when callback_freq is less than "gap_threshold_ratio" * timer_period for "count_threshold" times')
    parser.add_argument('-n', '--count_threshold', type=int, default=10,
                        help='Warning when callback_freq is less than "gap_threshold_ratio" * timer_period for "count_threshold" times')
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

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'start_point: {args.start_point}, duration: {args.duration}')
    _logger.debug(f'target_path_json: {args.target_path_json[0]}')
    _logger.debug(f'component_list_json: {args.component_list_json}')
    _logger.debug(f'architecture_file_path: {args.architecture_file_path}')
    _logger.debug(f'use_latest_message: {args.use_latest_message}')
    _logger.debug(f'max_node_depth: {args.max_node_depth}')
    _logger.debug(f'message_flow: {args.message_flow}')
    _logger.debug(f'gap_threshold_ratio: {args.gap_threshold_ratio}')
    _logger.debug(f'count_threshold: {args.count_threshold}')
    dest_dir = f'report_{Path(args.trace_data[0]).stem}'
    _logger.debug(f'dest_dir: {dest_dir}')

    # Check if files exist
    try:
        with open(args.target_path_json[0], encoding='UTF-8') as f_temp:
            pass
    except:
        _logger.error(f'Unable to read {args.target_path_json[0]}')
        sys.exit(-1)

    # Read LTTng log and create CARET object
    lttng = utils.read_trace_data(args.trace_data[0], args.start_point, args.duration, False)
    arch = Architecture('lttng', str(args.trace_data[0]))
    app = Application(arch, lttng)

    # Analyze
    analyze_node.analyze(args, lttng, arch, app, dest_dir + '/node')
    check_callback_sub.analyze(args, lttng, arch, app, dest_dir + '/check_callback_sub')
    check_callback_timer.analyze(args, lttng, arch, app, dest_dir + '/check_callback_timer')
    add_path_to_architecture.add_path_to_architecture(args, arch)
    arch = Architecture('yaml', args.architecture_file_path)
    app = Application(arch, lttng)
    analyze_path.analyze(args, lttng, arch, app, dest_dir + '/path')


if __name__ == '__main__':
    main()
