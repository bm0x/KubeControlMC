#!/bin/bash
# Wrapper para lanzar KubeControlMC en modo standalone

# Resolving absolute directory of this script to handle execution correctly
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# Try to active venv if it exists, otherwise assume global
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set PYTHONPATH to include local libs if they exist
export PYTHONPATH="$DIR/libs:$PYTHONPATH"

# Log output for debugging
LOG_FILE="/tmp/kcmc_launch.log"
echo "[$(date)] Launching KubeControlMC..." > "$LOG_FILE"
echo "DIR: $DIR" >> "$LOG_FILE"
echo "PYTHON: $(which python3)" >> "$LOG_FILE"

# Run the app
# Using gnome-terminal or xterm if not in a terminal is handled by the .desktop "Terminal=true" 
# This script just prepares environment.
python3 main.py "$@" >> "$LOG_FILE" 2>&1

# If it crashes, keep open for 5 seconds to read error
if [ $? -ne 0 ]; then
    echo "La aplicación se cerró con error. Esperando 10 segundos..."
    sleep 10
fi
