#!/usr/bin/env bash
# install.sh — instalador unificado para ambientes Linux/macOS (GitHub Codespaces)
# Uso: ./install.sh [opcoes adicionais encaminhadas ao python tools/install.py]

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 nao encontrado. Instale Python 3.8+ e tente novamente." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python3 tools/install.py --mode venv --venv-path .venv "$@"
