from mcstatus import BedrockServer
from msm.config.load_config import Config
import logging
from time import monotonic

# Get logger
log = logging.getLogger("bsm")

class MinecraftServer():
    def __init__(self, cfg: Config):
        self.server = BedrockServer(str(cfg.mc_ip), cfg.mc_port)
        self.player_count = None
        self.server_used = False

        if not (cfg.timing_shutdown and cfg.mc_ip and cfg.mc_port):
            self.shutdown_mode = False
            return
        else:
            self.shutdown_mode = True
        
        self.total_checks = (cfg.timing_shutdown * 60)/10
        self.checks_remaining = self.total_checks
        self.last_check = monotonic()
        self.shutdown_requested = False
    
    def tick(self):
        now = monotonic()

        if now - self.last_check >= 5:
            self.update_player_count()
            return True
        else:
            return False

    
    def update_player_count(self):
        if not self.shutdown_mode:
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

        if self.player_count == 0:
            self.checks_remaining -= 1
            log.info(f"No one online ({self.checks_remaining} remaining)")
        else:
            if not self.server_used:
                self.server_used = True
                log.info("Server used for the first time")
            log.info(f"{self.player_count} player(s) online")
            self.checks_remaining = self.total_checks

        if self.shutdown_mode:
            if self.checks_remaining == 0:
                self.shutdown_requested = True

