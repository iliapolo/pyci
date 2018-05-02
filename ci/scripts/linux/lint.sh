#!/usr/bin/env bash

set -e

echo "[lint] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

${DIR}/install.sh

echo "[lint] Running code analysis"
pylint --rcfile ${DIR}/../../config/pylint.ini pyci

echo "[lint] Done!"
