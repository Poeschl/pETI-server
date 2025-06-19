"""
pETI Sync Server - Python version

This script manages synchronization tasks based on a configuration file.
It handles starting, stopping, cleaning up, and updating synchronization keys.
"""

import argparse
import concurrent
import concurrent.futures
import logging
import os
import shutil
import sqlite3
import tarfile
from pathlib import Path

import requests

from peti_server.models import (Configuration, SyncFolder)

ETI_SYNC_SERVER_DOWNLOAD_URL = "https://www.eti-lan.xyz/sync_server.tar"
ETI_LAUNCHER_DATABASE_PATH = "eti_launcher/update/game.db"
LOCAL_DB_NAME = "game.db"


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(
        description='pETI Sync Server - Python Implementation')
    parser.add_argument('action',
                        choices=['update', 'cleanup'],
                        help='Action to perform')
    parser.add_argument('--config',
                        default='/app/eti-config.yaml',
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


def update_game_folders(config: Configuration) -> None:
    """
    Handles the start operation for the sync server

    Args:
        config: Configuration object containing sync settings
    """

    # Try to prepare the ETI database
    try:
        database = get_eti_database(config)
    except FileNotFoundError:
        logging.error(
            "ETI Database file not found. Downloading initial database...")
        download_initial_game_db(config)
        database = get_eti_database(config)

    # Add the core system folders
    system_folders = []
    for folder_name, values in config.get_folders().items():
        system_folders.append(
            SyncFolder(config, folder_name, secret=values.get('secret', ''))),

    logging.info("\n================================")
    logging.info("Add/Update system tools...")
    # Sync the system folders
    for folder in system_folders:
        folder.sync()

    # Process all game folders
    logging.info("\n================================")
    logging.info("Prepare lists of games...")

    allow_list = get_games_from_db(config, database)
    deny_list = get_discarded_from_db(config, database)

    denied_folder_ids = set(config.game_deny_list)
    moved_to_deny = [
        folder for folder in allow_list if folder.id in denied_folder_ids
    ]
    allow_list = [
        folder for folder in allow_list if folder.id not in denied_folder_ids
    ]
    for folder in moved_to_deny:
        logging.info(f"Move game {folder.name}|{folder.id} to deny list...")
        deny_list.append(folder)

    logging.info(f"Found {len(allow_list)} allowed games to sync.")
    logging.info(f"Found {len(deny_list)} games to remove if existing.")

    logging.info("\n================================")
    logging.info("Synchronizing allowed games...")
    with concurrent.futures.ThreadPoolExecutor() as executor:

        def process_folder(folder):
            logging.info(f"[{folder.name}|{folder.id}] processing...")
            folder.sync()
            folder.update_prefs()
            return folder.name

        # Submit all folders for parallel processing
        futures = [
            executor.submit(process_folder, folder) for folder in allow_list
        ]

        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                folder_name = future.result()
                logging.debug(f"[{folder_name}] completed")
            except Exception as e:
                logging.error(f"Error processing: {e}")

    if not config.keep_discarded_games:
        logging.info("\n================================")
        logging.info("Removing denied games...")

        # Remove discarded folders
        for folder in deny_list:
            logging.info(f"Removing {folder.name} ({folder.secret})...")
            folder.remove()

            # Remove local folder if it exists
            folder_path = os.path.join(config.sync_dir, folder.id)
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)

    logging.info("\n================================")
    logging.info("Games synchronized")


def cleanup(config: Configuration) -> None:
    """
    Handles the cleanup operation, removing synchronized data

    Args:
        config: Configuration object containing sync s++ettings
    """
    response = input("Should all synchronized data be removed? [yes|no] ")
    if response.lower() == "yes":

        # Remove all known game folders
        database = get_eti_database(config)
        game_folders = get_games_from_db(config, database)
        game_folders += get_discarded_from_db(config, database)

        with concurrent.futures.ThreadPoolExecutor() as executor:

            def process_folder(folder):
                logging.info(f"[{folder.name}|{folder.id}] processing...")
                folder.remove()

                # Remove local folder if it exists
                folder_path = os.path.join(config.sync_dir, folder.id)
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
                return folder.name

            # Submit all folders for parallel processing
            futures = [
                executor.submit(process_folder, folder)
                for folder in game_folders
            ]

            # Wait for all tasks to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    folder_name = future.result()
                    logging.debug(f"[{folder_name}] completed")
                except Exception as e:
                    logging.error(f"Error processing folder: {e}")


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


def download_initial_game_db(config: Configuration) -> None:
    """
    Downloads the initial game database from the sync server.

    Args:
        config: Configuration object containing sync settings
    """

    logging.info("Downloading initial game database...")

    try:
        response = requests.get(ETI_SYNC_SERVER_DOWNLOAD_URL,
                                allow_redirects=True)
        dl_path = Path(config.data_dir) / "download"
        tar_path = dl_path / Path(ETI_SYNC_SERVER_DOWNLOAD_URL).name

        # Write the tar file to disk
        dl_path.mkdir(parents=True, exist_ok=True)
        with open(tar_path, "wb") as f:
            f.write(response.content)

        # Extract games database
        downloaded_db = Path(config.data_dir) / LOCAL_DB_NAME
        with tarfile.open(tar_path, "r") as tar:
            for member in tar.getmembers():
                if member.name.endswith(LOCAL_DB_NAME):
                    tar.extract(member, path=dl_path, filter='data')
                    shutil.move(dl_path / member.path.lstrip('/'),
                                downloaded_db)
                    break
        # Clean up
        shutil.rmtree(dl_path, ignore_errors=True)

        if downloaded_db.exists():
            logging.info(
                f"Initial game database downloaded to {downloaded_db}")
        else:
            logging.error(
                f"Download failed: {LOCAL_DB_NAME} not found in tarball.")
    except requests.RequestException as e:
        logging.error(f"Error downloading initial game database: {e}")
        raise
    except tarfile.TarError as e:
        logging.error(f"Error extracting tar file: {e}")
        raise


if __name__ == "__main__":
    main()
