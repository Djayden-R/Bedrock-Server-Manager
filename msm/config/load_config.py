import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import os
from ipaddress import IPv4Address, IPv6Address
import sys


@dataclass(frozen=True)
class Config:
    ## Required

    # Minecraft Server
    mc_ip: IPv4Address | IPv6Address
    mc_port: int

    # Paths
    path_base: str
    
    ## Optional

    # Home Assistant
    ha_ip: Optional[str] = None
    ha_token: Optional[str] = None
    ha_update_entity: Optional[str] = None
    ha_shutdown_entity: Optional[str] = None

    # Dynu DNS
    dynu_pass: Optional[str] = None
    dynu_domain: Optional[str] = None

    # Backup settings
    backup_local_path: Optional[str] = None
    backup_hdd_path: Optional[str] = None
    backup_drive_name: Optional[str] = None
    backup_directories: Optional[List[str]] = None

    # Timing
    timing_begin_valid: Optional[int] = None
    timing_end_valid: Optional[int] = None
    timing_shutdown: Optional[int] = None
    timing_drive_backup: Optional[int] = None

    @classmethod
    def load(cls) -> "Config":
        program_location = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
        dir_path = os.path.dirname(program_location)
        config_location = Path(os.path.join(dir_path, "config.yaml"))

        if not config_location.exists():
            raise FileNotFoundError(f"Config file not found: {config_location}")

        data = yaml.safe_load(config_location.read_text())

        # Flatten nested structure
        flat_data = {}
        for section, values in data.items():
            if isinstance(values, dict):
                for key, value in values.items():  # type: ignore
                    flat_data[f"{section}_{key}"] = value
            else:
                flat_data[section] = values

        return cls(**flat_data)  # type: ignore
