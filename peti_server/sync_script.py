"""
pETI Sync Server - Python version

This script manages synchronization tasks based on a configuration file.
It handles starting, stopping, cleaning up, and updating synchronization keys.
"""

import argparse
import logging
import os
import shutil
import sqlite3
import time
from pathlib import Path

import requests

# Import classes from models module
from peti_server.models import (Configuration, SyncFolder, ApiMethod)


def update_game_folders(config_path: str = "/root/eti-config.yaml") -> None:
    """
    Handles the start operation for the sync server

    Args:
        config_path: Path to the configuration file
    """

    config = Configuration(config_path)

    # Add the core system folders
    system_folders = []
    for folder_name, values in config.get_folders().items():
        system_folders.append(
            SyncFolder(config, folder_name, secret=values.get('secret', ''))),

    # Sync the system folders
    for folder in system_folders:
        folder.sync()

    # Read games from game.db
    try:
        conn = sqlite3.connect("/root/game.db")
        cursor = conn.cursor()

        game_folders = []

        # Get games data
        cursor.execute(
            "SELECT game_key, game_title, game_id FROM games ORDER BY db_id")
        for row in cursor.fetchall():
            secret_key, title, folder_id = row
            game_folders.append(
                SyncFolder(config, title, folder_id, secret_key))

        # Get tools data
        cursor.execute(
            "SELECT tool_key, tool_name, tool_id FROM tools ORDER BY db_id")
        for row in cursor.fetchall():
            secret_key, title, folder_id = row
            game_folders.append(
                SyncFolder(config, title, folder_id, secret_key))

        conn.close()

        # Process all game folders
        for folder in game_folders:
            logging.info(f"Updating {folder.secret} ({folder.name})...")
            folder.sync()
            folder.update_prefs()
            time.sleep(1)

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")

    # Copy updated game database
    try:
        shutil.copy(f"/lan/eti_launcher/update/game.db", "/root/game.db")
    except FileNotFoundError as e:
        logging.error(f"File copy error: {e}")
    except IOError as e:
        logging.error(f"File copy IO error: {e}")

    logging.info("Game folders inserted into sync server.")


def cleanup(config_path: str = "/root/eti-config.yaml") -> None:
    """
    Handles the cleanup operation, removing synchronized data

    Args:
        config_path: Path to the configuration file
    """
    response = input("Should all synchronized data be removed? [yes|no] ")
    if response.lower() == "yes":
        config = Configuration(config_path)

        # Remove all files in sync directory
        try:
            for item in Path("/lan").glob("*"):
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
            logging.info("Cleanup completed.")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


def update_keys(config_path: str = "/root/eti-config.yaml") -> None:
    """
    Handles updating synchronization keys

    Args:
        config_path: Path to the configuration file
    """
    config = Configuration(config_path)

    # Copy database
    try:
        shutil.copy("/lan/eti_launcher/update/game.db", "/root/game.db")
    except (FileNotFoundError, IOError) as e:
        logging.error(f"Database copy error: {e}")

    # Process game folders from database
    try:
        conn = sqlite3.connect("/root/game.db")
        cursor = conn.cursor()

        game_folders = []

        # Get games data
        cursor.execute(
            "SELECT game_key, game_title, game_id FROM games ORDER BY db_id")
        for row in cursor.fetchall():
            secret_key, title, folder_id = row
            game_folders.append(
                SyncFolder(config, title, folder_id, secret_key))

        # Process discarded items for removal
        cursor.execute(
            "SELECT game_key, game_id FROM discarded ORDER BY del_id")
        removed_folders = []
        for row in cursor.fetchall():
            secret_key, folder_id = row
            removed_folders.append(
                SyncFolder(config, folder_id, folder_id, secret_key))

        conn.close()

        # Sync all game folders
        for folder in game_folders:
            logging.info(f"Updating {folder.secret} ({folder.name})...")
            folder.sync()
            folder.update_prefs()
            time.sleep(1)

        # Remove discarded folders
        for folder in removed_folders:
            logging.info(f"Removing {folder.secret} ({folder.id})...")
            folder.remove()
            time.sleep(1)

            # Remove local folder if it exists
            folder_path = os.path.join(config.sync_dir, folder.id)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)

    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")

    # Check for sync_server.service file and update if needed
    service_file = os.path.join(config.sync_dir, "eti_sync_server",
                                "sync_server.service")
    if os.path.isfile(service_file):
        logging.info("Updating Sync Server Service...")
        try:
            shutil.copy(service_file, "/etc/init.d/eti")
        except IOError as e:
            logging.error(f"Error copying service file: {e}")

        logging.info("Updating Sync Server Info...")
        info_file = os.path.join(config.sync_dir, "eti_sync_server",
                                 "sync_server.info")
        try:
            shutil.copy(info_file, "/etc/rc.local")
        except IOError as e:
            logging.error(f"Error copying info file: {e}")


def stop(config_path: str = "/root/eti-config.yaml") -> None:
    """
    Stop the sync server

    Args:
        config_path: Path to the configuration file
    """
    config = Configuration(config_path)
    logging.info("Stopping pETI sync server...")

    try:
        exit_url = config.get_api_url('shutdown')
        if exit_url:
            response = requests.get(exit_url,
                                    auth=(config.user, config.password))
            logging.info(f"Server shutdown initiated: {response.status_code}")
            time.sleep(2)
    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending shutdown request: {e}")

    logging.info("Service stopped")


def main():
    """Main entry point for the script"""
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(
        description='pETI Sync Server - Python Implementation')
    parser.add_argument('action',
                        choices=['update', 'stop', 'cleanup', 'update_keys'],
                        help='Action to perform')
    parser.add_argument('--config',
                        default='/root/eti-config.yaml',
                        help='Path to the configuration file')

    args = parser.parse_args()

    if args.action == 'update':
        update_game_folders(args.config)
    elif args.action == 'stop':
        stop(args.config)
    elif args.action == 'cleanup':
        cleanup(args.config)
    elif args.action == 'update_keys':
        update_keys(args.config)


if __name__ == "__main__":
    main()
