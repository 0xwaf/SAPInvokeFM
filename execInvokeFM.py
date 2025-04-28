#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SAP Remote Function Module Invocation Script
This script connects to a SAP system via RFC and calls any specified function module
on the target system. Supports function modules with parameters via JSON files.
"""

import sys
import argparse
import os
import json
from configparser import ConfigParser
from typing import Dict, List, Optional, Union, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pyrfc import Connection, RFCError, ABAPApplicationError, LogonError, CommunicationError

BANNER = """
    ██╗███╗   ██╗██╗   ██╗ ██████╗ ██╗  ██╗███████╗██████╗ ███████╗███╗   ███╗
    ██║████╗  ██║██║   ██║██╔═══██╗██║ ██╔╝██╔════╝██╔══██╗██╔════╝████╗ ████║
    ██║██╔██╗ ██║██║   ██║██║   ██║█████╔╝ █████╗  ██████╔╝█████╗  ██╔████╔██║
    ██║██║╚██╗██║╚██╗ ██╔╝██║   ██║██╔═██╗ ██╔══╝  ██╔══██╗██╔══╝  ██║╚██╔╝██║
    ██║██║ ╚████║ ╚████╔╝ ╚██████╔╝██║  ██╗███████╗██║  ██║██║     ██║ ╚═╝ ██║
    ╚═╝╚═╝  ╚═══╝  ╚═══╝   ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝     ╚═╝
    ====================================================
    SAP Remote Function Module Executor
    Author: @WaelFeguiri
    Github: https://github.com/0xwaf
    ====================================================
"""

def print_banner():
    """Print the ASCII art banner."""
    print(Colors.format(BANNER, 'cyan'))

@dataclass
class ConnectionParams:
    """Connection parameters data class"""
    user: str
    passwd: str
    ashost: str
    client: str
    sysnr: str = '00'
    saprouter: Optional[str] = None
    dest: Optional[str] = None
    lang: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary format for Connection class."""
        return {k: v for k, v in self.__dict__.items() 
                if v is not None and k not in ['dest', 'lang']}

class Colors:
    """ANSI color codes"""
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'orange': '\033[38;5;208m',
        'reset': '\033[0m'
    }

    @classmethod
    def format(cls, text: str, color: str) -> str:
        return f"{cls.COLORS.get(color, '')}{text}{cls.COLORS['reset']}"

class Logger:
    _loggers = {
        'info': lambda msg: print(Colors.format(f"[*] {msg}", 'cyan')),
        'success': lambda msg: print(Colors.format(f"[+] {msg}", 'green')),
        'warning': lambda msg: print(Colors.format(f"[!] {msg}", 'yellow')),
        'error': lambda msg: print(Colors.format(f"[-] {msg}", 'red'))
    }

    @classmethod
    def log(cls, level: str, message: str) -> None:
        cls._loggers.get(level, cls._loggers['info'])(message)

    @classmethod
    def info(cls, message: str) -> None:
        cls.log('info', message)

    @classmethod
    def success(cls, message: str) -> None:
        cls.log('success', message)

    @classmethod
    def warning(cls, message: str) -> None:
        cls.log('warning', message)

    @classmethod
    def error(cls, message: str) -> None:
        cls.log('error', message)

