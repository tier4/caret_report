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
import logging
import csv
from caret_analyze import Architecture, Application, Lttng
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')
from common.utils import create_logger, make_destination_dir, read_trace_data, export_graph, trail_df
from common.utils import Metrics, ResultStatus, ComponentManager

# Supress log for CARET
from logging import getLogger, FATAL
logger = getLogger()
logger.setLevel(FATAL)

_logger: logging.Logger = None


def generate_list(logger, arch: Architecture, component_list_json: str, topic_list_filename: str, expectation_csv_filename: str):
    """Generate topic list"""
    global _logger
    _logger = logger
    _logger.info(f'<<< Generate topic list start >>>')

    ComponentManager().initialize(component_list_json, _logger)

    if not os.path.isfile(topic_list_filename):
        _logger.error(f"Unable to read expectation csv: {topic_list_filename}")

    with open(topic_list_filename, 'r', encoding='utf-8') as csvfile:
        all_comms = arch.communications
        expectation_list = []
        for row in csv.DictReader(csvfile, ['topic_name', 'value']):
            try:
                topic_name = row['topic_name']
                value = float(row['value'])
            except:
                _logger.error(f"Error at reading: {row}")
                continue

            _logger.debug(f"=== {topic_name} ===")
            try:
                comms = [comm for comm in all_comms if comm.topic_name == topic_name]
                if len(comms) == 0:
                    raise Exception
                for comm in comms:
                    # plt = Plot.create_frequency_timeseries_plot(comm)
                    # df = plt.to_dataframe()
                    # if len(df) == 0:
                    #     raise Exception
                    expectation = {}
                    expectation['topic_name'] = topic_name
                    expectation['publish_node_name'] = comm.publish_node_name
                    expectation['pubilsh_component_name'] = ComponentManager().get_component_name(comm.publish_node_name)
                    expectation['subscribe_node_name'] = comm.subscribe_node_name
                    expectation['subscribe_component_name'] = ComponentManager().get_component_name(comm.subscribe_node_name)
                    expectation['value'] = value
                    if ComponentManager().check_if_external_in_topic(topic_name, comm.subscribe_node_name):
                        expectation['pubilsh_component_name'] = 'external'
                    if ComponentManager().check_if_external_out_topic(topic_name, comm.publish_node_name):
                        expectation['subscribe_component_name'] = 'external'
                    if expectation['pubilsh_component_name'] == expectation['subscribe_component_name']:
                        continue
                    expectation_list.append(expectation)
            except:
                found_as_callback = False
                if ComponentManager().check_if_external_in_topic(topic_name):
                    for callback in arch.callbacks:
                        if callback.subscribe_topic_name and callback.subscribe_topic_name == topic_name:
                            _logger.info(f'get_communications() fails for {topic_name}, but found as subscription callback')
                            found_as_callback = True
                            expectation = {}
                            expectation['topic_name'] = topic_name
                            expectation['publish_node_name'] = 'external'
                            expectation['pubilsh_component_name'] = 'external'
                            expectation['subscribe_node_name'] = callback.node_name
                            expectation['subscribe_component_name'] = ComponentManager().get_component_name(callback.node_name)
                            expectation['value'] = value
                            expectation_list.append(expectation)
                if not found_as_callback:
                    _logger.warning(f'get_communications() fails for {topic_name}')

    for expectation in expectation_list:
        if ComponentManager().check_if_ignore(expectation['publish_node_name']) or \
            ComponentManager().check_if_ignore(expectation['subscribe_node_name']):
            expectation_list.remove(expectation)

    with open(expectation_csv_filename, 'w', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=expectation_list[0].keys())
        writer.writerows(expectation_list)

    _logger.info(f'<<< Generate topic list finish >>>')


def generate_deleted_topic_list(logger, arch: Architecture, component_list_json: str, topic_list_filename: str):
    """Generate topic list"""
    global _logger
    _logger = logger
    _logger.info(f'<<< Generate deleted topic list start >>>')

    ComponentManager().initialize(component_list_json, _logger)

    if not os.path.isfile(topic_list_filename):
        _logger.error(f"Unable to read expectation csv: {topic_list_filename}")

    topic_list = []
    with open(topic_list_filename, 'r', encoding='utf-8') as csvfile:
        for row in csv.DictReader(csvfile, ['topic_name', 'value']):
            try:
                topic_name = row['topic_name']
            except:
                _logger.error(f"Error at reading: {row}")
                continue
            if topic_name not in topic_list:
                topic_list.append(topic_name)

    comm_topic_list = []
    for comm in arch.communications:
        topic_name = comm.topic_name
        publish_node_name = comm.publish_node_name
        pubilsh_component_name = ComponentManager().get_component_name(publish_node_name)
        subscribe_node_name = comm.subscribe_node_name
        subscribe_component_name = ComponentManager().get_component_name(subscribe_node_name)
        if ComponentManager().check_if_external_in_topic(topic_name, subscribe_node_name):
            pubilsh_component_name = 'external'
        if ComponentManager().check_if_external_out_topic(topic_name, publish_node_name):
            subscribe_component_name = 'external'

        if comm.topic_name == '/pacmod/to_can_bus':
            print(publish_node_name)
            print(pubilsh_component_name)
            print(subscribe_node_name)
            print(subscribe_component_name)


        if (pubilsh_component_name != subscribe_component_name) \
            and not(ComponentManager().check_if_ignore(publish_node_name) or ComponentManager().check_if_ignore(subscribe_node_name)):
            if topic_name not in comm_topic_list:
                comm_topic_list.append(topic_name)

    # check if expected topic is used in current arch
    topic_list_deleted = topic_list.copy()
    for topic_name in comm_topic_list:
        if topic_name in topic_list_deleted:
            topic_list_deleted.remove(topic_name)
    for topic_name in topic_list_deleted.copy():
        if ComponentManager().check_if_external_in_topic(topic_name):
            for callback in arch.callbacks:
                if callback.subscribe_topic_name and callback.subscribe_topic_name == topic_name:
                    topic_list_deleted.remove(topic_name)

    # check if topic in current arch is in expected topic list
    topic_list_new = comm_topic_list.copy()
    for topic_name in topic_list:
        if topic_name in topic_list_new:
            topic_list_new.remove(topic_name)

    with open('topic_list_deleted.csv', 'w', encoding='utf-8') as csvfile:
        csvfile.write('\n'.join(topic_list_deleted))

    with open('topic_list_new.csv', 'w', encoding='utf-8') as csvfile:
        csvfile.write('\n'.join(topic_list_new))

    _logger.info(f'<<< Generate deleted topic list finish >>>')


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(
                description='Script to generate expectation list for topic validation')
    parser.add_argument('trace_data', nargs=1, type=str)
    parser.add_argument('--component_list_json', type=str, default='component_list.json')
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
    logger.debug(f'component_list_json: {args.component_list_json}')
    logger.debug(f'topic_list_filename: {args.topic_list_filename}')
    logger.debug(f'expectation_csv_filename: {args.expectation_csv_filename}')

    arch = Architecture('lttng', str(args.trace_data[0]))
    # lttng = read_trace_data(args.trace_data[0], 0, 0)
    # app = Application(arch, lttng)

    generate_list(logger, arch, args.component_list_json, args.topic_list_filename, args.expectation_csv_filename)
    generate_deleted_topic_list(logger, arch, args.component_list_json, args.topic_list_filename)


if __name__ == '__main__':
    main()
