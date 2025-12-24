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

# Run the app
# Using gnome-terminal or xterm if not in a terminal is handled by the .desktop "Terminal=true" 
# This script just prepares environment.
python3 main.py "$@"

# If it crashes, keep open for 5 seconds to read error
if [ $? -ne 0 ]; then
    echo "La aplicación se cerró con error. Esperando 10 segundos..."
    sleep 10
fi
