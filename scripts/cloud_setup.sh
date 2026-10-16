#!/usr/bin/env bash
set -euo pipefail
cd /workspace/fintechathon-2026
export UV_CACHE_DIR=/workspace/.cache/uv
uv sync --frozen
npm --cache /workspace/.cache/npm ci
.venv/bin/python scripts/local_prepare.py
.venv/bin/python -m alembic upgrade head
.venv/bin/python scripts/install_ocr.py
.venv/bin/python scripts/validate_contract.py
.venv/bin/python scripts/check_generated.py
npm run build
