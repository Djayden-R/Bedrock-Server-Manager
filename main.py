from msm.services.ddns_update import update_DNS
from msm.services.server_status import check_playercount
from msm.services.check_ha import entity_status
from msm.config.load_config import Config
import msm.core.backup as backup
from msm.core.minecraft_updater import get_console_bridge, update_minecraft_server
import sys
from datetime import datetime
from enum import Enum
import subprocess
import os
from pathlib import Path
import logging
from rich.logging import RichHandler

# Logger setup
log = logging.getLogger("bsm")
log.setLevel(logging.INFO)

handler = RichHandler(
    rich_tracebacks=True,
    show_time=True,
    show_level=True,
    markup=True,
    log_time_format="%H:%M:%S.%f"
)
log.addHandler(handler)
log.propagate = False


class Mode(Enum):
    NORMAL = "normal"  # Normal operating mode, shutdown after defined time and create local backup and hdd backup (depends on config)
    DRIVE_BACKUP = "drive backup"  # Upload latest backup to drive, then shutdown
    INVALID = "invalid time"  # Boot up at an invalid time, just shutdown
    CONFIGURATION = "config"  # go through set-up process


def shutdown(reboot: bool = False):
    cmd = ["/usr/sbin/shutdown"]
    if reboot:
        cmd.append("-r")
    cmd.append("now")
    subprocess.run(cmd)


def hour_valid(hour: int) -> bool:
    if cfg.timing_begin_valid and cfg.timing_end_valid:
        return cfg.timing_begin_valid < hour < cfg.timing_end_valid
    else:
        return False


def get_mode():
    # Check if configuration is needed
    try:
        global cfg
        cfg = Config.load()
    except FileNotFoundError:
        return Mode.CONFIGURATION

    time = datetime.now()
    hour = time.hour
    log.info(f"Current hour: {hour}")

    if not (cfg.timing_begin_valid and cfg.timing_end_valid) or hour_valid(hour):
        return Mode.NORMAL
    elif hour == cfg.timing_drive_backup:
        return Mode.DRIVE_BACKUP
    else:
        return Mode.INVALID


def start_server(cfg: Config):
    if cfg.path_base:
        mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
        subprocess.run(['bash', mc_updater_path+'/updater/startserver.sh', mc_updater_path])
    else:
        raise ValueError("Base path is not defined")


def stop_server(cfg: Config):
    if cfg.path_base:
        mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
        subprocess.run(['bash', mc_updater_path+'/updater/stopserver.sh', mc_updater_path])
    else:
        raise ValueError("Base path is not defined")


def normal_operation():
    if cfg.dynu_domain and cfg.dynu_pass:
        update_DNS(cfg)

    server_updated = update_minecraft_server(cfg) # Try to update server and save whether it was updated

    if cfg.path_base:
        console_bridge = Path(os.path.join(cfg.path_base, "console_bridge", "MCXboxBroadcastStandalone.jar"))
        console_bridge_used = console_bridge.exists()
    else:
        raise ValueError("Base path is not defined")

    if server_updated:
        if console_bridge_used:
            get_console_bridge(cfg)
        shutdown(reboot=True)
        exit(0)

    else:
        start_server(cfg)
        if console_bridge_used:
            console_bridge_dir = os.path.join(cfg.path_base, "console_bridge")
            subprocess.Popen(["java", "-jar", str(console_bridge)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=console_bridge_dir)

    if cfg.timing_shutdown:
        while True:
            needs_backup = check_playercount(cfg)
            if needs_backup is True:  # server needs backup
                if entity_status(cfg, cfg.ha_shutdown_entity):  # type: ignore
                    log.info("Shutting down Minecraft server...")
                    stop_server(cfg)
                    if cfg.backup_directories:
                        log.info("Starting backup script")
                        backup.main(cfg, type="quick")
                    else:
                        log.info("No backup directories, skipping backup")
                    log.info("Shutting down...")
                    shutdown()
                else:
                    log.info("Auto shutdown is shut off...")
            elif needs_backup is False:  # server doesn't need backup
                if entity_status(cfg, cfg.ha_shutdown_entity):  # type: ignore
                    log.info("No one online, but server was not used, backup is not needed")
                    log.info("Shutting down Minecraft server...")
                    stop_server(cfg)
                    log.info("Shutting down...")
                    shutdown()
            elif needs_backup is None:  # error occured
                log.error("Error occurred in check_playercount, cannot proceed with shutdown/backup")
                break
    else:
        log.warning("Auto shutdown is off, this is not reccomended, backups will not work")


def drive_backup():
    log.info("Only backing up to drive")
    backup.main(cfg, type="drive")
    log.info("Shutting down...")
    shutdown()


def main():
    mode = get_mode()
    log.info(f"Current mode: {mode.value}")

    if mode == Mode.NORMAL:
        normal_operation()
    elif mode == Mode.DRIVE_BACKUP:
        drive_backup()
    elif mode == Mode.INVALID:
        log.info("Invalid time, shutting down")
        shutdown()
        sys.exit(1)
    elif mode == Mode.CONFIGURATION:
        from msm.config import configuration
        if getattr(sys, 'frozen', False):
            configuration.run_setupsh()
        configuration.main()


if __name__ == "__main__":
    main()
