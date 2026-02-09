import os
import datetime
import subprocess
from time import monotonic
from msm.config.load_config import Config
import shutil
import tempfile
from typing import Optional
from pathlib import Path
import logging

# Get logger
log = logging.getLogger("bsm")


def generate_file_name(cfg: Config):
    """Generate a file and foldername based on the date"""
    date = datetime.datetime.now()

    folder_name = date.strftime("%Y-%m-%d")
    backup_name = date.strftime('backup_%H-%M-%S')

    log.info(f"Name of the file will be: '{backup_name}.zip'")

    return backup_name, folder_name


def generate_zip(cfg: Config, backup_name: str) -> Optional[Path]:
    """Generate a zip file from the backup directories"""
    if cfg.backup_directories and cfg.path_base:
        with tempfile.TemporaryDirectory() as temp_dir:
            for directory in cfg.backup_directories:
                directory = Path(directory)
                # Get name and new location of directory that is getting backed up
                temp_dest = os.path.join(temp_dir, directory.name)
                # Copy directory to destination
                shutil.copytree(directory, temp_dest)
                # Determine a safe output directory for the archive
                archive_base = Path(cfg.path_base) / backup_name
                shutil.make_archive(str(archive_base), "zip", root_dir=temp_dir)
                archive_path = archive_base.with_suffix('.zip')
                log.info(f"Zip file generated: {archive_path}")
                return archive_path
    else:
        log.warning("There are no backup directories or base path defined")
        return None


def backup_drive(cfg: Config, backup_symlink: Path, folder: str, filename: str):
    t_beginning = monotonic()
    # Create the backup folder
    subprocess.run(["rclone", "mkdir", f"{cfg.backup_drive_name}{folder}"])

    log.info("Starting upload to drive...")

    # Get the actual path from the symlink
    backup_path = os.path.realpath(backup_symlink)

    # Upload to drive via rclone
    subprocess.run(["rclone", "copyto", backup_path, f"{cfg.backup_drive_name}{folder}/{filename}"])

    log.info(f"Drive upload successful, took {monotonic()-t_beginning:.1f} seconds")


def update_sym_link(cfg: Config, backup_path: Path):
    location = cfg.path_base

    if location:
        symlink = os.path.join(location, "latest_backup.zip")

        # Check if symlink already exists
        if os.path.islink(symlink):
            os.unlink(symlink)

        # Save latest backup to a symlink, so it can be accessed later for the drive backup
        os.symlink(backup_path, symlink)
        log.info(f"Symlink: '{symlink}' points to '{backup_path}'")
    else:
        raise ValueError("Base path is not defined")


def quick_backup(cfg: Config):
    # Check if directories exist and if local backup doesn't, it creates it
    if not cfg.backup_directories:
        raise ValueError("Please add the directories you want to backup to 'directories'")

    if not (cfg.backup_local_path or cfg.backup_hdd_path):
        return

    # Generate name and a folder with today's date, if it doesn't exist already from an earlier backup
    backup_name, folder_name = generate_file_name(cfg)

    # Check if backup locations and folders exist and create them if the don't
    for backup_location in [cfg.backup_local_path, cfg.backup_local_path]:
        if backup_location:
            backup_folder = os.path.join(backup_location, folder_name)
            if not os.path.exists(backup_folder):
                os.makedirs(backup_folder)
                log.info(f"Created backup folder for today: '{backup_folder}'")

    temp_backup_path = generate_zip(cfg, backup_name)  # Generate a zip file at a predictable location

    if not temp_backup_path:
        return

    # Copy the temp backup to the local folder and/or the hdd folder
    if cfg.backup_local_path:
        backup_folder = os.path.join(cfg.backup_local_path, folder_name)
        if not Path(backup_folder).exists():
            Path(backup_folder).mkdir(parents=True)
        shutil.copy(temp_backup_path, backup_folder)
        update_sym_link(cfg, temp_backup_path)  # Update symlink for later backups

    if cfg.backup_hdd_path:
        backup_folder = os.path.join(cfg.backup_hdd_path, folder_name)
        if not Path(backup_folder).exists():
            Path(backup_folder).mkdir(parents=True)
        shutil.copy(temp_backup_path, backup_folder)


def drive_backup(cfg: Config):
    # The backup is from the day before, so this is calculated
    backup_date = datetime.datetime.now() - datetime.timedelta(days=1)
    folder = backup_date.strftime("backup/%y-%m-%d")
    filename = backup_date.strftime("backup_%H-%M-%S.zip")
    if cfg.backup_local_path:
        # Get backup zip from latest backup symlink
        latest_backup_path = Path(os.path.join(cfg.backup_local_path, "latest_backup.zip")) 
        backup_drive(cfg, latest_backup_path, folder, filename)
    else:
        raise ValueError("Local backup is not defined")


def main(cfg: Config, type: str = "quick"):  
    "Check if a backup to hard drive or to the cloud is needed"
    if type == "quick":
        quick_backup(cfg)
    elif type == "drive":
        drive_backup(cfg)
