#!/usr/bin/env bash
# Validate skill metadata, references and component manifests. YAML parsing is mandatory.
set -euo pipefail
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY=(python3)
if ! python3 -c 'import yaml' 2>/dev/null; then
  command -v uv >/dev/null || { echo 'error: install PyYAML or uv to validate YAML' >&2; exit 1; }
  PY=(uv run -q --no-project --with pyyaml python)
fi
"${PY[@]}" "$KIT_DIR/scripts/check.py" "$KIT_DIR"
"${PY[@]}" "$KIT_DIR/scripts/check_skills.py" "$KIT_DIR" --kit "$KIT_DIR"
