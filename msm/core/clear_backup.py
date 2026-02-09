import os
import psutil
from datetime import datetime
from msm.config.load_config import Config
from pathlib import Path
from typing import Iterable
import logging

# Get logger
log = logging.getLogger("bsm")


def get_backup_folders(location: Path):
    """Gets every folder in the location and sorts them"""
    backup_folders = sorted(folder for folder in os.listdir(location) if os.path.isdir(os.path.join(location, folder)))
    return backup_folders


def get_sorted_list(base_path: Path, backup_folders: Iterable[str]) -> dict[str, list[Path]]:
    """
    Function wil return a dictionary with dates
    and their the backups in a list eg. "24-03-2025":["backup1", "backup2"]
    """
    backup_per_date: dict[str, list[Path]] = {}
    for folder in backup_folders:
        folder_path = base_path / folder
        if not folder_path.is_dir():
            continue
        backups = [Path(p.name) for p in sorted(folder_path.iterdir()) if p.is_file()]
        backup_per_date[folder] = backups
    return backup_per_date


def remove_oldest_backup(backup_dates: Iterable[str], backup_per_date: dict[str, list[Path]], base_path: Path, freed_space: float):
    for date in backup_dates:
        if len(backup_per_date[date]) > 1:
            oldest_backup_date = date
            oldest_backups = sorted(backup_per_date[oldest_backup_date])
            oldest_backup = oldest_backups[0]

            oldest_backup_path = os.path.join(base_path, oldest_backup_date, oldest_backup)
            oldest_backup_size = os.path.getsize(oldest_backup_path) / (1024 ** 3)

            log.info(f"\nRemoving old backup from {oldest_backup_date} folder: {oldest_backups}")
            log.info(f"Oldest backup: {oldest_backup} ({oldest_backup_size:.2f} GB)")
            log.info(f"Removing old backup: {oldest_backup_date} at {oldest_backup}")
            os.remove(oldest_backup_path)
            freed_space += oldest_backup_size
            #  Remove the backup from the dictionary to avoid trying to delete it again
            backup_per_date[oldest_backup_date].remove(oldest_backup)
            return freed_space  # Only remove one file per function call

    return freed_space


def clear_old_backups(backup_per_date: dict[str, list[Path]], required_free_space: float, base_path: Path):
    """Function will remove old backups based on the folder name (the date) and name of the backup (the time).
    The backup_per_date is a dictionary in this format: "24-03-2025":["backup1", "backup2"]"""

    all_dates = backup_per_date.keys()

    last_7_days: list[str] = []
    last_30_days: list[str] = []
    old_backups: list[str] = []

    amount_backups_last_7 = 0
    amount_backups_last_30 = 0
    amount_backups_old = 0

    freed_space = 0

    for date in all_dates:
        date_object = datetime.strptime(date, "%Y-%m-%d")
        current_date = datetime.now()
        backup_age = (current_date - date_object).days
        
        if backup_age <= 7:
            last_7_days.append(date)
        elif backup_age <= 30:
            last_30_days.append(date)
        else:
            old_backups.append(date)

    log.info(f"Last 7 days backups: {last_7_days} with a total of {amount_backups_last_7} backups")
    log.info(f"Last 30 days backups: {last_30_days} with a total of {amount_backups_last_30} backups")
    log.info(f"Old backups: {old_backups} with a total of {amount_backups_old} backups")

    previous_freed_space = -1

    while freed_space < required_free_space:
        # Check to prevent infinite loops
        if freed_space == previous_freed_space:
            log.info(f"No more space can be freed. Current freed space: {freed_space:.2f} GB, Required: {required_free_space:.2f} GB")
            break
        previous_freed_space = freed_space

        if old_backups:
            directory = old_backups
        elif last_30_days:
            directory = last_30_days
        elif freed_space < required_free_space:
            log.error("No more old backups to remove, but not enough space freed.")
            break
        else:
            directory = None

        if directory is not None:
            freed_space = remove_oldest_backup(directory, backup_per_date, base_path, freed_space)
    log.info(f"Total freed space: {freed_space:.2f} GB")


def clear_duplicate_files(backup_folders: Iterable[str], base_path: Path, backup_per_date: dict[str, list[Path]]):
    """Function will check for duplicate files in the backup folders
    based on size and remove them"""

    size_list: list[int] = []
    duplicates = 0

    for folder in backup_folders:
        folder_path = os.path.join(base_path, folder)
        backups = os.listdir(folder_path)

        for backup in backups:
            backup_path = os.path.join(folder_path, backup)
            size = os.path.getsize(backup_path)

            file_new = size not in size_list

            if file_new:
                size_list.append(size)

            else:
                log.info("Duplicate found")
                duplicates += 1
                os.remove(backup_path)
                log.info(f"Removed {backup_path} with size {size/(1024**3):.2f} GB")

                # Remove the backup from the dictionary to keep it in sync
                if folder in backup_per_date and Path(backup) in backup_per_date[folder]:
                    backup_per_date[folder].remove(Path(backup))

    return duplicates


def clear_backups(location: Path, required_free_space: float):

    backup_folders = get_backup_folders(location)
    backup_per_date = get_sorted_list(location, backup_folders)

    duplicates_amount = clear_duplicate_files(backup_folders, location, backup_per_date)
    clear_old_backups(backup_per_date, required_free_space, location)

    log.info(f"There are a total of {duplicates_amount} duplicate files found, all of them were removed")


def check_and_clear(location: Path, min_free_gb: int, name: str):
    space_left = psutil.disk_usage(str(location)).free / (1024 ** 3)

    log.info(f"{name} free space: {space_left:.2f} GB")

    if space_left < min_free_gb:
        log.info(f"Less than {min_free_gb} GB left on {name}, clearing backup's...")
        required_free_space = min_free_gb - space_left  # in GB
        clear_backups(location, required_free_space)
    else:
        log.info(f"More than {min_free_gb} GB left on {name}, no need to clear backups.")


def main(cfg: Config):
    if cfg.backup_local_path:
        check_and_clear(Path(cfg.backup_local_path), 30, "Local Backup")
    else:
        log.info("Not checking local backup folder, since it doesn't exist")
    if cfg.backup_hdd_path:
        check_and_clear(Path(cfg.backup_hdd_path), 50, "HDD Backup")
    else:
        log.info("Not checking hdd backup folder, since it doesn't exist")
