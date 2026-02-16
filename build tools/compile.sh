# Update all programs
sudo apt-get update -y

sudo apt-get upgrade -y

# Clone repo
git clone -b dev --single-branch https://github.com/Djayden-R/Bedrock-server-manager.git

# Make a virtual environment
sudo apt install python3.12-venv -y

python3.12 -m venv venv

source ./venv/bin/activate

# Install dependencies
pip install -r Bedrock-server-manager/requirements.txt

pip install pyinstaller

cd Bedrock-server-manager

# Make the executable
pyinstaller --onefile --add-data "setup.sh:." main.py

# Move to home folder
cp dist/main ~/bsm

# Clean up files
cd ~

deactivate

rm -rf Bedrock-server-manager venv
