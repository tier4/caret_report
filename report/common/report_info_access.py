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
Save/Load CARET Configurations
"""
import argparse
import yaml
import os


def parse_arg():
    """Parse arguments"""
    parser = argparse.ArgumentParser(description='Script to save/load CARET configurations')
    parser.add_argument('yaml_file', nargs=1, type=str)
    parser.add_argument('trace_data_name', nargs=1, type=str)
    parser.add_argument('mode', nargs=1, type=str)
    parser.add_argument('key', nargs=1, type=str)
    parser.add_argument('val', nargs=1, type=str, help='value to save or default value to return')
    args = parser.parse_args()
    return args


def main():
    """main function"""
    args = parse_arg()
    yaml_file = args.yaml_file[0]
    trace_data_name = args.trace_data_name[0]
    mode = args.mode[0]
    key = args.key[0]
    val = args.val[0]

    info = {}
    if os.path.exists(yaml_file):
      with open(yaml_file, 'r', encoding='utf-8') as f_yaml:
        info = yaml.safe_load(f_yaml)
        if info is None:
            info = {}

    if trace_data_name not in info:
        print(f'No {trace_data_name} in {yaml_file}')
        info[trace_data_name] = {}
        loaded_val = val
    if key not in info[trace_data_name]:
        print(f'No {key} in {trace_data_name} in {yaml_file}')
        loaded_val = val
    else:
      loaded_val = info[trace_data_name][key]

    if mode == 'load':
      return loaded_val
    elif mode == 'load_save':
      val = loaded_val

    info[trace_data_name][key] = val
    with open(yaml_file, 'w', encoding='utf-8') as f_yaml:
      yaml.safe_dump(info, f_yaml, encoding='utf-8', allow_unicode=True, sort_keys=False)
    return val

if __name__ == '__main__':
    main()
