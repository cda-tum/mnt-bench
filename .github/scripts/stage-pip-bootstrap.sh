#!/usr/bin/env bash
set -euo pipefail

# setup-python's cold-cache installer upgrades pip before our normal bootstrap.
url="${PIP_BOOTSTRAP_URL%%#*}"
wheel="$RUNNER_TEMP/pip-bootstrap/${url##*/}"
mkdir -p "${wheel%/*}"
curl --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
  --output "$wheel" "$url"
echo "${PIP_BOOTSTRAP_URL##*#sha256=}  $wheel" | sha256sum --check --strict