class SAPConnection:
    """SAP connection handler"""
    def __init__(self, conn_params: ConnectionParams):
        self.conn_params = conn_params
        self.connection = None
        self._metadata_cache = {}

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def connect(self) -> None:
        """Establish connection"""
        params_dict = self.conn_params.to_dict()
        Logger.info(f"Connecting to SAP system {params_dict['ashost']} "
                   f"(sys: {params_dict['sysnr']}, client: {params_dict['client']})...")

        try:
            self.connection = Connection(**params_dict)
            system_info = self.connection.get_connection_attributes()
            Logger.success(f"Connected to SAP system: {system_info.get('sysId', 'Unknown')}")
        except (LogonError, CommunicationError, RFCError) as e:
            Logger.error(f"Connection error: {str(e)}")
            sys.exit(1)

    def close(self) -> None:
        if self.connection:
            self.connection.close()
            Logger.info("SAP connection closed")

    def get_function_metadata(self, function_name: str) -> bool:
        """Display function module metadata."""
        if not self.connection:
            raise RuntimeError("No active connection")

        Logger.info(f"Getting function description for: {function_name}")
        
        try:
            func_desc = self.connection.get_function_description(function_name)
            if not func_desc:
                Logger.error(f"Could not retrieve description for function {function_name}")
                return False
            
            Logger.success(f"Parameters of function: {function_name}")

            # Define parameter sorting function
            def parameter_key_function(parameter):
                direction_order = {"IMPORTING": 1, "EXPORTING": 2, "CHANGING": 3, "TABLES": 4}
                direction = parameter.get("direction", "").upper()
                return direction_order.get(direction, 5), parameter.get("name", "")

            # Define parameter display format
            parameter_keys = [
                "name",
                "parameter_type",
                "direction",
                "nuc_length",
                "uc_length",
                "decimals",
                "default_value",
                "optional",
                "type_description",
                "parameter_text",
            ]
            parameter_widths = [20, 17, 11, 10, 9, 9, 15, 10, 15, 20]
            
            # Print header
            print(" ".join(key.upper().ljust(width) for key, width in zip(parameter_keys, parameter_widths)))

            # Print each parameter
            for parameter in sorted(func_desc.parameters, key=parameter_key_function):
                # Print parameter row
                row = []
                for key, width in zip(parameter_keys, parameter_widths):
                    value = parameter[key]
                    if key == "type_description" and value is not None:
                        value = value.name
                    row.append(str(value).ljust(width))
                print(" ".join(row))
                
                # If parameter has a complex structure, display its details
                type_desc = parameter["type_description"]
                if type_desc is not None:
                    field_keys = [
                        "name",
                        "field_type",
                        "nuc_length",
                        "nuc_offset",
                        "uc_length",
                        "uc_offset",
                        "decimals",
                        "type_description",
                    ]
                    field_widths = [20, 17, 10, 10, 9, 9, 10, 15]

                    print(f"    -----------( Structure of {type_desc.name} "
                          f"(n/uc_length={type_desc.nuc_length}/{type_desc.uc_length})--")
                    
                    # Print field header
                    print("    " + " ".join(key.upper().ljust(width) for key, width in zip(field_keys, field_widths)))

                    # Print fields
                    for field in type_desc.fields:
                        print("    " + " ".join(str(field[key]).ljust(width) for key, width in zip(field_keys, field_widths)))

                    print(f"    -----------( Structure of {type_desc.name} )-----------")
                
                print("-" * sum(parameter_widths))
            
            return True
            
        except RFCError as e:
            Logger.error(f"RFC error retrieving function description: {str(e)}")
            return False
        except Exception as e:
            Logger.error(f"Error retrieving function description: {str(e)}")
            return False

    def execute_function(self, function_name: str, 
                        import_params: Optional[Dict] = None,
                        params_to_capture: Optional[Set[str]] = None) -> bool:
        """Function execution"""
        if not self.connection:
            raise RuntimeError("No active connection")

        Logger.info(f"Invoking function module '{function_name}'...")
        import_params = import_params or {}

        try:
            result = self.connection.call(function_name, **import_params)
            Logger.success(f"Function module '{function_name}' called successfully")
            
            if result:
                self._process_results(result, params_to_capture)
            return True
        except (ABAPApplicationError, RFCError) as e:
            Logger.error(f"Function execution error: {str(e)}")
            return False

    def _process_results(self, result: Dict, params_to_capture: Optional[Set[str]]) -> None:
        """Process results"""
        if not params_to_capture:
            self._display_all_results(result)
            return

        captured_results = defaultdict(list)
        for param in params_to_capture:
            if '[' in param and param.endswith(']'):
                table_name, field = param.split('[', 1)
                field = field.rstrip(']')
                if table_name in result and isinstance(result[table_name], list):
                    captured_results[param].extend(
                        row.get(field) or row.get("WA")
                        for row in result[table_name]
                        if isinstance(row, dict)
                    )
            elif param in result:
                captured_results[param] = result[param]

        self._display_captured_results(captured_results)

    def _display_all_results(self, result: Dict) -> None:
        Logger.info("Function returned the following data:")
        for key, value in result.items():
            formatted_value = (json.dumps(value, indent=2) 
                             if isinstance(value, (list, dict)) 
                             else value)
            print(f"  {key}: {formatted_value}")

    def _display_captured_results(self, results: Dict) -> None:
        Logger.info("Function returned the following requested data:")
        for key, value in results.items():
            formatted_value = (json.dumps(value, indent=2) 
                             if isinstance(value, (list, dict)) 
                             else value)
            print(f"  {key}: {formatted_value}")

