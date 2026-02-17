import socket
import sys
import time
import questionary
import os
import yaml
from msm.config.load_config import Config
from msm.services.ha_mqtt import check_mqtt
import msm.core.minecraft_updater
from msm.services.ddns_update import test_DNS
import subprocess
import ipaddress
from pathlib import Path
import tempfile
import shutil
from rich import print
from rich.spinner import Spinner
from rich.live import Live
import logging

log = logging.getLogger("bsm")

def run_setupsh():
    # Make a temp folder
    tmpdir = tempfile.mkdtemp(prefix="bsm_")
    log.info(f"Moving setup.sh to: {tmpdir}")

    # Copy setup.sh file into a temp dir and give it permission to run
    source_path = os.path.join(sys._MEIPASS, "setup.sh") #type: ignore
    destination_path = os.path.join(tmpdir, "setup.sh")
    shutil.copy(source_path, destination_path)
    os.chmod(destination_path, 0o755)

    # Run the setup file
    log.info("Running setup.sh...")
    subprocess.run(["bash", destination_path], check=True)
    log.info("Setup finished.")

    # Clean up temp dir
    shutil.rmtree(tmpdir)
    log.info("Cleaned up temporary files.")


# Setup file for new users
def linux_check():
    if sys.platform != "linux":
        log.warning("You are not running Linux. This program will not work as expected.")
        input("Press enter to continue or ctrl+c to exit.")


def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_program_location():
    program_location = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

    if questionary.confirm(f"{program_location} \nAre you sure you want to use the above location for this program?").ask():
        print("Great, let's continue")
        return program_location
    else:
        questionary.press_any_key_to_continue("Please move this program to the location you want to use and run it again.").ask()
        sys.exit(0)


def password_confirm() -> str:
    dynu_password = questionary.password("What is your ddns password?").ask()
    dynu_password_confirm = questionary.password("Please confirm your ddns password.").ask()
    if dynu_password != dynu_password_confirm:
        print("Passwords do not match. Please try again.")
        return password_confirm()
    return dynu_password


def dynu_setup():
    clear_console()

    print("Let's configure dynu.")
    print("First you must go to https://www.dynu.com and create an account")
    questionary.press_any_key_to_continue("Press any key once you have created an account.").ask()

    print("\nNice, now let's get you a custom DNS address")
    if not questionary.confirm("You should be on the control panel, correct?").ask():
        print("No problem! Just go to https://www.dynu.com/en-US/ControlPanel or click on the settings icon.")

    print("\nThere you must click on \"DDNS Services\" and then \"Add\"")
    print("Follow the prompts to create a new DDNS service.")
    questionary.press_any_key_to_continue("Press any key once you have created a DDNS service.").ask()

    print("\nGreat! Now just add a password to your DDNS service.")
    print("Click on the link next to the red flag \"IP Update Password\"")
    print("And then enter a strong password into the \"New IP Update Password\" and confirm field.")
    questionary.press_any_key_to_continue("Press any key once you have added a password.").ask()

    print("\nNow that we got your DDNS service set up, let's get your password and domain.")

    while True:
        dynu_password = password_confirm()
        dynu_domain = questionary.text("What is your dynu domain?").ask()

        credentials_valid = test_DNS(dynu_domain, dynu_password)

        if credentials_valid:
            print("DNS credentials [green]valid[/green]")
            break
        else:
            print("DNS credentials [red]invalid[/red]")
            questionary.press_any_key_to_continue("Press any key to re-enter credentials")

    return dynu_password, dynu_domain


def mqtt_setup():
    while True:
        clear_console()

        print("MQTT will be used to view information about your Minecraft server")
        print("This requires an MQTT broker")

        mqtt_url = questionary.text(
            "What is you MQTT broker address? (do not include port)",
            validate=lambda val: not(val.startswith("http://") or val.startswith("https://")) or "Must NOT start with http:// or https://",  # type: ignore
        ).ask()

        mqtt_port = int(questionary.text(
            "What port is the broker on?",
            validate=lambda val: val.isdigit() or "Must be a number",
            default="1883"
        ).ask())

        mqtt_username = questionary.text("MQTT broker username:").ask()
        mqtt_password = questionary.password("MQTT broker password:").ask()

        credentials_valid = check_mqtt(mqtt_url, mqtt_port, mqtt_username, mqtt_password)

        if credentials_valid:
            print("Credentials are [green]valid[/green]")
            questionary.press_any_key_to_continue("\nPress any key to continue...").ask()
            break
        else:
            print("Credentials are [red]not valid[/red]")
            questionary.press_any_key_to_continue("Press any key to try again...").ask()

    clear_console()
    
    return mqtt_url, mqtt_port, mqtt_username, mqtt_password


