from msm.config.load_config import Config
from msm.services.server_status import MinecraftServer
import paho.mqtt.client as mqtt
import json

MQTT_BROKER = "192.168.1.186"
MQTT_PORT = 1883
MQTT_USERNAME = "mqtt-user"
MQTT_PASSWORD = "MQTT_PASSWORD"

MQTT_TOPICS = [
    ("minecraft_server/chat", 0),
    ("minecraft_server/log", 0),
    ("minecraft/players", 0),
    ("minecraft/version", 0),
]

def on_connect(client, userdata, flags, rc):
    connection_success = rc == 0
    if connection_success:
        for topic, qos in MQTT_TOPICS:
            client.subscribe(topic, qos)
    else:
        print(f"Connecting to MQTT failed: {rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT EVENT] {msg.topic}: {payload}")

    if msg.topic == "minecraft/players":
        player_amount = payload


def check_mqtt(url: str, port: int, username: str, password: str) -> bool:
    try:
        client = mqtt.Client()

        client.username_pw_set(
            username=username,
            password=password,
        )

        client.connect(url, port, keepalive=60)
        client.disconnect()
    except Exception:
        return False
    else:
        return True
    

def setup_mqtt(cfg: Config) -> mqtt.Client|None:
    if not (cfg.mqtt_url and cfg.mqtt_port):
        return None
    
    client = mqtt.Client()

    client.username_pw_set(
        username=cfg.mqtt_username,
        password=cfg.mqtt_password,
    )

    client.connect(cfg.mqtt_url, cfg.mqtt_port, keepalive=60)
    client.on_connect = on_connect
    client.on_message = on_message

    client.loop_start()

    return client

def send_server_state(mc: MinecraftServer, mqtt_client: mqtt.Client|None):
    if not mqtt_client:
        return
    
    server_info = {
        "player_count": mc.player_count,
        "server_used": mc.server_used,
        "shutdown_mode": mc.shutdown_mode,
        "checks_remaining": mc.checks_remaining,
        "shutdown_requested": mc.shutdown_requested
    }

    json_payload = json.dumps(server_info)

    mqtt_client.publish("bedrock_manager/server/state", json_payload)