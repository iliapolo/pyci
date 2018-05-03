#!/usr/bin/env bash

set -e

echo "[release] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

source ${DIR}/install.sh

echo "[release] Running release"
pyci --debug release --pypi-test

echo "[release] Done!"
