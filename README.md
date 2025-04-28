# SAPInvokeFM - An SAP client to invoke Remote Enabled RFC Function Modules

Invoke SAP RFC remote enabled function modules using the PyRFC client bindings of SAP NWRFC SDK. 
Only RFC authentication is supported. 

Below an example 
## Basic Usage

```bash
# Using connection configuration file
python3 execInvokeFM.py -conn conn.cfg -f FUNCTION_NAME -i import.json -e export.json

# Using direct connection parameters
python3 execInvokeFM.py -u USERNAME -p PASSWORD -t TARGET -c CLIENT -f FUNCTION_NAME -i import.json -e export.json
```

## Connection Configuration

### Connection File Format (conn.cfg)
```ini
[section_name]
dest = DESTINATION_NAME
user = username
passwd = password
ashost = hostname
sysnr = 00
client = 800
lang = EN
```

### Connection Options
- `-conn, --connection`: Path to connection configuration file
- `--dest`: Destination name in the connection config file
- `-u, --user`: SAP username (required if not using -conn)
- `-p, --password`: SAP password (required if not using -conn)
- `-t, --target`: SAP hostname or IP (required if not using -conn)
- `-c, --client`: SAP client number (required if not using -conn)
- `-s, --sysnr`: SAP system number (default: '00')
- `-P, --port`: SAP gateway port (default: '3300')
- `-r, --saprouter`: SAP Router string

## Function Module Execution

### Basic Parameters
- `-f, --function`: Function module name to call (required)
- `-i, --import`: Path to JSON file containing IMPORTING/CHANGING/TABLES parameters
- `-e, --export`: Path to JSON file specifying which parameters to capture from the result
- `-d, --desc`: Show function module metadata/description instead of executing it

## Common Use Cases

### 1. List Logical System Commands available to the SXPG framework (SM49/SM69)
```bash
python3 execInvokeFM.py -conn conn.cfg -f 'SXPG_COMMAND_LIST_GET' --dest NPL -i import.json -e export.json
```

Import parameters (import.json):
```json
{
    "COMMANDNAME": "*"
}
```

### 2. Execute Logical System Commands using the SXPG framework (as defined in SM49/SM69)
```bash
python3 execInvokeFM.py -conn conn.cfg -f 'SXPG_COMMAND_EXECUTE' --dest NPL -i import.json -e export.json
```

Import parameters (import.json):
```json
{
    "COMMANDNAME": "ENV",
    "OPERATINGSYSTEM": "UNIX",
    "TARGETSYSTEM": "vhcalnplci",
    "STDOUT": "X",
    "STDERR": "X",
    "TERMINATIONWAIT": "X"
}
```

### 3. Read Database Tables (e.g., Extract user hashes)
```bash
python3 execInvokeFM.py -conn conn.cfg -f 'RFC_READ_TABLE' --dest A4H -i import.json -e export.json
```

Import parameters (import.json):
```json
{
    "QUERY_TABLE": "USR02",
    "DELIMITER": "|",
    "FIELDS": [
        {"FIELDNAME": "BNAME"},
        {"FIELDNAME": "BCODE"},
        {"FIELDNAME": "PASSCODE"},
        {"FIELDNAME": "PWDSALTEDHASH"}
    ],
    "OPTIONS": []
}
```

## Export File Format

The export file specifies which parameters to capture from the function module's result:

```json
{
    "capture": ["PARAM1", "PARAM2", "TABLE1[FIELD1]"]
}
```

- Use `[]` to specify table field access
- Use empty array `[]` to capture all results
- Omit `-e` parameter to show all results by default

## Function Module Description

To view a function module's interface and parameters without executing it:

```bash
python3 execInvokeFM.py -conn conn.cfg -f FUNCTION_NAME -d
```

# SAPInvokeFM TODO LIST 
## Authentication & Protocol Enhancements
- [ ] Add support for SNC (Secure Network Communications) authentication
- [ ] Add support for WebSocket RFC
