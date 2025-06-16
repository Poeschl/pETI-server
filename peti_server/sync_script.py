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

from peti_server.models import (Configuration, SyncFolder,
                                ETI_LAUNCHER_DATABASE_PATH, LOCAL_DB_NAME)


def get_eti_database(config: Configuration) -> Path:
    """
    Returns the path to the ETI database file.

    Args:
        config: Configuration object containing sync settings

    Returns:
        Path to the ETI database file
    """
    db_path = Path(config.data_dir) / LOCAL_DB_NAME

    # Check for new database file in the sync directory
    new_db_path = Path(config.sync_dir) / ETI_LAUNCHER_DATABASE_PATH
    if new_db_path.exists():
        logging.info(f"Updating database from download: {new_db_path}")
        try:
            shutil.copy(new_db_path, db_path)
        except IOError as e:
            logging.error(f"Could not copy updated games database: {e}")

    if not db_path.exists():
        logging.error(f"ETI Database file not found: {db_path}")
        raise FileNotFoundError(f"ETI Database file not found: {db_path}")

    return db_path


def get_games_from_db(config: Configuration, db_path: Path) -> list:
    """
    Retrieves game folders from the ETI database.

    Args:
        config: Configuration object containing sync settings

    Returns:
        List of SyncFolder objects representing game folders
    """
    game_folders = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

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
    except sqlite3.Error as e:
        logging.error(f"SQLite error during games and tool retrieval: {e}")
        raise

    return game_folders


def get_discarded_from_db(config: Configuration, db_path: Path) -> list:
    """
    Retrieves discarded game folders from the ETI database.

    Args:
        config: Configuration object containing sync settings

    Returns:
        List of SyncFolder objects representing discarded game folders
    """
    removed_folders = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get discarded items for removal
        cursor.execute(
            "SELECT game_key, game_id FROM discarded ORDER BY del_id")
        for row in cursor.fetchall():
            secret_key, folder_id = row
            removed_folders.append(
                SyncFolder(config, folder_id, folder_id, secret_key))

        conn.close()
    except sqlite3.Error as e:
        logging.error(f"SQLite error during discarded retrieval: {e}")
        raise

    return removed_folders


def update_game_folders(config: Configuration) -> None:
    """
    Handles the start operation for the sync server

    Args:
        config: Configuration object containing sync settings
    """

    # Add the core system folders
    system_folders = []
    for folder_name, values in config.get_folders().items():
        system_folders.append(
            SyncFolder(config, folder_name, secret=values.get('secret', ''))),

    # Sync the system folders
    for folder in system_folders:
        folder.sync()

    game_folders = get_games_from_db(config, get_eti_database(config))

    # Process all game folders
    for folder in game_folders:
        logging.info(f"Updating {folder.secret} ({folder.name})...")
        folder.sync()
        folder.update_prefs()
        time.sleep(1)

    if not config.keep_discarded_games:
        removed_folders = get_discarded_from_db(config,
                                                get_eti_database(config))

        # Remove discarded folders
        for folder in removed_folders:
            logging.info(f"Removing {folder.secret} ({folder.id})...")
            folder.remove()
            time.sleep(1)

            # Remove local folder if it exists
            folder_path = os.path.join(config.sync_dir, folder.id)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)

    logging.info("Game folders updated on sync server.")


def cleanup(config: Configuration) -> None:
    """
    Handles the cleanup operation, removing synchronized data

    Args:
        config: Configuration object containing sync settings
    """
    response = input("Should all synchronized data be removed? [yes|no] ")
    if response.lower() == "yes":

        # Remove all files in sync directory
        try:
            for item in Path(config.sync_dir).glob("*"):
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)
            logging.info("Cleanup completed.")
        except Exception as e:
            logging.error(f"Error during cleanup: {e}")


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
    parser.add_argument('--keep_discarded_games',
                        action='store_true',
                        help='Dont remove discarded games from sync')

    args = parser.parse_args()

    config = Configuration(args.config, args.keep_discarded_games)

    if args.action == 'update':
        update_game_folders(config)
    elif args.action == 'cleanup':
        cleanup(config)


if __name__ == "__main__":
    main()
