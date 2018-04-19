#!/usr/bin/env bash

set -e

TRAVIS_BRANCH=${TRAVIS_BRANCH:-}
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


function install_python_on_mac {

    echo "Installing pyenv..."
    HOMEBREW_NO_AUTO_UPDATE=1 brew install pyenv
    echo "Successfully installed pyenv"

    echo "Initializing pyenv..."
    eval "$(pyenv init -)"
    echo "Successfully initialized pyenv..."

    echo "Installing python 2.7.14 with pyenv..."
    # --enable-shared is needed for pyinstaller.
    env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 2.7.14
    pyenv global 2.7.14
    echo "Successfully installed python 2.7.14 with pyenv..."

    echo "Checking where python is"
    which python

    echo "Checking python version"
    $(which python) --version

    echo "Checking where pip is"
    which pip

    echo "Finished installing and configuring python"
}


os=$(uname -s)
if [ ${os} == "Darwin" ] && [ ! -z ${TRAVIS_BRANCH} ]; then
    # only install on travis since it does not have python
    # installed for mac builds
    install_python_on_mac
fi

echo "Starting ci script"
program=pyci

echo "Installing test requirements"
pip install -r ${DIR}/test-requirements.txt

echo "Installing dependencies"
pip install -e ${DIR}/.

echo "Running code analysis"
pylint --rcfile ${DIR}/.pylint.ini ${program}

echo "Running tests"
py.test -s --cov-report term-missing --cov=${DIR}/${program} ${DIR}/${program}/tests

echo "Running release"
${program} --debug release --pypi-test

echo "Done!"
