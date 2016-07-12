import time
import re
from envparse import env
import subprocess


def check_vm_status(vm_name, hv_server):
    ps_command = subprocess.Popen([
        env.str('PSPath'), 'get-vm', '-Name', vm_name, '-ComputerName', hv_server, '|', 'Select', 'State'
    ], stdout=subprocess.PIPE)

    if ps_command.stdout.read().strip().split('\n')[2].strip() == 'Off':
        return False
    else:
        return True


def start_vm(vm_name, hv_server, wait=10):
    ps_command = subprocess.Popen([
        env.str('PSPath'), 'start-vm', '-Name', vm_name, '-ComputerName ', hv_server
    ], stdout=subprocess.PIPE)

    time.sleep(wait)
    print("Waited %d seconds for vm to boot" % wait)


def run_kvp_command(script_path, vm_name, hv_server):
    kvp_command = subprocess.Popen([
        env.str('PSPath'), script_path, '-vmName ', vm_name, '-hvServer', hv_server,
        '-TestParams', '"TC_COVERED=KVP-01"'
    ], stdout=subprocess.PIPE)

    return kvp_command.stdout.read()


def get_kvp_value(kvp_output, value):
    kvp_output = kvp_output.split('\n')
    pattern = ''.join(['^', value])
    for line in kvp_output:
        if re.search(pattern, line.strip()):
            return line.split(':')[1]

