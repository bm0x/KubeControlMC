import requests
import os

class JarManager:
    # PaperMC sunset the v2 API; the downloads service now lives here:
    # https://docs.papermc.io/misc/downloads-service/
    BASE_URL = "https://fill.papermc.io/v3/projects"
    USER_AGENT = "KubeControlMC/1.0 (https://github.com/bm0x/KubeControlMC)"

    def __init__(self, download_dir="server_bin"):
        self.download_dir = download_dir
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

    def _get_json(self, path: str):
        resp = requests.get(
            f"{self.BASE_URL}{path}",
            headers={"Accept": "application/json", "User-Agent": self.USER_AGENT},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()

    def get_current_jar(self) -> str:
        """Find the first/latest JAR file in the download directory."""
        if not os.path.exists(self.download_dir):
            return None
        jars = [f for f in os.listdir(self.download_dir) if f.endswith('.jar')]
        if jars:
            # Return most recently modified JAR
            jars.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
            return os.path.join(self.download_dir, jars[0])
        return None

    def is_server_jar(self, filename: str) -> bool:
        """
        Determine if a JAR file is a server JAR (not a plugin).
        
        Args:
            filename: Name of the JAR file
            
        Returns:
            True if it's a server JAR (paper, folia, etc.), False otherwise
        """
        server_patterns = ['paper-', 'folia-', 'velocity-', 'spigot-', 'craftbukkit-',
                          'purpur-', 'pufferfish-', 'airplane-', 'tuinity-']
        lower_name = filename.lower()
        return any(lower_name.startswith(p) for p in server_patterns)

    @staticmethod
    def _version_sort_key(version: str):
        try:
            return [int(p) for p in version.split(".")]
        except (ValueError, AttributeError):
            return [0]

    def get_versions(self, project: str) -> list[str]:
        """Get stable release versions for a project (paper, folia, velocity)."""
        try:
            data = self._get_json(f"/{project}")
            raw = [v for group in data.get("versions", {}).values() for v in group]
            # Keep only stable releases (drop rc/pre/alpha/beta/dev)
            stable = {
                v for v in raw
                if not any(token in v for token in ("-rc", "-pre", "-alpha", "-beta", "-dev"))
            }
            versions = sorted(stable, key=self._version_sort_key)
            return versions
        except Exception as e:
            print(f"Error fetching versions: {e}")
            return []

    def get_latest_version(self, project: str) -> str:
        versions = self.get_versions(project)
        if versions:
            return versions[-1]
        return None

    def get_builds(self, project: str, version: str) -> list[dict]:
        try:
            data = self._get_json(f"/{project}/versions/{version}/builds")
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            print(f"Error fetching builds: {e}")
            return []

    def get_latest_build(self, project: str, version: str) -> int:
        builds = self.get_builds(project, version)
        if not builds:
            return None
        stable = [b for b in builds if b.get("channel") == "STABLE"]
        pool = stable or builds
        pool.sort(key=lambda b: b.get("id", 0))
        return pool[-1].get("id")

    def _get_download_url(self, project: str, version: str, build: int) -> str:
        """Resolve the direct download URL for a build from the Fill API."""
        url = None
        for b in self.get_builds(project, version):
            if b.get("id") == build:
                dl = b.get("downloads", {}).get("server:default") or b.get("downloads", {}).get("server") or {}
                url = dl.get("url")
                break
        if not url:
            # Fallback: ask for the latest build of that version
            try:
                data = self._get_json(f"/{project}/versions/{version}/builds/latest")
                dl = data.get("downloads", {}).get("server:default") or data.get("downloads", {}).get("server") or {}
                url = dl.get("url")
            except Exception:
                pass
        return url

    def download_jar(self, project: str, version: str, build: int = None) -> str:
        """Downloads the JAR and returns the file path"""
        if build is None:
            build = self.get_latest_build(project, version)

        if build is None:
            raise ValueError("No build found")

        jar_name = f"{project}-{version}-{build}.jar"
        output_path = os.path.join(self.download_dir, jar_name)

        if os.path.exists(output_path):
            return output_path

        download_url = self._get_download_url(project, version, build)
        if not download_url:
            raise ValueError(f"No download URL found for {project} {version} build {build}")

        print(f"Downloading {jar_name}...")
        try:
            with requests.get(download_url, stream=True, headers={"User-Agent": self.USER_AGENT}) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return output_path
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e