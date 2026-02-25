from mcstatus import BedrockServer
from msm.config.load_config import Config
import logging
from time import monotonic
from datetime import datetime, timezone

# Get logger
log = logging.getLogger("bsm")

class MinecraftServer():
    def __init__(self, cfg: Config):
        self.server = BedrockServer(str(cfg.mc_ip), cfg.mc_port)
        self.player_count = None
        self.server_used_since_boot = False
        self.last_check = monotonic()
        self.server_online = False
        self.server_boot_time = None

        if not cfg.timing_shutdown:
            self.shutdown_enabled = False
            return
        else:
            self.shutdown_enabled = True
        
        self.total_checks = (cfg.timing_shutdown * 60)/5
        self.checks_remaining = self.total_checks
        self.shutdown_requested = False
    
    def tick(self):
        now = monotonic()

        if now - self.last_check >= 5:
            self.update_player_count()
            self.last_check = now
            return True
        else:
            return False

    
    def update_player_count(self):
        if not self.shutdown_enabled:
            return
        
        try:
            status = self.server.status()  # type: ignore
            self.player_count = status.players.online
        except TimeoutError:
            log.info("Server is not online yet")
            return
        except Exception as e:
            log.error(f"Error checking server status: {e}")
            return
        else:
            self.server_online = True
            self.server_boot_time = datetime.now(timezone.utc).isoformat()
        
        someone_online = self.player_count > 0

        if someone_online:
            if not self.server_used_since_boot:
                self.server_used_since_boot = True
                log.info("Server used for the first time")
            log.info(f"{self.player_count} player(s) online")
            self.checks_remaining = self.total_checks
        else:
            self.checks_remaining -= 1
            log.info(f"No one online ({self.checks_remaining} remaining)")

        if self.checks_remaining == 0:
            self.shutdown_requested = True
            log.info("Shutdown requested")

