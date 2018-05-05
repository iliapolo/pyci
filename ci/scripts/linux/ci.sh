#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[ci] Starting script"

source ${DIR}/install.sh

#source ${DIR}/lint.sh

#source ${DIR}/test.sh

#source ${DIR}/codecov.sh

#source ${DIR}/release.sh

echo "[ci] Done!"

