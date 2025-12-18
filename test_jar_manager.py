import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libs"))
from src.core.jar_manager import JarManager

try:
    jm = JarManager()
    print("Checking Paper versions...")
    versions = jm.get_versions("paper")
    print(f"Versions found: {len(versions)}")
    latest = jm.get_latest_version("paper")
    print(f"Latest version: {latest}")
    
    if latest:
        print(f"Checking builds for {latest}...")
        build = jm.get_latest_build("paper", latest)
        print(f"Latest build: {build}")
        print("JarManager verification passed!")
    else:
        print("No versions found!")
except Exception as e:
    print(f"Error: {e}")
