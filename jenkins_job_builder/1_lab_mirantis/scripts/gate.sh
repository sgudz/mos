#!/bin/bash -xe
echo "============================================================"
echo "                      Start PEP8"
echo "============================================================"
tox -epep8
echo "============================================================"
echo "                      Start unitests"
echo "============================================================"
tox -epy27 || true
.tox/py27/bin/python .tox/py27/bin/testr last --subunit | .tox/py27/bin/subunit2junitxml > tests.xml