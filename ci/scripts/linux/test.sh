#!/usr/bin/env bash

set -e

echo "[test] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ${DIR}/install.sh

echo "[test] Running tests"
py.test -c ${DIR}/../../config/pytest.ini --cov-config=${DIR}/../../config/coverage.ini --cov=pyci ${DIR}/../../../pyci/tests

echo "[test] Done!"
