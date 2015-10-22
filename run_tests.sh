#!/bin/bash
source venv/bin/activate
source config.sh
./manage.py test 
[ $? -ne 0 ] && exit 1
prospector -A -F .
[ $? -ne 0 ] && exit 1
exit 0