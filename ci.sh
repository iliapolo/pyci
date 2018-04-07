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
py.test --cov-report term-missing --cov=fileconfig pyrelease/tests

if [ -z ${TRAVIS_PULL_REQUEST_BRANCH} ] && [ "dev" = ${TRAVIS_BRANCH} ]; then
    echo "Running release"
    pip install https://github.com/iliapolo/pyrelease/archive/master.zip
    pyrelease release --repo iliapolo/pyrelease --branch dev
fi

echo "Done!"