from msm.services.ddns_update import update_DNS
from msm.services.server_status import MinecraftServer
from msm.services.ha_mqtt import setup_mqtt, send_server_state
from msm.config.load_config import Config
import msm.core.backup as backup
from msm.core.minecraft_updater import get_latest_version_console_bridge, update_minecraft_server
import sys
from datetime import datetime
from enum import Enum
import subprocess
import os
from pathlib import Path
import logging
from rich.logging import RichHandler
from time import sleep, monotonic

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
    cmd = ["/usr/sbin/shutdown"]
    if reboot:
        cmd.append("-r")
    cmd.append("now")
    subprocess.run(cmd)


def shutdown_flag_present(cfg: Config):
    if os.path.exists(os.path.join(cfg.path_base, "no_shutdown.flag")):
        return True
    else:
        return False


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


def handle_shutdown(mc: MinecraftServer, cfg: Config):
    backup_needed = mc.server_used
    auto_shutdown_enabled = shutdown_flag_present(cfg)

    if backup_needed:
        if auto_shutdown_enabled:
            stop_server(cfg)

            if cfg.backup_directories:
                backup.main(cfg, type="quick")
            else:
                log.info("No backup directories, skipping backup")
            
            shutdown()
        else:
            log.info("Auto shutdown is turned off...")
    else:
        if auto_shutdown_enabled:
            log.info("Shutting down server without backup...")
            stop_server(cfg)
            shutdown()

def normal_operation():
    if cfg.dynu_domain and cfg.dynu_pass:
        update_DNS(cfg)

    # Try to update server and save whether it was updated
    server_updated = update_minecraft_server(cfg)

    if cfg.path_base:
        console_bridge = Path(os.path.join(cfg.path_base, "console_bridge", "MCXboxBroadcastStandalone.jar"))
        console_bridge_used = console_bridge.exists()
    else:
        raise ValueError("Base path is not defined")

    if server_updated:
        if console_bridge_used:
            get_latest_version_console_bridge(cfg)
        shutdown(reboot=True)
        exit(0)

    else:
        start_server(cfg)
        if console_bridge_used:
            console_bridge_dir = os.path.join(cfg.path_base, "console_bridge")
            subprocess.Popen(["java", "-jar", str(console_bridge)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=console_bridge_dir)
    
    mc = MinecraftServer(cfg)
    mqtt = setup_mqtt(cfg)

    while True:
        if mc.tick():
            send_server_state(mc, mqtt)
            if mc.shutdown_requested:
                handle_shutdown(mc, cfg)
        sleep(0.1)


def drive_backup():
    log.info("Saving backup to drive")
    backup.main(cfg, type="drive")
    log.info("Shutting down...")
    shutdown()


def main():
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
        log.info("Invalid time, shutting down...")
        shutdown()
    elif mode == Mode.CONFIGURATION:
        # Run setup file and go through setup questions
        from msm.config import configuration
        if getattr(sys, 'frozen', False):
            configuration.run_setupsh()
        configuration.main()


if __name__ == "__main__":
    main()
