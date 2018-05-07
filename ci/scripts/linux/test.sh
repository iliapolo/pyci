#!/usr/bin/env bash

set -e

function create_wheel {
    $(pyci pack --path ${DIR}/../../../ wheel)
    echo $(ls -A | grep .whl)
}

function create_binary {
    $(pyci pack --path ${DIR}/../../../ binary)
    echo "$(pwd)/py-ci-$(uname -m)-$(uname -s)"
}

function cleanup {

    pip uninstall -y py-ci
    pip install -e ${DIR}/../../../.
    if [ ! -z ${wheel_path} ]; then
        rm -rf ${wheel_path}
    fi
    if [ ! -z ${binary_path} ]; then
        rm -rf ${binary_path}
    fi

}

trap cleanup EXIT

echo "[test] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ${DIR}/install.sh

echo "[test] Creating wheel"
wheel_path=$(create_wheel)

echo "[test] Creating binary"
binary_path=$(create_binary)

rm -rf .coverage

command="py.test -rs --cov-append -c ${DIR}/../../config/pytest.ini --cov-config=${DIR}/../../config/coverage.ini --cov=pyci ${DIR}/../../../pyci/tests"

echo "[test] Running source tests"
pip uninstall -y py-ci
pip install ${DIR}/../../../.
PYCI_TEST_PACKAGE=source ${command}

echo "[test] Running wheel tests"
pip uninstall -y py-ci
pip install ${wheel_path}
PYCI_TEST_PACKAGE=wheel PYCI_EXECUTABLE_PATH=pyci ${command}

echo "[test] Running binary tests"
pip uninstall -y py-ci
PYCI_TEST_PACKAGE=binary PYCI_EXECUTABLE_PATH=${binary_path} ${command}

echo "[test] Done!"