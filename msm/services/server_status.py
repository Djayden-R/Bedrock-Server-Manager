from mcstatus import BedrockServer
from time import sleep
from datetime import datetime
from msm.config.load_config import Config
import os
import logging

# Get logger
log = logging.getLogger("bsm")


def check_playercount(cfg: Config) -> bool | str | None:

    if cfg.mc_ip and cfg.timing_shutdown and cfg.mc_port is not None:
        server = BedrockServer(str(cfg.mc_ip), int(cfg.mc_port))
        shutdown_sec = cfg.timing_shutdown * 60
        amount_of_checks = max(1, int(shutdown_sec / 10))
        interval_seconds = 10
    else:
        raise ValueError(
            "Cannot check player count: "
            f"{'Minecraft ip not defined' if not cfg.mc_ip else ''} "
            f"{'port not defined' if cfg.mc_port is None else ''} "
            f"{'and timing not defined' if not cfg.timing_shutdown else ''}"
        )

    times_no_one = 0
    server_used = False

    while True:
        try:
            status = server.status()  # type: ignore
            online_players = status.players.online
        except Exception as e:
            log.error(f"[{datetime.now()}] Error checking server status: {e}")
            sleep(interval_seconds)
            # Skip loop if player count is not found 
            continue

        if online_players == 0:
            times_no_one += 1
            log.info(f"[{datetime.now()}] No one online ({times_no_one}/{amount_of_checks})")
        elif online_players > 0:
            log.info(f"[{datetime.now()}] Someone online")
            server_used = True
            times_no_one = 0
        else:
            log.error(f"[{datetime.now()}] Unexpected value: {status.players.online}")
            return None

        # If no one has been online for the set time, exit function
        if times_no_one >= amount_of_checks:
            # Check if no_shutdown flag is present, reset loop if it is
            if cfg.path_base:
                if os.path.exists(os.path.join(cfg.path_base, "no_shutdown.flag")):
                    times_no_one = 0
                    log.info(f"[{datetime.now()}] No-shutdown flag found, restarting check...")
                else:
                    # Return if a backup is needed
                    return True if server_used else False

        # Wait before next check
        sleep(interval_seconds)
