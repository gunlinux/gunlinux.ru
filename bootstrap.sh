#!/bin/bash

cp config.example.sh config.sh
cp gunicorn.example.conf gunicorn.conf
mkdir -p pro/static/upload tmp pro/static/components

virtualenv venv
pip install -r requirements.txt 

npm install
gulp

bower install
python pro/static/components/highlight/tools/build.py

