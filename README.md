# LISA Persist

An utility for LIS Automation script that parses the input and output files of a test run and persists the 
results in a SQL Server database

## Installation

```bash
$ git clone git@..
$ cd lisa-persist
$ pip install -r requirements.txt
```

## Usage

### Arguments:

```
-x | --xmlfile  The xml config file for the test run
-l | --logfile  Log file generated by the test run
-e | --env      Env file that holds values for the database connection - config/.env default
-a | --dbg      Log level for the script - INFO default
```

### Basic usage

```bash
$ python persist.py -x demo_files/test.xml -l demo_files/ica.log
```

### Specify env file

```bash
$ python persist.py -x demo_files/test.xml -l demo_files/ica.log -e path_to_env_file
```

## Documentation

The script is structured in 3 main modules that handle file parsing, interaction with the VM and
db insertion

### lisa_parser.py
#### XML Parser
The file handles the parsing of the .xml and .log files.
The xml parser uses the default xml python library - xml.etree.cElementTree

First it iterates the test cases written in the <suiteTests> section
```python
for test in self.root.iter('suiteTest'):
            tests_dict[test.text.lower()] = {
                'details': {},
                'results': {}
            }
```

For each test case two dicts are created:
- 'results' - stores ```python {'vmName' : 'Success | Failed'}```
- 'details' - the script iterates through the specific test section from <testCases>
and saves the test properties
```python
test_dict[test_property.tag] = list()
                for item in test_property.getchildren():
                    if test_property.tag == 'testparams':
                        parameter = item.text.split('=')
                        test_dict[test_property.tag].append(
                            (parameter[0], parameter[1])
                        )
                    else:
                        test_dict[test_property.tag].append(item.text)
```

VM details are saved separately inside the tests_dict by iterating through the <VMs> section of the xml file
```python
for machine in self.root.iter('vm'):
            vm_dict[machine.find('vmName').text] = {
                'hvServer': machine.find('hvServer').text,
                'sshKey': machine.find('sshKey').text,
                'os': machine.find('os').text
            }
```

#### Log file parser
The log file is parsed by a different method that saves the parsed field in the tests_dict created previously 
by parsing the initial xml config file
First the function goes through the log file looking for the final section called 'Test Results Summary'
Using regex the script looks for specific patterns in each line and saves the values
```python
for line in log_file:
            line = line.strip()
            if re.search("^VM:", line) and len(line.split()) == 2:
                vm_name = line.split()[1]
```


### vm_utils.py
The module runs 4 main PowerShell commands in order to interact and get more details regarding the VM and
the guest OS

It uses the subprocess module in order to run PS commands. The path to PS is saved in the .env file
```python
 def execute_command(command_arguments):
    ps_command = subprocess.Popen(
        command_arguments,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
```

### sql_utils.py
Database interaction is handled by the pyodbc module, connection variables being saved in the .env file.

The main method, insert_values, expects a dict in which the keys represent the table column names and the values
are the final values to be inserted
```python
def insert_values(cursor, table_name, values_dict):
    insert_command = Template('insert into $tableName($columns)'
                              ' values($values)')

    cursor.execute(insert_command.substitute(
        tableName=table_name,
        columns=', '.join(values_dict.keys()),
        values=', '.join("'" + item + "'" for item in values_dict.values())
    ))

```

## License
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