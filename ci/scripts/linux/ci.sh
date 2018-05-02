#!/usr/bin/env bash

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[ci] Starting script"

${DIR}/install.sh

${DIR}/lint.sh

${DIR}/test.sh

${DIR}/release.sh

echo "[ci] Done!"