class ConfigManager:
    def __init__(self):
        self._config_cache = {}
        self._json_cache = {}

    @lru_cache(maxsize=32)
    def load_config(self, config_file: str, dest: Optional[str] = None) -> Dict[str, str]:
        """Load and cache configuration after initial load."""
        if not os.path.isfile(config_file):
            Logger.error(f"Configuration file not found: {config_file}")
            sys.exit(1)

        try:
            config = ConfigParser()
            config.read(config_file)

            if dest:
                for section in config.sections():
                    if config.has_option(section, 'dest') and config.get(section, 'dest') == dest:
                        return dict(config.items(section))
                Logger.error(f"Destination '{dest}' not found in config file")
                sys.exit(1)

            if not config.sections():
                Logger.error(f"No connection configurations found in {config_file}")
                sys.exit(1)

            return dict(config.items(config.sections()[0]))
        except Exception as e:
            Logger.error(f"Error reading configuration: {str(e)}")
            sys.exit(1)

    @lru_cache(maxsize=32)
    def load_json(self, file_path: str) -> Dict:
        """Load and cache JSON after initial load."""
        if not os.path.isfile(file_path):
            Logger.error(f"File not found: {file_path}")
            sys.exit(1)

        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("Expected a dictionary")
            return data
        except Exception as e:
            Logger.error(f"Error reading {file_path}: {str(e)}")
            sys.exit(1)

def parse_args() -> argparse.Namespace:
    """Parse arguments"""
    parser = argparse.ArgumentParser(
        description='Invoke SAP Remote Function Modules via RFC',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Connection options
    parser.add_argument('-conn', '--connection', help='Path to connection configuration file (.cfg)')
    parser.add_argument('--dest', help='Destination name in the connection config file')
    
    # Direct connection parameters
    conn_group = parser.add_argument_group('Connection Parameters (required if --connection is not specified)')
    conn_group.add_argument('-u', '--user', help='SAP username')
    conn_group.add_argument('-p', '--password', help='SAP password')
    conn_group.add_argument('-t', '--target', help='SAP hostname or IP')
    conn_group.add_argument('-c', '--client', help='SAP client number')
    conn_group.add_argument('-s', '--sysnr', default='00', help='SAP system number')
    conn_group.add_argument('-P', '--port', default='3300', help='SAP gateway port')
    parser.add_argument('-r', '--saprouter', help='SAP Router string')

    # Function options
    parser.add_argument('-f', '--function', required=True, help='Function module name to call')
    parser.add_argument('-i', '--import', dest='import_path', help='Path to JSON file containing parameters')
    parser.add_argument('-e', '--export', dest='export_path', help='Path to JSON file specifying parameters to capture')
    parser.add_argument('-d', '--desc', action='store_true', help='Show function module metadata')

    args = parser.parse_args()

    if not args.connection and not all([args.user, args.password, args.target, args.client]):
        parser.error("When --connection is not specified, --user, --password, --target, and --client are required")

    return args

def main() -> None:
    """Main function with optimized flow."""
    try:
        print_banner()
        args = parse_args()
        config_manager = ConfigManager()
        
        # Load parameters with caching
        import_params = (config_manager.load_json(args.import_path) 
                        if args.import_path else None)
        export_spec = (config_manager.load_json(args.export_path) 
                      if args.export_path else None)
        params_to_capture = (set(export_spec.get("capture", [])) 
                           if export_spec else None)

        # Establish connection
        if args.connection:
            conn_params = ConnectionParams(**config_manager.load_config(args.connection, args.dest))
        else:
            conn_params = ConnectionParams(
                user=args.user,
                passwd=args.password,
                ashost=args.target,
                client=args.client,
                sysnr=args.sysnr,
                saprouter=args.saprouter
            )

        # Execute function with context manager
        with SAPConnection(conn_params) as sap:
            if args.desc:
                if not sap.get_function_metadata(args.function):
                    sys.exit(1)
            else:
                sap.execute_function(args.function, import_params, params_to_capture)

    except KeyboardInterrupt:
        print()
        Logger.warning("Operation interrupted by user")
        sys.exit(130)
    except Exception as e:
        Logger.error(f"Unhandled exception: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
