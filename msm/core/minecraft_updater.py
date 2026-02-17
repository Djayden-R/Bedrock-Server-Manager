from git import Repo
import requests
import os
import subprocess
from msm.config.load_config import Config
from shutil import rmtree
import questionary
from pathlib import Path
from typing import Optional
import yaml
import logging

log = logging.getLogger("bsm")

console_bridge_repo = "MCXboxBroadcast/Broadcaster"
minecraft_updater_repo = "ghwns9652/Minecraft-Bedrock-Server-Updater"


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')


def download_file(url: str, file_path: Path):
    r = requests.get(url, stream=True)

    with open(file_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def get_latest_release(repository_name: str, download_location: Path, file_name: Optional[str] = None):
    url = f"https://api.github.com/repos/{repository_name}/releases/latest"

    response = requests.get(url)
    response.raise_for_status()
    release = response.json()

    for asset in release["assets"]:

        if asset["name"] == file_name:
            # Location for where file will be saved
            file_path = Path(os.path.join(download_location, asset['name']))

            if os.path.exists(file_path):
                os.remove(file_path)

            download_file(asset["browser_download_url"], file_path)

            download_success = os.path.exists(file_path) and os.path.getsize(file_path) > 0

            if download_success:
                log.info("File is successfully downloaded")
            else:
                log.error("Problem during download")


def get_latest_version_console_bridge(cfg: Config):
    if cfg.path_base:
        console_bridge_folder = Path(os.path.join(cfg.path_base, "console_bridge"))
        if not console_bridge_folder.exists():
            os.mkdir(console_bridge_folder)
        console_bridge_file = Path(os.path.join(console_bridge_folder, "MCXboxBroadcastStandalone.jar"))
        if os.path.exists(console_bridge_file):
            os.remove(console_bridge_file)

        get_latest_release(console_bridge_repo, console_bridge_folder, file_name="MCXboxBroadcastStandalone.jar")
    else:
        raise ValueError("Cannot get console bridge, since base path is not defined")


def authenticate_console_bridge(cfg: Config):
    if cfg.path_base:
        console_bridge_path = os.path.join(cfg.path_base, "console_bridge", "MCXboxBroadcastStandalone.jar")
        if os.path.exists(console_bridge_path):
            console_bridge_dir = os.path.dirname(console_bridge_path)
            process = subprocess.Popen(["java", "-jar", console_bridge_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, cwd=console_bridge_dir)
            if process.stdout:
                try:
                    for line in process.stdout:
                        if "enter the code" in line:
                            cleaned_auth_line = line.split("enter the code ")[1]
                            auth_code = cleaned_auth_line.split()[0]
                            print("Now you need to go to https://microsoft.com/link")
                            print(f"Then enter this code: {auth_code}")

                        elif "Successfully authenticated as" in line:
                            print("Great! The console bridge is now authenticated.")
                            break

                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:

                        process.kill()
                        process.wait()
                    if process.stdout:
                        process.stdout.close()
            else:
                log.error("There is no output from the console bridge")
        else:
            log.error("Console bridge is not found")
            log.error(f"Checked this path: {console_bridge_path}")
    else:
        raise ValueError("Cannot authenticate console bridge, since base path is not defined")


def configure_console_bridge(cfg: Config, host_name: str, world_name: str):
    config_path = os.path.join(cfg.path_base, "console_bridge", "config.yml")  # type: ignore

    with open(config_path, 'r', encoding='utf-8') as file:  # type: ignore
        data = yaml.safe_load(file)

    session_info = data['session']['session-info']

    session_info['host-name'] = host_name
    session_info['world-name'] = world_name
    session_info['ip'] = cfg.mc_ip
    session_info['port'] = cfg.mc_port

    data['session']['session-info'] = session_info

    with open(config_path, 'w', encoding='utf-8') as file:  # type: ignore
        yaml.safe_dump(data, file, default_flow_style=False, allow_unicode=True)


def get_minecraft_updater(cfg: Config):
    if cfg.path_base:
        mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
        if os.path.exists(mc_updater_path):
            if len(os.listdir(mc_updater_path)) > 1:
                print(os.listdir(mc_updater_path))
                print("WARNING - The Minecraft updater is already downloaded")
                print("Continuing could mean that your Minecraft world will be overwritten")
                if questionary.text("Confirm by writing 'DELETE':", ).ask() == "DELETE":
                    rmtree(mc_updater_path)
                else:
                    print("Didn't update minecraft_updater")
            else:
                rmtree(mc_updater_path)

        Repo.clone_from(f"https://github.com/{minecraft_updater_repo}.git", mc_updater_path, )
    else:
        print("Cannot get Minecraft updater, since download location is not defined")


def update_minecraft_server(cfg: Config) -> bool:
    if cfg.path_base:
        mc_updater_path = os.path.join(cfg.path_base, "minecraft_updater")
        minecraft_updater_path = os.path.expanduser(f"{mc_updater_path}/updater/mcserver_autoupdater.py")
        minecraft_updater_output = subprocess.run(['python3', minecraft_updater_path], capture_output=True, text=True)
        if "minecraft server is already newest version" in minecraft_updater_output.stdout:
            print("Nothing to update, starting server")
            return False
        elif "minecraft server is updated" in minecraft_updater_output.stdout:
            print("Minecraft server successfully updated and started")
            return True
        else:
            raise ValueError(f"Unknown state: {minecraft_updater_output.stdout} \nerror: {minecraft_updater_output.stderr}")
    else:
        raise ValueError("Cannot update Minecraft server, since base path is not defined")


def main(cfg: Config):
    get_latest_version_console_bridge(cfg)
    update_minecraft_server(cfg)
