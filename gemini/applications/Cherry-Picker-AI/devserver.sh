#!/bin/sh
source .venv/bin/activate
python -m flask --app main run -p $PORT --debug