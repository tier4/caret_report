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
Script to analyze path
"""
from __future__ import annotations
import sys
import os
import datetime
import argparse
import logging
from caret_analyze import Architecture, Application, Lttng
from caret_analyze.plot import Plot
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, read_trace_data_duration

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

# Suppress log for Bokeh "BokehUserWarning: out of range integer may result in loss of precision"
import warnings
warnings.simplefilter("ignore")

_logger: logging.Logger = None


def analyze_path(app: Application, target_path_name: str, skip_first_num: int):
    """Analyze a path"""
    _logger.info(f'Processing: {target_path_name}')
    target_path = app.get_path(target_path_name)
    target_path.include_first_callback = False
    target_path.include_last_callback = False

    plot_timeseries = Plot.create_response_time_timeseries_plot(target_path, case='best')

    # Find the start time of the path (but choose the second one because the first one could be very long)
    df = plot_timeseries.to_dataframe()
    skip_first_num = min(skip_first_num, len(df) - 1)
    if skip_first_num >= 0:
        start_time = df.iloc[skip_first_num, 0]
        start_date_time = datetime.datetime.fromtimestamp(start_time * 1.0e-9)
    else:
        start_date_time = None
    _logger.info(f'  start_date_time = {start_date_time}')
    return start_date_time


def analyze(args, lttng: Lttng, arch: Architecture, app: Application):
    """Analyze paths"""
    global _logger
    if _logger is None:
        _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)
    _logger.info('<<< Analyze Paths: Start >>>')

    # Verify each path
    for target_path in arch.paths:
        target_path_name = target_path.path_name
        path = arch.get_path(target_path_name)
        ret_verify = path.verify()
        _logger.info(f'path.verify {target_path_name}: {ret_verify}')
        if not ret_verify:
            sys.exit(-1)

    # Analyze each path
    start_date_time_list = []
    for target_path in arch.paths:
        target_path_name = target_path.path_name
        start_date_time = analyze_path(app, target_path_name, args.skip_first_num)
        if start_date_time:
            start_date_time_list.append(start_date_time)

    bt, et = lttng.get_trace_range()
    lttng_duration = (et - bt).total_seconds()
    _logger.info(f'lttng_bt = {bt}, lttng_et = {et}, lttng_duration = {lttng_duration}')

    start_strip_list = [(start_date_time - bt).total_seconds() for start_date_time in start_date_time_list]
    if len(start_strip_list) > 0:
        start_strip = max(start_strip_list)
    else:
        start_strip = 0.0
    end_strip = (et - (bt + datetime.timedelta(seconds=start_strip + args.duration))).total_seconds()

    _logger.info(f'start_strip = {start_strip}, end_strip = {end_strip}')
    _logger.info('<<< Analyze Paths: Finish >>>')
    return max(0, start_strip), max(0, end_strip)


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to analyze path')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--architecture_file_path', type=str, default='architecture_path.yaml')
    parser.add_argument('--duration', type=float, default=60.0,
                        help='Duration [sec] to load trace data')
    parser.add_argument('--load_duration', type=float, default=120.0,
                        help='Duration [sec] to load trace data to find valid duration')
    parser.add_argument('--skip_first_num', type=int, default=1,
                        help='The number to skip the first n-th trace data')
    parser.add_argument('-v', '--verbose', action='store_true', default=False)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    global _logger
    args = parse_arg()
    _logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    _logger.debug(f'trace_data: {args.trace_data[0]}')
    _logger.debug(f'architecture_file_path: {args.architecture_file_path}')
    _logger.debug(f'duration: {args.duration}')

    lttng = read_trace_data_duration(args.trace_data[0], 0, args.load_duration, False)

    arch = Architecture('yaml', args.architecture_file_path)
    app = Application(arch, lttng)

    start_strip, end_strip = analyze(args, lttng, arch, app)
    with open("start_strip.txt", "w") as f:
        f.write(str(start_strip))

    with open("end_strip.txt", "w") as f:
        f.write(str(end_strip))


if __name__ == '__main__':
    main()
