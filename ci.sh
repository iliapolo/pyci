#!/usr/bin/env bash

set -e

TRAVIS_BRANCH=${TRAVIS_BRANCH:-}


function install_python_on_mac {
    brew install python@2
    export PATH="/usr/local/opt/python@2/libexec/bin:$PATH"
}


os=$(uname -s)
if [ ${os} == "Darwin" ] && [ ! -z ${TRAVIS_BRANCH} ]; then
    # only install on travis since it does not have python
    # installed for mac builds
    install_python_on_mac
fi

program=pyci

echo "Installing test requirements"
pip install -r test-requirements.txt

echo "Installing dependencies"
pip install -e .

echo "Running code analysis"
pylint --rcfile .pylint.ini ${program}

echo "Running tests"
py.test --cov-report term-missing --cov=${program} ${program}/tests

echo "Running release"
${program} --repo iliapolo/${program} releaser release --sha release --binary-entrypoint pyci.spec

echo "Done!"
