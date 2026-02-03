"""
Models for pETI Sync Server

Contains the configuration and sync folder classes for the sync server.
"""
import json
import logging
import re
import sys
from enum import Enum
from typing import Dict
from urllib.parse import quote

import requests
import yaml

# API URL templates with named placeholders
API_URL_BASE = "http://{host}/api?method={method}"
API_FOLDER_URL = API_URL_BASE + "&dir={dir}&secret={secret}&{options}"
API_SIMPLE_URL = API_URL_BASE + "&dir={dir}&{options}"

MAX_WAIT_SECONDS = 120
RETRY_INTERVAL_SECONDS = 10

# Regex pattern for validating host:port format
# Matches valid hostnames/IPs with port numbers
# Hostname: alphanumeric with hyphens, dots to separate labels
# IPv4: basic pattern (detailed validation done separately if needed)
HOST_PORT_PATTERN = re.compile(
    r'^([a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]*[a-zA-Z0-9])?)*|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):\d+$'
)


def validate_hosts(hosts: list) -> list:
    """
    Validate a list of hosts in 'host:port' format.
    
    Args:
        hosts: List of host strings to validate
        
    Returns:
        List of validated hosts
        
    Raises:
        ValueError: If any host is invalid
    """
    if not isinstance(hosts, list):
        raise ValueError(f"hosts must be a list, got {type(hosts)}")
    
    validated_hosts = []
    for host in hosts:
        if not isinstance(host, str):
            raise ValueError(f"Each host must be a string, got {type(host)}")
        
        # Validate format
        if not HOST_PORT_PATTERN.match(host):
            raise ValueError(
                f"Invalid host format '{host}'. Expected format: 'hostname:port' or 'IP:port'"
            )
        
        # Additional check: port must be in valid range
        # split() always returns a list, so IndexError is not possible here
        port_str = host.split(':')[-1]
        
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port in host '{host}': port must be a valid integer")
        
        if port < 1 or port > 65535:
            raise ValueError(f"Port {port} in '{host}' is out of valid range (1-65535)")
        
        validated_hosts.append(host)
    
    return validated_hosts


class ApiMethod(Enum):
    """API method endpoints for Resilio Sync"""
    ADD_FOLDER = 'add_folder'
    REMOVE_FOLDER = 'remove_folder'
    SET_FOLDER_PREFS = 'set_folder_prefs'
    SET_FOLDER_HOSTS = 'set_folder_hosts'
    SHUTDOWN = 'shutdown'


class Configuration:
    """
    Object-oriented wrapper for the configuration data.
    Provides access to configuration values in a structured manner.
    """

    def __init__(self,
                 config_path: str = "/root/eti-config.yaml",
                 keep_discarded_games: bool = False):
        """Initialize configuration by loading from the specified path"""
        self._config = load_config(config_path)
        self._yaml = self._config.get('_yaml', {})
        self.keep_discarded_games = keep_discarded_games

    @property
    def user(self) -> str:
        """Get authentication username"""
        return self._config.get('resilio_auth', {}).get('user', '')

    @property
    def password(self) -> str:
        """Get authentication password"""
        return self._config.get('resilio_auth', {}).get('password', '')

    @property
    def host(self) -> str:
        """Get Resilio host and port"""
        return self._config.get('resilio_host', 'localhost:8080')

    @property
    def sync_dir(self) -> str:
        """Get synchronization directory path"""
        return self._config.get('resilio_sync_dir', '')

    @property
    def data_dir(self) -> str:
        """Get data directory path"""
        return self._config.get('data_dir', '')

    @property
    def sync_options(self) -> str:
        """Get synchronization options"""
        return self._config.get('resilio_sync_options', '')

    @property
    def game_deny_list(self) -> list:
        """Returns the game denylist from the configuration"""
        return self._yaml.get('games', {}).get('denylist', [])

    @property
    def game_predefined_hosts(self) -> list:
        """Get the predefined hosts list for game folders"""
        return self._yaml.get('games', {}).get('predefined_hosts', [])

    def get_folders(self) -> Dict[str, Dict[str, str]]:
        """Get all folder configurations"""
        return self._yaml.get('folders', {})


