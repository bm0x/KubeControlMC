import requests
import os

class PluginManager:
    GEYSER_URL = "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot"
    FLOODGATE_URL = "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot"

    def __init__(self, plugins_dir=None):
        self.plugins_dir = plugins_dir or os.path.join("server_bin", "plugins")
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)

    def download_geyser(self) -> str:
        return self._download(self.GEYSER_URL, "Geyser-Spigot.jar")

    def download_floodgate(self) -> str:
        return self._download(self.FLOODGATE_URL, "floodgate-spigot.jar")

    def _download(self, url: str, filename: str) -> str:
        output_path = os.path.join(self.plugins_dir, filename)
        print(f"Downloading {filename}...")
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return output_path
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