def shutdown_mode_setup(drive_enabled: bool):
    clear_console()
    print("This code is made to shutdown your server after a set amount of time where no one is online")
    setup_auto_shutdown = questionary.confirm("Would you like to enable that?").ask()
    
    if setup_auto_shutdown:
        shutdown_time = int(questionary.text(
            "After how many minutes of inactivity should the server shutdown?",
            validate=lambda val: val.isdigit() or "Enter a number"
        ).ask())
        
        enable_valid_times = questionary.confirm("It is also possible to enable certain timeframes where the server will not startup.\nWould you like to enable that?").ask()

        if enable_valid_times:
            begin_valid_time = int(questionary.text(
                "Enter the start time in 24h format HH",
                validate=lambda val: val.isdigit() and 0 <= int(val.removeprefix("0") if len(val) > 1 else val) < 24 or "Enter a valid time in HH format"
            ).ask().removeprefix("0"))

            end_valid_time = int(questionary.text(
                "Enter the end time in 24h format (HH)",
                validate=lambda val: val.isdigit() and 0 <= int(val.removeprefix("0") if len(val) > 1 else val) < 24 or "Enter a valid time in HH format"
            ).ask().removeprefix("0"))
            
        begin_valid_time = end_valid_time = None
    else:
        shutdown_time = begin_valid_time = end_valid_time = None

    if drive_enabled:
        drive_backup_time = int(questionary.text(
            "At what time do you want the server to create drive backup?",
            validate=lambda val: val.isdigit() and 0 <= int(val.removeprefix("0")) < 24 or "Enter a valid time in HH format",
            default="3"
            ).ask().removeprefix("0"))
    else:
        drive_backup_time = None
    
    return shutdown_time, begin_valid_time, end_valid_time, drive_backup_time


def automatic_backups_setup(program_location: str) -> tuple[Path, Path | None, str | None, list[Path]]:
    clear_console()
    backup_options = questionary.checkbox(
        "There are different options for automatic backups, select the ones you want to use:",
        choices=["Local backup", "Back up to external drive", "Drive backup"],
        validate=lambda var: True if "Local backup" in var else "Local backup is required"
    ).ask()

    hdd_backup = "Back up to external drive" in backup_options
    drive_backup = "Drive backup" in backup_options

    print("Where do you want to save the local backups?")
    print("[italic underline red]DO NOT[/] select the main folder for this project, since backups will then contain every previous backup")
    local_path = questionary.path(
        "Location (Tab to autocomplete):",
        default=os.path.join(str(os.path.dirname(program_location)), "backups"),
        only_directories=True
    ).ask()

    if hdd_backup:
        hdd_path = questionary.path(
            "Where do you want to save the external drive backups?",
            default="/mnt",
            only_directories=True
        ).ask()
    else:
        hdd_path = None
    if drive_backup:
        print("You will need rclone for drive backups, so make sure you have it set up")
        drive_name = str(questionary.text(
            "What is the name of your rclone remote? (something like 'drive:')",
            validate=lambda val: val.endswith(":") or "Remote name must end with ':'"
        ).ask())
    else:
        drive_name = None

    directories: list[Path] = []
    while True:
        directory = questionary.path(
            "Enter a directory to back up (or leave blank to finish):",
            only_directories=True,
            default=program_location
        ).ask()
        if not directory:
            break
        directories.append(directory)
    return local_path, hdd_path, drive_name, directories


def get_minecraft_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


def add_alias(program_location: str):
    subprocess.run(['bash', '-c', f'echo \'alias bsm=\"{program_location}\"\' >> ~/.bashrc'])