class SyncFolder:
    """
    Represents a folder to be synchronized with the sync server.
    """

    def __init__(self,
                 config: Configuration,
                 folder_name: str,
                 folder_id: str = None,
                 secret: str = None):
        """
        Initialize a sync folder with the necessary details

        Args:
            config: Configuration object
            folder_name: Display name of the folder
            folder_id: ID/path component of the folder
            secret: Secret key for the folder
        """
        self.config = config
        self.name = folder_name
        self.id = folder_id or folder_name
        self.secret = secret or self._get_secret_from_config(folder_name)

    def _get_secret_from_config(self, folder_name: str) -> str:
        """Get the secret key for a folder from configuration"""
        folders = self.config.get_folders()
        return folders.get(folder_name, {}).get('secret', '')

    def sync(self) -> bool:
        """Add or update this folder in the sync system"""
        return self._make_sync_request(ApiMethod.ADD_FOLDER)

    def update_prefs(self) -> bool:
        """Update preferences for this folder"""
        return self._make_sync_request(ApiMethod.SET_FOLDER_PREFS)

    def set_hosts(self, hosts: list) -> bool:
        """
        Set predefined hosts for this folder
        
        Args:
            hosts: List of host strings in 'hostname:port' or 'IP:port' format
            
        Returns:
            bool: True if successful or if list is empty
            
        Raises:
            ValueError: If hosts list contains invalid entries
        """
        if not hosts:
            return True  # If list is empty, don't set any hosts
        
        # Validate hosts before making request
        try:
            validated_hosts = validate_hosts(hosts)
        except ValueError as e:
            logging.error(f"Invalid hosts configuration: {e}")
            raise
        
        return self._make_sync_request(ApiMethod.SET_FOLDER_HOSTS, hosts=validated_hosts)

    def remove(self) -> bool:
        """Remove this folder from the sync system"""
        return self._make_sync_request(ApiMethod.REMOVE_FOLDER, force=True)

    def __repr__(self):
        """String representation of the sync folder"""
        return f"SyncFolder(name={self.name}, id={self.id})"

    def _make_sync_request(self,
                           method: ApiMethod,
                           force: bool = False,
                           hosts: list = None) -> bool:
        """
        Make a sync-related API request

        Args:
            method: API method to use
            force: Whether to add force=1 parameter
            hosts: List of predefined hosts (for SET_FOLDER_HOSTS method)

        Returns:
            bool: True if successful, False if failed
        """
        try:
            if self.secret:
                url = API_FOLDER_URL.format(
                    host=self.config.host,
                    method=method.value,
                    dir=f"{self.config.sync_dir}/{self.id}",
                    secret=self.secret,
                    options=self.config.sync_options)
            else:
                url = API_SIMPLE_URL.format(
                    host=self.config.host,
                    method=method.value,
                    dir=f"{self.config.sync_dir}/{self.id}",
                    options=self.config.sync_options)

            if force:
                url += "&force=1"
            
            # Add hosts parameter for SET_FOLDER_HOSTS method
            if method == ApiMethod.SET_FOLDER_HOSTS and hosts:
                # Hosts are already validated at this point
                hosts_param = ",".join(hosts)
                # URL encode the hosts parameter for GET request
                # - Commas remain literal (safe=',') as they separate multiple hosts
                # - Colons are encoded as %3A (required for URL query parameters)
                # - This is the correct format for Resilio Sync API GET requests
                url += f"&hosts={quote(hosts_param, safe=',')}"
            
            import time
            start_time = time.time()
            while True:
                try:
                    response = requests.get(url,
                                            auth=(self.config.user,
                                                  self.config.password))
                    response.raise_for_status()
                    break
                except requests.exceptions.ConnectionError as e:
                    if time.time() - start_time > MAX_WAIT_SECONDS:
                        raise RuntimeError(
                            f"Server not reachable after {MAX_WAIT_SECONDS} seconds."
                        ) from e
                    logging.info(
                        f"Server not reachable, retrying in {RETRY_INTERVAL_SECONDS} seconds..."
                    )
                    time.sleep(RETRY_INTERVAL_SECONDS)
                except Exception:
                    raise
            if method == ApiMethod.REMOVE_FOLDER:
                action = "removed"
            elif method == ApiMethod.ADD_FOLDER:
                action = "added or updated"
            elif method == ApiMethod.SET_FOLDER_PREFS:
                action = "preferences updated"
            elif method == ApiMethod.SET_FOLDER_HOSTS:
                action = "hosts set"
            else:
                action = "processed (unknown method)"

            json_response = response.json()
            sync_message = json_response.get('message', '')
            sync_error: int = json_response.get('error', 0)

            # Map some error codes to more readable messages
            if sync_error == 3:
                sync_message = "Folder is not known"

            log_message = f"[{self.name}|{self.id}] {action}"
            if sync_error != 0:
                log_message += f": '{sync_message}' ({sync_error})"
            logging.info(log_message)
            return True

        except requests.exceptions.RequestException as e:
            logging.error(f"Error processing folder '{self.name}': {e}")
            return False


def load_config(config_path: str = "/root/eti-config.yaml") -> dict:
    """
    Load configuration from the YAML config file

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        dict: Configuration dictionary preserving the original structure
    """
    try:
        with open(config_path, 'r') as file:
            config_yaml = yaml.safe_load(file)

        # Store the original YAML structure
        config = {'_yaml': config_yaml}

        # Add the root elements directly to config
        for key, value in config_yaml.items():
            if key != '_yaml':
                config[key] = value

        return config
    except FileNotFoundError:
        logging.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML configuration: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error loading configuration: {e}")
        sys.exit(1)
