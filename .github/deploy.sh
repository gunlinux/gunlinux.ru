#!/bin/bash

REPO_DIR="/home/loki/www/gunlinux.ru"
BRANCH="master"

# Navigate to the repository directory
cd $REPO_DIR || exit

# Fetch and reset changes from the remote repository
git fetch --all
git reset --hard origin/$BRANCH

# Optionally run build or install commands here if needed
# e.g., npm install, yarn install for Node.js projects
uv sync

# Restart services using sudo
sudo systemctl restart gunlinux.ru

echo "Deployment completed successfully."
