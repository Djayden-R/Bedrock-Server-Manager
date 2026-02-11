import requests
from datetime import datetime
from msm.config.load_config import Config
import logging

# Get logger
log = logging.getLogger("bsm")

url = "https://api.dynu.com/nic/update"


def test_update_DNS():
    pass

def update_DNS(cfg: Config):
    if not (cfg.dynu_domain and cfg.dynu_pass):
        return
    
    
def update_DNS_raw(host_name: str, port: int):
    


    params = {
        "hostname": cfg.dynu_domain if cfg else domain,
        "password": cfg.dynu_pass if cfg else password,
    }

    response = requests.get(url, params=params)

    if "good" in response.text:
        log.info(f"DDNS update successful")
    elif "nochg" in response.text:
        log.info(f"DDNS update successful (IP is unchanged)")
    else:
        log.error(f"DDNS update failed: {response.text}")
    
    if test:
        return True
