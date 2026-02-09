#!/bin/bash
set -e

# Update and upgrade system packages
sudo apt-get update
sudo apt-get upgrade -y

# Install required system packages for Minecraft updater, and also install java for the console bridge
sudo apt-get install -y python3 python3-pip python3-venv wget unzip tmux libcurl4 default-jdk