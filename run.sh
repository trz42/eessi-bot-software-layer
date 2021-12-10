#!/bin/bash
# Usage: run with ./run.sh from directory where eessi-bot-software-layer.py is located
waitress-serve --port 3000 --call 'eessi_bot_software_layer:main'
