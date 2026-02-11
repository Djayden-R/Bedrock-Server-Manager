import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from ipaddress import IPv4Address, IPv6Address
import sys


@dataclass(frozen=True)
class Config:
    ## Required

    # Minecraft Server
    mc_ip: IPv4Address | IPv6Address
    mc_port: int

    # Paths
    path_base: Path
    
    ## Optional

    # Home Assistant
    mqtt_ip: Optional[str] = None
    mqtt_port: Optional[int] = None
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None

    # Dynu DNS
    dynu_pass: Optional[str] = None
    dynu_domain: Optional[str] = None


    # Backup settings
    backup_local_path: Optional[Path] = None
    backup_hdd_path: Optional[Path] = None
    backup_drive_name: Optional[Path] = None
    backup_directories: Optional[List[Path]] = None

    # Timing
    timing_begin_valid: Optional[int] = None
    timing_end_valid: Optional[int] = None
    timing_shutdown: Optional[int] = None
    timing_drive_backup: Optional[int] = None

    @classmethod
    def load(cls) -> "Config":
        # Check if program is bundled
        program_frozen = getattr(sys, "frozen", False)

        # Get path where program is run
        if program_frozen:
            program_folder_path = Path(sys.executable).resolve().parent
        else:
            program_folder_path = Path(__file__).resolve().parent
        
        config_path = program_folder_path / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")


        data: dict = yaml.safe_load(config_path.read_text())



        """
        The code below turns yaml structure like this

        server:
            ip: 21
            port: 22
        backup: true
        
        into a flat dictionary like this

        {
            "server_ip": 21,
            "server_port": 22,
            backup: True
        }
        
        This dictionary is then returned as a Config class
        """

        # Flatten nested structure
        flat_data: dict = {}

        for section, values in data.items():
            # Section contains nested dictionary
            if isinstance(values, dict):
                for key, value in values.items():
                    flat_data[f"{section}_{key}"] = value
            else:
                flat_data[section] = values

        return Config(**flat_data)
