import sys
import os

# Add local libs directory to path for portability/restricted envs
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))

import asyncio
from src.tui.app import MCSMApp

def main():
    app = MCSMApp()
    app.run()

if __name__ == "__main__":
    main()
