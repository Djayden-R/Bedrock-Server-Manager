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
    NORMAL = "normal"
    DRIVE_BACKUP = "drive backup"  
    INVALID = "invalid time"  
    CONFIGURATION = "config"


def shutdown(reboot: bool = False):
    log.info("Shutting down...")
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
    mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
    subprocess.run(['bash', mc_updater_path+'/updater/startserver.sh', mc_updater_path])


def stop_server(cfg: Config):
    log.info("Shutting down Minecraft server...")

    mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
    subprocess.run(['bash', mc_updater_path+'/updater/stopserver.sh', mc_updater_path])


def normal_operation():
    update_DNS(cfg)

    server_updated = update_minecraft_server(cfg) # Try to update server and save whether it was updated

    console_bridge = Path(os.path.join(cfg.path_base, "console_bridge", "MCXboxBroadcastStandalone.jar"))
    console_bridge_used = console_bridge.exists()

    if server_updated:
        if console_bridge_used:
            get_console_bridge(cfg)
        shutdown(reboot=True)

    else:
        start_server(cfg)
        if console_bridge_used:
            console_bridge_dir = os.path.join(cfg.path_base, "console_bridge")
            subprocess.Popen(["java", "-jar", str(console_bridge)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=console_bridge_dir)

    if cfg.timing_shutdown:
        while True:
            server_used = check_playercount(cfg)
            auto_shutdown_enabled = entity_status(cfg)

            if server_used:
                if auto_shutdown_enabled:
                    stop_server(cfg)

                    if cfg.backup_directories:
                        backup.main(cfg, type="quick")
                    else:
                        log.info("No backup directories, skipping backup")
                    
                    shutdown()
                else:
                    log.info("Auto shutdown is shut off...")
            else:
                if auto_shutdown_enabled:
                    log.info("No one online, but server was not used, backup is not needed")
                    log.info("Shutting down Minecraft server...")
                    stop_server(cfg)
                    log.info("Shutting down...")
                    shutdown()
    else:
        log.warning("Auto shutdown is off, this is not reccomended, backups will not work")


def drive_backup():
    log.info("Only backing up to drive")
    backup.main(cfg, type="drive")
    log.info("Shutting down...")
    shutdown()


def main():
    if not cfg.path_base:
        raise ValueError("Base path is not defined")
    
    mode = get_mode()
    log.info(f"Current mode: {mode.value}")

    if mode == Mode.NORMAL:
        # Standard operating mode, shutdown after defined time and create backups (depending on config)
        normal_operation()
    elif mode == Mode.DRIVE_BACKUP:
        # Upload latest backup to drive, then shutdown
        drive_backup()
    elif mode == Mode.INVALID:
        # Shutdown server if started at incorrect time
        log.warning("Invalid time, shutting down")
        shutdown()
        sys.exit(1)
    elif mode == Mode.CONFIGURATION:
        # Run setup file and go through setup questions
        from msm.config import configuration
        if getattr(sys, 'frozen', False):
            configuration.run_setupsh()
        configuration.main()


if __name__ == "__main__":
    main()
