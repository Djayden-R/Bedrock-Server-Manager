import requests
from datetime import datetime
from msm.config.load_config import Config
import logging

# Get logger
log = logging.getLogger("bsm")

url = "https://api.dynu.com/nic/update"


def test_DNS(host_name: str, password: str) -> bool:
    response = update_DNS_raw(host_name, password)

    if "good" in response or "nochg" in response:
        return True
    else:
        return False

def update_DNS(cfg: Config):
    if not (cfg.dynu_domain and cfg.dynu_pass):
        return
    
    response = update_DNS_raw(cfg.dynu_domain, cfg.dynu_pass)

    if "good" in response:
        log.info(f"DDNS update successful")
    elif "nochg" in response:
        log.info(f"DDNS update successful (IP is unchanged)")
    else:
        log.error(f"DDNS update failed: {response}")
    
    
def update_DNS_raw(host_name: str, password: str):
    params = {
        "hostname": host_name,
        "password": password,
    }

    response = requests.get(url, params=params)
    return response.text
