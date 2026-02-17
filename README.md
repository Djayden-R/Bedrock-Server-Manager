# Bedrock Server Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Ubuntu-orange)](https://ubuntu.com/)
[![GitHub last commit](https://img.shields.io/github/last-commit/Djayden-R/Bedrock-server-manager)](https://github.com/Djayden-R/Bedrock-server-manager)

An automated management tool for a bedrock server. It will handle updating, shutting down, making backups, handling a dynamic dns, and even connecting players on a console to the server.

## How it Works

After setup, the program determines which mode to run based on configuration and timing:

- **NORMAL** - Standard operating mode that updates the DNS and then updates the server if needed and lastly starts the server with automatic shutdown after inactivity
- **DRIVE_BACKUP** - Initiates backup to online drive using the latest symlink via Rclone  
- **INVALID** - Triggered when server starts outside configured valid hours
- **CONFIGURATION** - First-time setup mode when no config.yaml exists

## Prerequisites

> **Note:** This program has been tested exclusively on Ubuntu. Ubuntu is the recommended platform. For drive backup functionality, Rclone must be configured separately (tutorial below).

## Installation

### Initial Setup

Firstly, place the script in the desired location, then just run the following commands in that folder

```bash
chmod +x bedrock-manager
./bedrock-manager
```

The setup script will guide you through the configuration process.

### Running the Server

```bash
./{location}/bedrock-manager
```

or after adding the alias

```bash
bsm
```

### Turning off auto shutdown

If you need to work on the server without being disturbed by the automatic shutdown you will need to create the no shutdown flag, like this:

 ```bash
cd Bedrock-server-manager
touch no_shutdown.flag
```

To make it shutdown again, you'll need to remove the file again:

```bash
cd Bedrock-server-manager
rm no_shutdown.flag
```

## Features

- **Home Assistant Integration** - Manage auto shutdown via a Home Assistant switch
- **Backup Management** - Create multiple backups, two to a storage device and one to a cloud service using Rclone  
- **Intelligent Scheduling** - Cloud backups can be scheduled in the night to make shutdown faster
- **Dynamic DNS** - DynuDNS integration to make managing a url easy

## Extra tutorials

To automatically start this program on boot, follow [**this tutorial**](https://www.youtube.com/watch?v=Un9ASbGCN0U).

To configure Rclone follow one of these tutorials:

- [**for Google Drive**](https://www.youtube.com/watch?v=FQuMFrazK1Y)
- [**for Onedrive**](https://www.youtube.com/watch?v=dTFt2DkOde4)

## Planned features

- Replacing Home Assistant API for MQTT
- Adding (almost) all variables to MQTT
- Parsing tmux to make a chat sensor

## Acknowledgments

This project integrates the following open-source tools:

- **[Broadcaster](https://github.com/MCXboxBroadcast/Broadcaster)** (GPL-3.0 License) - Console bridge functionality
- **[Minecraft-Bedrock-Server-Updater](https://github.com/ghwns9652/Minecraft-Bedrock-Server-Updater)** (MIT License) - Server update automation

## Development Notes

AI assistance was utilized for specific components: `load_config.py` and formatting of the `README.md`.
