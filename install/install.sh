#!/usr/bin/env bash
# install/install.sh — instalador unificado para Linux/macOS
# Uso: ./install/install.sh [opcoes adicionais encaminhadas ao python install/install.py]

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 nao encontrado. Instale Python 3.10+ e tente novamente." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

python3 "install/install.py" --mode venv --venv-path .venv "$@"
