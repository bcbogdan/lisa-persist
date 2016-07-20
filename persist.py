"""
Copyright (c) Cloudbase Solutions 2016
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from __future__ import print_function
import logging
import time
import sys
from envparse import env
from lisa_parser import ParseXML
from lisa_parser import parse_log_file
import parse_arguments
import sql_utils
import vm_utils


def create_tests_list(tests_dict):
    """
    Method creates a list of dicts with keys that
    match the column names from the SQL Server table,
    each dict corresponding to a table line
    """
    logger = logging.getLogger(__name__)
    logger.debug('Creating the list with the lines to be inserted')
    tests_list = list()
    for test_name, test_props in tests_dict['tests'].iteritems():
        for name, details in tests_dict['vms'].iteritems():
            test_dict = dict()

            # Getting test id from tests dict
            # for param in test_props['details']['testparams']:
            #     if param[0] == 'TC_COVERED':
            #         test_dict['TestID'] = param[1]

            test_dict['TestLocation'] = details['TestLocation']
            test_dict['HostName'] = details['hvServer']
            test_dict['HostVersion'] = details['hostOSVersion']
            test_dict['GuestOSType'] = details['os']

            try:
                test_dict['TestResult'] = test_props['results'][name]
                test_dict['LogPath'] = tests_dict['logDir']
            except KeyError, ex:
                logger.warning('Test result not found for %s on vm %s',
                               test_name, name)
                continue

            test_dict['TestCaseName'] = test_name
            test_dict['TestArea'] = tests_dict['testSuite']
            test_dict['TestDate'] = format_date(tests_dict['timestamp'])
            test_dict['GuestOSDistro'] = details['OSName']
            test_dict['KernelVersion'] = details['OSBuildNumber']

            logger.debug(test_dict)
            tests_list.append(test_dict)

    return tests_list


def format_date(test_date):
    """
    Formats the date taken from the log file
     in order to align with the sql date format - YMD
    """
    split_date = test_date.split()
    split_date[0] = split_date[0].split('/')
    return ''.join(
        [split_date[0][2], split_date[0][0], split_date[0][1]]
    )


# TODO: Find a better name for method
def get_vm_info(vms_dict):
    """
    Method calls the get_vm_details function in order
    to find the Kernel version and Distro Name from the vm
    and saves them in the vm dictionary
    """
    logger = logging.getLogger(__name__)
    for vm_name, vm_details in vms_dict.iteritems():
        try:
            vm_values = vm_utils.get_vm_details(vm_name, vm_details['hvServer'])
        except RuntimeError, e:
            logger.error('Error on running command', exc_info=True)
            sys.exit(0)

        if not vm_values:
            logger.error('Unable to get vm details for %s', vm_name)
            sys.exit(2)

        vm_info = {}

        # Stop VM
        logger.info('Stopping %s', vm_name)
        vm_utils.manage_vm('stop', vm_name, vm_details['hvServer'])

        logger.debug('Parsing xml output of PS command')
        for value in vm_values.split('\r\n')[:-1]:
            result_tuple = ParseXML.parse_from_string(value)
            vm_info.update({
                result_tuple[0]: result_tuple[1]
            })

        vm_details['OSBuildNumber'] = vm_info['OSBuildNumber']
        vm_details['OSName'] = ' '.join([vm_info['OSName'], vm_info['OSMajorVersion']])
        logger.debug('Saving %s and %s from parsed command',
                     vm_info['OSBuildNumber'], vm_details['OSName'])

    return vms_dict


def create_tests_dict(xml_file, log_file):
    """
    The method creates the general tests dictionary
     in order for it to be processed for db insertion
    """
    # Parsing given xml and log files
    logger = logging.getLogger(__name__)
    logger.info('Parsing XML file - %s', xml_file)
    xml_parser = ParseXML(xml_file)
    tests_object = xml_parser()
    logger.info('Parsing log file - %s', log_file)
    parse_log_file(log_file, tests_object)

    # Getting more VM details from KVP exchange
    logger.info('Getting VM details using PS Script')
    is_booting = False
    for vm_name, vm_details in tests_object['vms'].iteritems():
        logging.debug('Checking %s status', vm_name)
        try:
            vm_state = vm_utils.manage_vm('check', vm_name, vm_details['hvServer'])
        except RuntimeError, ex:
            logger.error('Error on command for checking vm', exc_info=True)
            sys.exit(0)

        if vm_state.split('-----')[1].strip() == 'Off':
            logging.info('Starting %s', vm_name)
            try:
                vm_utils.manage_vm('start', vm_name, vm_details['hvServer'])
                is_booting = True
            except RuntimeError, ex:
                logger.error('Error on command for starting vm', exc_info=True)
                sys.exit(0)

    if is_booting:
        # TODO: Check for better option to see if VM has booted
        wait = 60
        logging.info('Waiting %d seconds for VMs to boot', wait)
        time.sleep(wait)

    tests_object['vms'] = get_vm_info(tests_object['vms'])

    return tests_object


def main(args):
    """
    The main entry point of the application
    """
    parse_arguments.setup_logging(default_level=logging.DEBUG)
    logger = logging.getLogger(__name__)

    logger.debug('Parsing env variables')
    env.read_envfile('config/.env')
    # Parse arguments and check if they exist

    logger.debug('Parsing command line arguments')
    input_files = parse_arguments.parse_arguments(args)

    print(input_files)
    sys.exit(0)

    if not all(input_files):
        print('Invalid command line arguments')
        sys.exit(2)

    logger.info('Creating tests dictionary')
    tests_object = create_tests_dict(
        input_files[0],
        input_files[1]
    )

    # Parse values to be inserted
    logger.info('Parsing tests dictionary for database insertion')
    insert_values = create_tests_list(tests_object)

    # Connect to db and insert values in the table
    logger.info('Initializing database connection')
    db_connection, db_cursor = sql_utils.init_connection()

    logger.info('Executing insertion commands')
    for table_line in insert_values:
        sql_utils.insert_values(db_cursor, 'TestResults', table_line)

    logger.info('Committing changes to the database')
    db_connection.commit()

if __name__ == '__main__':
    main(sys.argv[1:])
