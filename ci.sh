#!/usr/bin/env bash

set -e

env

echo "Installing test requirements"
pip install -r test-requirements.txt

echo "Installing dependencies"
pip install -e .

echo "Running code analysis"
pylint --rcfile .pylint.ini pyrelease

echo "Running tests"
py.test --cov-report term-missing --cov=pyrelease pyrelease/tests

echo "Running release"
pyrelease release --repo iliapolo/pyrelease --branch dev

echo "Done!"