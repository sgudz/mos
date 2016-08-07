#!/bin/bash -xe
virtualenv .venv
.venv/bin/pip install -r requirements/test.txt
.venv/bin/python manage.py test