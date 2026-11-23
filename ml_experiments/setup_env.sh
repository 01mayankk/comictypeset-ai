#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== ComicTypeset AI: Initializing ML Training Environment ==="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in ml_experiments/.venv..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip, setuptools, and wheel..."
pip install --upgrade pip setuptools wheel

echo "Installing training dependencies from requirements-train.txt..."
pip install -r requirements-train.txt

echo "Registering Jupyter kernel 'comictypeset-ml'..."
python -m ipykernel install --user --name=comictypeset-ml --display-name="Python (ComicTypeset ML)"

echo "=== ML Environment Setup Complete ==="
echo "To activate: source ml_experiments/.venv/bin/activate"
