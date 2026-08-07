#!/bin/bash
# Wrapper para lanzar KubeControlMC en modo standalone

# Resolving absolute directory of this script to handle execution correctly
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Prefer the project venv if present, otherwise fall back to system python3
PY="python3"
if [ -x "$DIR/.venv/bin/python" ]; then
    PY="$DIR/.venv/bin/python"
    export VIRTUAL_ENV="$DIR/.venv"
    export PATH="$DIR/.venv/bin:$PATH"
fi

# Set PYTHONPATH to include local libs if they exist
export PYTHONPATH="$DIR/libs:$PYTHONPATH"

# Log output for debugging
LOG_FILE="/tmp/kcmc_launch.log"
echo "[$(date)] Launching KubeControlMC..." > "$LOG_FILE"
echo "DIR: $DIR" >> "$LOG_FILE"
echo "PY: $PY" >> "$LOG_FILE"
echo "PYTHON_VERSION: $("$PY" --version 2>&1)" >> "$LOG_FILE"

# Run the app
"$PY" main.py "$@" >> "$LOG_FILE" 2>&1
LAUNCH_EC=$?

# If it crashes, show the error and keep the window open so the user can read it
if [ $LAUNCH_EC -ne 0 ]; then
    echo ""
    echo "La aplicación se cerró con error (código: $LAUNCH_EC)."
    echo "------------------------------------------------"
    echo "Últimas líneas del log:"
    tail -n 40 "$LOG_FILE"
    echo "------------------------------------------------"
    echo "Si faltan dependencias, ejecuta:"
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    echo ""
    echo "Esperando 10 segundos..."
    sleep 10
fi

exit $LAUNCH_EC