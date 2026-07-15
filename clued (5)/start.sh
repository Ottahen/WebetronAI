#!/usr/bin/env bash
set -e
pip install -r requirements.txt --quiet
python3 api.py
