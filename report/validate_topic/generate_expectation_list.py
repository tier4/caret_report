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
Generate expectation list for topic
"""
import sys
import os
import argparse
from pathlib import Path
import logging
import csv
from caret_analyze import Architecture, Application, Lttng
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir
from common.utils import ComponentManager

# Suppress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def generate_list(logger, arch: Architecture, dest_dir: str, component_list_json: str, topic_list_filename: str, expectation_csv_filename: str):
    """Generate topic list"""
    global _logger
    _logger = logger
    _logger.info(f'<<< Generate topic list start >>>')

    ComponentManager().initialize(component_list_json, _logger)

    if not os.path.isfile(f'{dest_dir}/{topic_list_filename}'):
        _logger.error(f"Unable to read expectation csv: {dest_dir}/{topic_list_filename}")
        return

    unknown_topic_name_list = []

    with open(f'{dest_dir}/{topic_list_filename}', 'r', encoding='utf-8') as csvfile:
        all_comms = arch.communications
        expectation_list = []
        for row in csv.DictReader(csvfile, ['topic_name', 'value']):
            try:
                topic_name = row['topic_name']
                value = row['value']
            except:
                _logger.error(f"Error at reading: {row}")
                continue

            _logger.debug(f"=== {topic_name} ===")
            comms = [comm for comm in all_comms if comm.topic_name == topic_name]
            if len(comms) > 0:
                for comm in comms:
                    # plt = Plot.create_frequency_timeseries_plot(comm)
                    # df = plt.to_dataframe()
                    # if len(df) == 0:
                    #     raise Exception
                    expectation = {}
                    expectation['topic_name'] = topic_name
                    expectation['publish_node_name'] = comm.publish_node_name
                    expectation['publish_component_name'] = ComponentManager().get_component_name(comm.publish_node_name)
                    expectation['subscribe_node_name'] = comm.subscribe_node_name
                    expectation['subscribe_component_name'] = ComponentManager().get_component_name(comm.subscribe_node_name)
                    expectation['value'] = value
                    if ComponentManager().check_if_external_in_topic(topic_name, comm.subscribe_node_name):
                        expectation['publish_component_name'] = 'external'
                    if ComponentManager().check_if_external_out_topic(topic_name, comm.publish_node_name):
                        expectation['subscribe_component_name'] = 'external'
                    if expectation['publish_component_name'] == expectation['subscribe_component_name']:
                        continue
                    expectation_list.append(expectation)
            else:
                found_as_callback = False
                if ComponentManager().check_if_external_in_topic(topic_name):
                    for callback in arch.callbacks:
                        if callback.subscribe_topic_name and callback.subscribe_topic_name == topic_name:
                            _logger.info(f'get_communications() fails for {topic_name}, but found as subscription callback')
                            found_as_callback = True
                            expectation = {}
                            expectation['topic_name'] = topic_name
                            expectation['publish_node_name'] = 'external'
                            expectation['publish_component_name'] = 'external'
                            expectation['subscribe_node_name'] = callback.node_name
                            expectation['subscribe_component_name'] = ComponentManager().get_component_name(callback.node_name)
                            expectation['value'] = value
                            expectation_list.append(expectation)
                if not found_as_callback:
                    _logger.warning(f'get_communications() fails for {topic_name}')
                    unknown_topic_name_list.append(topic_name)

    for expectation in expectation_list:
        if ComponentManager().check_if_ignore(expectation['publish_node_name']) or \
            ComponentManager().check_if_ignore(expectation['subscribe_node_name']):
            expectation_list.remove(expectation)

    if len(expectation_list) > 0:
        with open(f'{dest_dir}/{expectation_csv_filename}', 'w', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=expectation_list[0].keys())
            writer.writerows(expectation_list)

    with open(f'{dest_dir}/topic_list_unknown.csv', 'w', encoding='utf-8') as csvfile:
        csvfile.writelines('\n'.join(unknown_topic_name_list))

    _logger.info(f'<<< Generate topic list finish >>>')


def create_topic_from_callback(callback_list_filename: str, dest_dir: str, topic_list_filename):
    topic_list = {}
    with open(callback_list_filename, 'r', encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile, ['node_name', 'callback_type', 'trigger', 'value']):
            try:
                callback_type = row['callback_type']
                trigger = row['trigger']
                value = row['value']
            except:
                _logger.error(f"Error at reading: {row}")
                continue
            if callback_type == 'subscription_callback':
                if trigger not in topic_list:
                    topic_list[trigger] = value
                else:
                    if isinstance(value, int) or isinstance(value, float):
                        topic_list[trigger] = value
                    else:
                        # don't update
                        pass

    topic_list = sorted(topic_list.items())
    with open(f'{dest_dir}/{topic_list_filename}', 'w', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        for topic_name, value in topic_list:
            writer.writerow([topic_name, value])


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to generate expectation list for topic validation')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--report_directory', type=str, default='')
    parser.add_argument('--component_list_json', type=str, default='component_list.json')
    parser.add_argument('--callback_list_filename', type=str, default='callback_list.csv')
    parser.add_argument('--topic_list_filename', type=str, default='topic_list.csv')
    parser.add_argument('--expectation_csv_filename', type=str, default='expectation_topic.csv')
    parser.add_argument('-v', '--verbose', action='store_true', default=True)
    args = parser.parse_args()
    return args


def main():
    """Main function"""
    args = parse_arg()
    logger = create_logger(__name__, logging.DEBUG if args.verbose else logging.INFO)

    logger.debug(f'trace_data: {args.trace_data[0]}')
    dest_dir = args.report_directory if args.report_directory != '' else f'val_{Path(args.trace_data[0]).stem}'
    logger.debug(f'dest_dir: {dest_dir}')
    logger.debug(f'component_list_json: {args.component_list_json}')
    logger.debug(f'callback_list_filename: {args.callback_list_filename}')
    logger.debug(f'topic_list_filename: {args.topic_list_filename}')
    logger.debug(f'expectation_csv_filename: {args.expectation_csv_filename}')

    make_destination_dir(dest_dir, False, _logger)
    create_topic_from_callback(args.callback_list_filename, dest_dir, args.topic_list_filename)

    arch = Architecture('lttng', str(args.trace_data[0]))
    # lttng = read_trace_data(args.trace_data[0], 0, 0)
    # app = Application(arch, lttng)

    generate_list(logger, arch, dest_dir, args.component_list_json, args.topic_list_filename, args.expectation_csv_filename)


if __name__ == '__main__':
    main()
