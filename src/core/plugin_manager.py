import requests
import os
import json
from typing import Optional, Dict, Tuple

class PluginManager:
    # APIs
    GEYSER_API = "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest"
    FLOODGATE_API = "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest"
    KUBECONTROL_API = "https://api.github.com/repos/bm0x/KubeControlPlugin/releases/latest"
    
    # Download URLs
    GEYSER_DOWNLOAD = "https://download.geysermc.org/v2/projects/geyser/versions/latest/builds/latest/downloads/spigot"
    FLOODGATE_DOWNLOAD = "https://download.geysermc.org/v2/projects/floodgate/versions/latest/builds/latest/downloads/spigot"

    def __init__(self, plugins_dir=None):
        self.plugins_dir = plugins_dir or os.path.join("server_bin", "plugins")
        self.metadata_file = os.path.join(self.plugins_dir, ".plugin_versions.json")
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
    
    # ==================== Metadata Management ====================
    
    def _load_metadata(self) -> Dict:
        """Load installed plugins metadata."""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_metadata(self, data: Dict):
        """Save plugins metadata."""
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _update_plugin_metadata(self, plugin_name: str, version: str, build: int = None, filename: str = None):
        """Update metadata for a specific plugin."""
        metadata = self._load_metadata()
        metadata[plugin_name] = {
            "version": version,
            "build": build,
            "filename": filename
        }
        self._save_metadata(metadata)
    
    # ==================== Version Checking ====================
    
    def get_remote_geyser_info(self) -> Optional[Dict]:
        """Get latest Geyser version info from API."""
        try:
            resp = requests.get(self.GEYSER_API, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "version": data.get("version"),
                "build": data.get("build"),
                "sha256": data.get("downloads", {}).get("spigot", {}).get("sha256")
            }
        except:
            return None
    
    def get_remote_floodgate_info(self) -> Optional[Dict]:
        """Get latest Floodgate version info from API."""
        try:
            resp = requests.get(self.FLOODGATE_API, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                "version": data.get("version"),
                "build": data.get("build"),
                "sha256": data.get("downloads", {}).get("spigot", {}).get("sha256")
            }
        except:
            return None
    
    def get_remote_kubecontrol_info(self) -> Optional[Dict]:
        """Get latest KubeControlPlugin version info from GitHub."""
        try:
            resp = requests.get(self.KUBECONTROL_API, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            jar_asset = next((a for a in data.get("assets", []) if a["name"].endswith(".jar")), None)
            return {
                "version": data.get("tag_name"),
                "download_url": jar_asset["browser_download_url"] if jar_asset else None,
                "filename": jar_asset["name"] if jar_asset else None
            }
        except:
            return None
    
    def check_for_updates(self) -> Dict[str, Tuple[bool, str, str]]:
        """
        Check all plugins for updates.
        Returns: {plugin_name: (has_update, current_version, latest_version)}
        """
        results = {}
        metadata = self._load_metadata()
        
        # Check Geyser
        geyser_remote = self.get_remote_geyser_info()
        geyser_local = metadata.get("geyser", {})
        if geyser_remote:
            has_update = geyser_remote["build"] != geyser_local.get("build")
            results["geyser"] = (
                has_update,
                f"{geyser_local.get('version', 'N/A')} (build {geyser_local.get('build', '?')})",
                f"{geyser_remote['version']} (build {geyser_remote['build']})"
            )
        
        # Check Floodgate
        floodgate_remote = self.get_remote_floodgate_info()
        floodgate_local = metadata.get("floodgate", {})
        if floodgate_remote:
            has_update = floodgate_remote["build"] != floodgate_local.get("build")
            results["floodgate"] = (
                has_update,
                f"{floodgate_local.get('version', 'N/A')} (build {floodgate_local.get('build', '?')})",
                f"{floodgate_remote['version']} (build {floodgate_remote['build']})"
            )
        
        # Check KubeControlPlugin
        kube_remote = self.get_remote_kubecontrol_info()
        kube_local = metadata.get("kubecontrol", {})
        if kube_remote:
            has_update = kube_remote["version"] != kube_local.get("version")
            results["kubecontrol"] = (
                has_update,
                kube_local.get("version", "No instalado"),
                kube_remote["version"] if kube_remote["version"] else "No disponible"
            )
        
        return results
    
    # ==================== Download & Update ====================
    
    def _remove_old_plugin(self, plugin_name: str):
        """Remove old plugin JAR based on metadata."""
        metadata = self._load_metadata()
        plugin_data = metadata.get(plugin_name, {})
        old_filename = plugin_data.get("filename")
        
        if old_filename:
            old_path = os.path.join(self.plugins_dir, old_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
                print(f"Eliminado plugin antiguo: {old_filename}")
        
        # Also try to find by pattern (fallback)
        patterns = {
            "geyser": "Geyser",
            "floodgate": "floodgate",
            "kubecontrol": "KubeControlPlugin"
        }
        pattern = patterns.get(plugin_name, "")
        if pattern and os.path.exists(self.plugins_dir):
            for f in os.listdir(self.plugins_dir):
                if f.startswith(pattern) and f.endswith(".jar"):
                    os.remove(os.path.join(self.plugins_dir, f))
                    print(f"Eliminado: {f}")
    
    def download_geyser(self, force_update: bool = False) -> str:
        """Download or update Geyser plugin."""
        remote_info = self.get_remote_geyser_info()
        if not remote_info:
            raise Exception("No se pudo obtener información de Geyser")
        
        metadata = self._load_metadata()
        local_info = metadata.get("geyser", {})
        
        # Check if update needed
        if not force_update and local_info.get("build") == remote_info["build"]:
            existing = os.path.join(self.plugins_dir, local_info.get("filename", ""))
            if os.path.exists(existing):
                return existing  # Already up to date
        
        # Remove old version
        self._remove_old_plugin("geyser")
        
        # Download new version
        filename = f"Geyser-Spigot-{remote_info['version']}-b{remote_info['build']}.jar"
        path = self._download(self.GEYSER_DOWNLOAD, filename)
        
        # Update metadata
        self._update_plugin_metadata("geyser", remote_info["version"], remote_info["build"], filename)
        
        return path
    
    def download_floodgate(self, force_update: bool = False) -> str:
        """Download or update Floodgate plugin."""
        remote_info = self.get_remote_floodgate_info()
        if not remote_info:
            raise Exception("No se pudo obtener información de Floodgate")
        
        metadata = self._load_metadata()
        local_info = metadata.get("floodgate", {})
        
        if not force_update and local_info.get("build") == remote_info["build"]:
            existing = os.path.join(self.plugins_dir, local_info.get("filename", ""))
            if os.path.exists(existing):
                return existing
        
        self._remove_old_plugin("floodgate")
        
        filename = f"floodgate-spigot-{remote_info['version']}-b{remote_info['build']}.jar"
        path = self._download(self.FLOODGATE_DOWNLOAD, filename)
        
        self._update_plugin_metadata("floodgate", remote_info["version"], remote_info["build"], filename)
        
        return path
    
    def download_kubecontrol_plugin(self, force_update: bool = False) -> str:
        """Download or update KubeControlPlugin from GitHub Releases."""
        remote_info = self.get_remote_kubecontrol_info()
        if not remote_info or not remote_info.get("download_url"):
            raise Exception("No se encontró un release de KubeControlPlugin. Crea un tag en GitHub primero.")
        
        metadata = self._load_metadata()
        local_info = metadata.get("kubecontrol", {})
        
        if not force_update and local_info.get("version") == remote_info["version"]:
            existing = os.path.join(self.plugins_dir, local_info.get("filename", ""))
            if os.path.exists(existing):
                return existing
        
        self._remove_old_plugin("kubecontrol")
        
        filename = remote_info["filename"]
        path = self._download(remote_info["download_url"], filename)
        
        self._update_plugin_metadata("kubecontrol", remote_info["version"], filename=filename)
        
        return path
    
    def update_all_plugins(self) -> Dict[str, str]:
        """Update all installed plugins that have updates available."""
        results = {}
        updates = self.check_for_updates()
        
        for plugin, (has_update, current, latest) in updates.items():
            if has_update:
                try:
                    if plugin == "geyser":
                        self.download_geyser(force_update=True)
                    elif plugin == "floodgate":
                        self.download_floodgate(force_update=True)
                    elif plugin == "kubecontrol":
                        self.download_kubecontrol_plugin(force_update=True)
                    results[plugin] = f"Actualizado: {current} → {latest}"
                except Exception as e:
                    results[plugin] = f"Error: {e}"
            else:
                results[plugin] = "Ya está actualizado"
        
        return results
    
    def _download(self, url: str, filename: str) -> str:
        output_path = os.path.join(self.plugins_dir, filename)
        print(f"Descargando {filename}...")
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(output_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            return output_path
        except Exception as e:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
