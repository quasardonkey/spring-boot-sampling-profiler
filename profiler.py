#!/usr/bin/env python3
"""
MIT License

Copyright (c) 2025 Daniel Hanrahan <quasardonkey@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

SPDX-License-Identifier: MIT
"""

from collections import Counter, defaultdict
import argparse
import csv
import json
import logging
import requests
import random
import time


def get_thread_dump(url):
    """
    Fetch the thread dump from the given URL.

    :param url: The URL to fetch the thread dump from
    :return: JSON response containing the thread dump or None if an error occurs
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching thread dump: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON response: {e}")
        return None


def filter_stack_trace(stack_trace, method_filter):
    """
    Filter the stack trace based on the specified method filter.

    :param stack_trace: The stack trace to filter
    :param method_filter: The method filter in the format 'ClassName#MethodName'
    :return: Filtered stack trace
    """
    if method_filter is None or method_filter == '':
        return stack_trace
    else:
        class_name_filter, method_name_filter = method_filter.split('#')
        start_depth = None
        for depth, stack_frame in enumerate(stack_trace):
            if stack_frame['className'] == class_name_filter and stack_frame['methodName'] == method_name_filter:
                start_depth = depth
                break
        if start_depth is None:
            return []
        else:
            return stack_trace[start_depth:]


def extract_methods_with_depth(thread_dump, package_filter, method_filter):
    """
    Extract methods with their depth and state from the thread dump.

    :param thread_dump: The thread dump to extract methods from
    :param package_filter: The package filter to apply
    :param method_filter: The method filter to apply
    :return: List of tuples containing method, depth, and state
    """
    methods_with_depth = []
    for thread in thread_dump['threads']:
        thread_state = thread['threadState']
        if thread_state == 'RUNNABLE':
            stack_trace_reversed = list(reversed(thread['stackTrace']))
            filtered_stack_trace = filter_stack_trace(stack_trace_reversed, method_filter)
            for depth, stack_frame in enumerate(filtered_stack_trace):
                if stack_frame['className'].startswith(package_filter):
                    method = f"{stack_frame['className']}.{stack_frame['methodName']}"
                    methods_with_depth.append((method, depth, thread_state))
    return methods_with_depth


def report_estimated_time_remaining(samples, min_interval, max_interval):
    """
    Report the estimated time remaining for sampling.

    :param samples: The number of samples to take
    :param min_interval: The minimum interval between samples
    :param max_interval: The maximum interval between samples
    """
    avg_sampling_interval = (max_interval - min_interval) / 2 + min_interval
    estimated_time_in_seconds = samples * avg_sampling_interval
    logging.info(f"Estimated sampling time is {estimated_time_in_seconds} seconds")


def sample_thread_dumps(url, package_filter, method_filter, samples, min_interval, max_interval):
    """
    Sample thread dumps from the given URL and analyze the methods.

    :param url: The URL to fetch thread dumps from
    :param package_filter: The package filter to apply
    :param method_filter: The method filter to apply
    :param samples: The number of samples to take
    :param min_interval: The minimum interval between samples
    :param max_interval: The maximum interval between samples
    :return: Combined data containing method, count, average depth
    """
    logging.info(f"Started sampling {url}")
    report_estimated_time_remaining(samples, min_interval, max_interval)
    method_counts = Counter()
    depth_sums = defaultdict(int)
    depth_counts = Counter()
    for sample in range(samples):
        interval = random.uniform(min_interval, max_interval)
        logging.debug(f"Waiting {interval:1.2f} seconds before taking sample {sample + 1} / {samples}")
        time.sleep(interval)
        thread_dump = get_thread_dump(url)
        if thread_dump:
            methods_with_depth = extract_methods_with_depth(thread_dump, package_filter, method_filter)
            for method, depth, state in methods_with_depth:
                method_counts.update([method])
                depth_sums[method] += depth
                depth_counts.update([method])
        else:
            logging.warning(f"Skipping sample {sample + 1} due to failed thread dump retrieval")

    combined_data = []
    for method, count in method_counts.items():
        avg_depth = depth_sums[method] / depth_counts[method]
        combined_data.append((method, count, avg_depth))

    combined_data.sort(key=lambda x: x[2], reverse=False)
    logging.info(f"Finished sampling {url}")
    return combined_data


def write_combined_report(combined_data, filename='combined_report.csv'):
    """
    Write the combined report to a CSV file.

    :param combined_data: The combined data to write
    :param filename: The name of the output CSV file
    """
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Method', 'Count', 'Average Depth'])
        for method, count, avg_depth in combined_data:
            writer.writerow([method, count, round(avg_depth)])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description='Profile a Java application using Spring Actuator thread dump endpoint.')
    parser.add_argument('--config', type=str, help='Path to the config file', default='config.json')
    parser.add_argument('--output', type=str, help='Path to the output CSV file', default=None)
    args = parser.parse_args()

    with open(args.config, 'r') as config_file:
        config = json.load(config_file)

    url = config['url']
    package_filter = config['package_filter']
    method_filter = config['method_filter']
    samples = config['samples']
    min_interval = config['min_interval']
    max_interval = config['max_interval']
    output_file = args.output if args.output else config.get('output_file', 'method_counts.csv')

    combined_data = sample_thread_dumps(url, package_filter, method_filter, samples, min_interval, max_interval)
    write_combined_report(combined_data, output_file)
