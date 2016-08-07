#!/bin/bash -xe
if [ ! -d .venv ]; then
                 virtualenv .venv
fi
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install matplotlib
.venv/bin/python $WORKSPACE/generate_summary_report/generate_summary_report.py
