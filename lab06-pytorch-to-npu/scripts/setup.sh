#!/usr/bin/env bash
set -euo pipefail
lab_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
lab_python=${LAB6_SYSTEM_PYTHON:-/usr/bin/python3}
if command -v uv >/dev/null 2>&1; then
  if [[ ! -x "$lab_dir/build/venv/bin/python" ]]; then
    uv venv --python "$lab_python" "$lab_dir/build/venv"
  fi
  uv pip install --python "$lab_dir/build/venv/bin/python" -r "$lab_dir/requirements.txt"
else
  "$lab_python" -m venv "$lab_dir/build/venv"
  "$lab_dir/build/venv/bin/python" -m pip install -r "$lab_dir/requirements.txt"
fi
"$lab_dir/build/venv/bin/python" -c 'import torch; print("PyTorch:", torch.__version__)'
