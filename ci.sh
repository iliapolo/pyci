#!/usr/bin/env bash

set -e

TRAVIS_BRANCH=${TRAVIS_BRANCH:-}

whoami=$(whoami)

function install_python_on_mac {
    curl -OL https://www.python.org/ftp/python/2.7.13/Python-2.7.13.tgz
    tar xzvf Python-2.7.13.tgz
    cd Python-2.7.13
    make
    ./configure --prefix=/Users/$(whoami)/ --enable-shared
    make install
    ls -lr /Users/$(whoami)/
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
