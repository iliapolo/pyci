#!/usr/bin/env bash

set -e

echo "[codecov] Starting script"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "[codecov] Uploading code coverage..."
codecov

echo "[codecov] Done!"
