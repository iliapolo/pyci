#!/usr/bin/env bash

set -e

echo "[lint] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

${DIR}/install.sh

echo "[install] Initializing pyenv..."
eval "$(pyenv init -)"
echo "[install] Successfully initialized pyenv..."

echo "[install] Installing python 2.7.14 with pyenv..."
# --enable-shared is needed for pyinstaller.
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install -s 2.7.14
pyenv global 2.7.14
echo "[install] Successfully installed python 2.7.14 with pyenv..."

echo "[lint] Running code analysis"
pylint --rcfile ${DIR}/../../config/pylint.ini pyci

echo "[lint] Done!"