def main():
    print("Hi, there!")
    print("This is a program for fully managing your bedrock server")

    # Display warning if program is not run on Linux
    linux_check()

    clear_console()

    config_data = {}

    program_location = get_program_location()

    config_data["path"] = {"base": program_location}

    clear_console()

    questionary.press_any_key_to_continue("I am going to ask you a few questions to set everything up.").ask()

    activated_services = questionary.checkbox("What services do you want to set up?\nAll of these are recommended", choices=["Home Assistant", "Dynu DNS", "Automatic shutdown", "Automatic backups"]).ask()

    home_assistant = "Home Assistant" in activated_services
    dynu = "Dynu DNS" in activated_services
    auto_shutdown = "Automatic shutdown" in activated_services
    auto_backup = "Automatic backups" in activated_services

    if home_assistant:
        mqtt_url, mqtt_port, mqtt_username, mqtt_password = mqtt_setup()
        config_data["mqtt"] = {"url": mqtt_url, "port": mqtt_port, "username": mqtt_username, "password": mqtt_password}

    if dynu:
        dynu_password, dynu_domain = dynu_setup()
        config_data["dynu"] = {"pass": dynu_password, "domain": dynu_domain}

    if auto_backup:
        local_path, hdd_path, drive_name, directories = automatic_backups_setup(program_location)
        config_data["backup"] = {k: v for k, v in [("local_path", local_path), ("hdd_path", hdd_path), ("drive_name", drive_name), ("directories", directories)] if v is not None}
    else:
        drive_name = None

    if auto_backup and drive_name:
        drive_enabled = True
    else:
        drive_enabled = False

    if auto_shutdown:
        shutdown_time, begin_valid_time, end_valid_time, drive_backup_time = shutdown_mode_setup(drive_enabled)
        config_data["timing"] = {k: v for k, v in [("shutdown", shutdown_time), ("begin_valid", begin_valid_time), ("end_valid", end_valid_time), ("drive_backup", drive_backup_time)] if v is not None}

    clear_console()

    # Automatically get the users ip and confirm if it's right
    mc_ip = get_minecraft_ip()

    def validate_local_ip(ip: str) -> bool:
        try:
            adress = ipaddress.ip_address(ip)
            return adress.is_private or adress.is_loopback or adress.is_link_local
        except Exception:
            return False

    if not questionary.confirm(f"Is this your local ip: {mc_ip}").ask():
        mc_ip = questionary.text("Please add your local ip:", default="192.168.1.1", validate=validate_local_ip).ask()

    # Ask for the minecraft port (type checking is not needed, because variable is always string)
    mc_port = int(questionary.text("Enter the Minecraft server port:", default="19132", validate=lambda x: x.isdigit()).ask())  # type: ignore

    # Save the minecraft data
    config_data["mc"] = {"ip": mc_ip, "port": mc_port}
    clear_console()

    config_location = Path(os.path.join(program_location, "config.yaml"))

    # Save the file and warn the user if it contains sensitive information
    with open(config_location, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, indent=2)
        print(f"[#9e9e9e]Config file saved to {config_location}")

    if dynu or home_assistant:
        print("[underline]Never[/] share this file with anyone as it will give access to all of the services you configured")

    # Load config we just saved
    cfg = Config.load()

    # Ask permission to download the repositories
    print("\nThis program can uses [italics]MCXboxBroadcast/Broadcaster[/] to make it possible for console players to join the server, this is optional\n")

    # Install and configure the console bridge
    if questionary.confirm("Do you want to download this program?").ask():
        print("\nFor the console bridge you will need a throw-away Microsoft account")
        print("This account will then host your Minecraft world, so players on console can join it\n")
        print("Also, like the Broadcaster project says:")
        print("\"You use this project at your own risk...we emulate some features of a client which may or may not be against TOS\"")
        print("So, be warned\n")

        if questionary.confirm("Do you want to continue?").ask():
            with Live(Spinner("dots9", text="Great, downloading now..."), refresh_per_second=10):
                msm.core.minecraft_updater.get_latest_version_console_bridge(cfg)

            msm.core.minecraft_updater.authenticate_console_bridge(cfg)
            print("Now we just need to configure the bot")
            print("Luckily it is just two questions\n")
            host_name = questionary.text("What should the host name (top text) be?").ask()
            world_name = questionary.text("What should the world name (bottom text) be?").ask()

            msm.core.minecraft_updater.configure_console_bridge(cfg, host_name, world_name)
        else:
            print("No problem")

        questionary.press_any_key_to_continue("Press any key to continue.").ask()

    clear_console()
    # Install the minecraft updater and run it to also install the minecraft server
    with Live(Spinner("dots4", text="Downloading Minecraft updater repository..."), refresh_per_second=10):
        msm.core.minecraft_updater.get_minecraft_updater(cfg)
    with Live(Spinner("dots8", text="Downloading Minecraft server..."), refresh_per_second=10):
        msm.core.minecraft_updater.update_minecraft_server(cfg)

    print("An alias makes it possible to run this program by just typing 'bsm' into the terminal")
    if not questionary.confirm("Have you added an alias for this program before").ask():
        if questionary.confirm("Would you like to add an alias").ask():
            program_path = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
            add_alias(program_path)

    # Give instructions for running the program
    print("To make this code work, first reboot this computer and then run 'bsm'")
    print("If you want the code to run on boot, follow the tutorial inside the README.md")


if __name__ == "__main__":
    main()
