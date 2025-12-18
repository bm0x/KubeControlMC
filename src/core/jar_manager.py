import requests
import os

class JarManager:
    BASE_URL = "https://api.papermc.io/v2/projects"

    def __init__(self, download_dir="server_bin"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def get_versions(self, project: str) -> list[str]:
        """Get available versions for a project (paper, folia, velocity)"""
        try:
            resp = requests.get(f"{self.BASE_URL}/{project}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("versions", [])
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return []

    def get_latest_version(self, project: str) -> str:
        versions = self.get_versions(project)
        if versions:
            return versions[-1]
        return None

    def get_builds(self, project: str, version: str) -> list[int]:
        try:
            resp = requests.get(f"{self.BASE_URL}/{project}/versions/{version}")
            resp.raise_for_status()
            data = resp.json()
            return data.get("builds", [])
        except Exception as e:
            print(f"Error fetching builds: {e}")
            return []

    def get_latest_build(self, project: str, version: str) -> int:
        builds = self.get_builds(project, version)
        if builds:
            return builds[-1]
        return None

    def download_jar(self, project: str, version: str, build: int = None) -> str:
        """Downloads the JAR and returns the file path"""
        if build is None:
            build = self.get_latest_build(project, version)
        
        if build is None:
            raise ValueError("No build found")

        jar_name = f"{project}-{version}-{build}.jar"
        download_url = f"{self.BASE_URL}/{project}/versions/{version}/builds/{build}/downloads/{jar_name}"
        
        output_path = os.path.join(self.download_dir, jar_name)
        
        if os.path.exists(output_path):
            return output_path

        print(f"Downloading {jar_name}...")
        try:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192): 
                        f.write(chunk)
            return output_path
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
