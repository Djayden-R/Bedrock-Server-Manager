from requests import get, head, RequestException
import urllib3
from msm.config.load_config import Config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def entity_status(cfg: Config) -> bool:
    url = f"{cfg.ha_ip}/api/states/{cfg.ha_shutdown_entity}"

    headers = {
        "Authorization": f"Bearer {cfg.ha_token}",
        "content-type": "application/json",
    }

    response = get(url, headers=headers, timeout=3)
    if response.status_code in [200, 201]:
        dictionary = response.json()
        status = dictionary["state"]
        return status == "on"
    else:
        return True


def check_api(url: str, token: str) -> tuple[bool, bool]:
    base_url = url.rstrip("/")

    # Get authproviders to check if URL belongs to Home Assistant
    try:
        
        response = get(base_url + "/auth/providers", timeout=3)

        # If Home Assistant is found in providers, then the URL is valid
        data = response.json()
        providers = data.get("providers", [])
        url_valid = any(p.get("type", "").lower() == "homeassistant" for p in providers)
    except Exception:
        return False, False

    if not url_valid:
        return False, False
    
    # Try to get status of Home Assistant API
    try:
        headers = {"Authorization": f"Bearer {token}", "content-type": "application/json"}
        response = get(base_url + "/api/", headers=headers, timeout=3)
        data = response.json()
        token_valid = data.get("message", []) == "API running."
    except Exception:
        return True, False
    
    return url_valid, token_valid
