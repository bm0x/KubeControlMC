"""
ServerSanitizer - Module for validating and repairing Minecraft server directory structure.

This module ensures that server files are in their correct locations:
- Plugin JARs should be in the 'plugins/' directory
- Only the server JAR should be in the root server_bin directory
- Plugin configuration folders should be inside 'plugins/'
"""

import os
import shutil
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SanitizationIssue:
    """Represents a single issue found during sanitization scan."""
    issue_type: str  # 'misplaced_jar', 'misplaced_dir', 'unknown_file'
    file_path: str
    suggested_action: str
    destination: Optional[str] = None


@dataclass
class SanitizationReport:
    """Report of issues found during a directory scan."""
    issues: List[SanitizationIssue] = field(default_factory=list)
    scanned_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0
    
    def summary(self) -> str:
        if not self.has_issues:
            return "No issues found. Directory structure is correct."
        return f"Found {len(self.issues)} issue(s) requiring attention."


@dataclass
class SanitizationResult:
    """Result of a sanitization operation."""
    success: bool
    moved_files: List[Dict[str, str]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        if self.success:
            return f"Moved {len(self.moved_files)} file(s) successfully."
        return f"Completed with {len(self.errors)} error(s)."


class ServerSanitizer:
    """
    Validates and repairs Minecraft server directory structure.
    
    Expected structure:
        server_bin/
        ├── *.jar                    # Only server JAR (paper, folia, etc.)
        ├── eula.txt
        ├── server.properties
        ├── plugins/                 # All plugin JARs and configs HERE
        │   ├── *.jar
        │   └── [plugin-folders]/
        ├── world/
        ├── logs/
        └── [other server files]
    """
    
    # Files that are valid in the root directory
    VALID_ROOT_FILES = {
        'eula.txt', 'server.properties', 'bukkit.yml', 'spigot.yml', 
        'paper.yml', 'paper-global.yml', 'paper-world-defaults.yml',
        'commands.yml', 'help.yml', 'permissions.yml', 'whitelist.json',
        'banned-ips.json', 'banned-players.json', 'ops.json', 'usercache.json',
        '.plugin_versions.json'
    }
    
    # Directories that are valid in the root directory
    VALID_ROOT_DIRS = {
        'plugins', 'world', 'world_nether', 'world_the_end',
        'logs', 'cache', 'libraries', 'versions', 'config',
        'crash-reports', 'bundler'
    }
    
    # Patterns that identify server JARs (NOT plugins)
    SERVER_JAR_PATTERNS = [
        'paper-', 'folia-', 'velocity-', 'spigot-', 'craftbukkit-',
        'purpur-', 'pufferfish-', 'airplane-', 'tuinity-'
    ]
    
    # Known plugin JAR patterns (to distinguish from server JAR)
    PLUGIN_JAR_PATTERNS = [
        'geyser', 'floodgate', 'kubecontrol', 'essentials', 'worldedit',
        'worldguard', 'vault', 'luckperms', 'coreprotect', 'dynmap',
        'multiverse', 'citizens', 'protocollib', 'placeholderapi',
        'sk89q', 'hologram', 'tab', 'npc', 'quest'
    ]
    
    def __init__(self, server_dir: str):
        """
        Initialize the sanitizer.
        
        Args:
            server_dir: Path to the server_bin directory
        """
        self.server_dir = os.path.abspath(server_dir)
        self.plugins_dir = os.path.join(self.server_dir, 'plugins')
    
    def is_server_jar(self, filename: str) -> bool:
        """
        Determine if a JAR file is a server JAR (not a plugin).
        
        Args:
            filename: Name of the JAR file
            
        Returns:
            True if it's a server JAR, False otherwise
        """
        lower_name = filename.lower()
        
        # Check if it matches server patterns
        for pattern in self.SERVER_JAR_PATTERNS:
            if lower_name.startswith(pattern):
                return True
        
        return False
    
    def is_plugin_jar(self, filename: str) -> bool:
        """
        Determine if a JAR file is a plugin JAR.
        
        Simple rule: Any JAR that is NOT a server JAR is a plugin.
        Server JARs are: paper, folia, velocity, spigot, etc.
        
        Args:
            filename: Name of the JAR file
            
        Returns:
            True if it's a plugin JAR (should go in plugins/), False if it's a server JAR
        """
        # If it's a server JAR, it's NOT a plugin
        if self.is_server_jar(filename):
            return False
        
        # Any other JAR is a plugin and should be in plugins/
        return True
    
    def is_plugin_config_dir(self, dirname: str) -> bool:
        """
        Determine if a directory should be moved to plugins/.
        
        Simple rule: Any folder that is NOT a valid server folder
        (world, logs, plugins, etc.) is treated as a plugin config folder.
        
        Args:
            dirname: Name of the directory
            
        Returns:
            True if it should be in plugins/, False if it's a valid server folder
        """
        # If it's a valid server root directory, leave it alone
        if dirname in self.VALID_ROOT_DIRS:
            return False
        
        # Any other folder should be moved to plugins/
        return True
    
    def scan(self) -> SanitizationReport:
        """
        Scan the server directory for structural issues.
        Scans root AND subdirectories for misplaced plugin JARs.
        
        Returns:
            SanitizationReport with all issues found
        """
        report = SanitizationReport()
        
        if not os.path.exists(self.server_dir):
            return report
        
        # Ensure plugins directory exists
        if not os.path.exists(self.plugins_dir):
            os.makedirs(self.plugins_dir)
        
        # Scan root directory
        for item in os.listdir(self.server_dir):
            item_path = os.path.join(self.server_dir, item)
            
            if os.path.isfile(item_path):
                # Check JAR files in root
                if item.endswith('.jar'):
                    if self.is_plugin_jar(item):
                        report.issues.append(SanitizationIssue(
                            issue_type='misplaced_jar',
                            file_path=item_path,
                            suggested_action=f"Move plugin JAR to plugins/",
                            destination=os.path.join(self.plugins_dir, item)
                        ))
            
            elif os.path.isdir(item_path):
                # Any folder that's not a valid server folder should be in plugins/
                if self.is_plugin_config_dir(item):
                    report.issues.append(SanitizationIssue(
                        issue_type='misplaced_dir',
                        file_path=item_path,
                        suggested_action=f"Move folder to plugins/",
                        destination=os.path.join(self.plugins_dir, item)
                    ))
                # Also scan inside valid server directories for stray plugin JARs
                elif item in self.VALID_ROOT_DIRS and item != 'plugins':
                    self._scan_subdirectory(item_path, report)
        
        return report
    
    def _scan_subdirectory(self, dir_path: str, report: SanitizationReport):
        """
        Recursively scan a subdirectory for misplaced plugin JARs.
        
        Args:
            dir_path: Path to the directory to scan
            report: SanitizationReport to append issues to
        """
        try:
            for item in os.listdir(dir_path):
                item_path = os.path.join(dir_path, item)
                
                if os.path.isfile(item_path) and item.endswith('.jar'):
                    # Any JAR in a server subdirectory (not plugins) should be checked
                    if self.is_plugin_jar(item):
                        report.issues.append(SanitizationIssue(
                            issue_type='misplaced_jar_deep',
                            file_path=item_path,
                            suggested_action=f"Move plugin JAR to plugins/",
                            destination=os.path.join(self.plugins_dir, item)
                        ))
                elif os.path.isdir(item_path):
                    # Recurse into subdirectories
                    self._scan_subdirectory(item_path, report)
        except PermissionError:
            pass
    
    def sanitize(self, dry_run: bool = True) -> SanitizationResult:
        """
        Fix structural issues by moving files to correct locations.
        After moving, verifies and deletes any leftovers from source.
        
        Args:
            dry_run: If True, only report what would be done without making changes
            
        Returns:
            SanitizationResult with operation details
        """
        report = self.scan()
        result = SanitizationResult(success=True)
        
        if not report.has_issues:
            return result
        
        for issue in report.issues:
            if issue.destination is None:
                continue
            
            try:
                if dry_run:
                    result.moved_files.append({
                        'from': issue.file_path,
                        'to': issue.destination,
                        'status': 'would_move'
                    })
                else:
                    # Check if destination already exists
                    if os.path.exists(issue.destination):
                        # Overwrite - delete existing first
                        if os.path.isdir(issue.destination):
                            shutil.rmtree(issue.destination)
                        else:
                            os.remove(issue.destination)
                    
                    # Move the file/directory
                    shutil.move(issue.file_path, issue.destination)
                    result.moved_files.append({
                        'from': issue.file_path,
                        'to': issue.destination,
                        'status': 'moved'
                    })
                    logger.info(f"Moved: {issue.file_path} -> {issue.destination}")
                    
                    # VERIFY: If source still exists, DELETE it
                    if os.path.exists(issue.file_path):
                        if os.path.isdir(issue.file_path):
                            shutil.rmtree(issue.file_path)
                        else:
                            os.remove(issue.file_path)
                        logger.info(f"Deleted leftover: {issue.file_path}")
                    
            except Exception as e:
                result.errors.append(f"Error processing {issue.file_path}: {str(e)}")
                result.success = False
                logger.error(f"Failed to process {issue.file_path}: {e}")
        
        return result
    
    def validate_structure(self) -> bool:
        """
        Quick validation check for directory structure.
        
        Returns:
            True if structure is valid, False otherwise
        """
        report = self.scan()
        return not report.has_issues
    
    def get_structure_summary(self) -> Dict:
        """
        Get a summary of the current directory structure.
        
        Returns:
            Dictionary with structure information
        """
        summary = {
            'server_dir': self.server_dir,
            'exists': os.path.exists(self.server_dir),
            'server_jar': None,
            'plugins_count': 0,
            'worlds': [],
            'has_eula': False,
            'has_properties': False
        }
        
        if not summary['exists']:
            return summary
        
        for item in os.listdir(self.server_dir):
            item_path = os.path.join(self.server_dir, item)
            
            if item.endswith('.jar') and self.is_server_jar(item):
                summary['server_jar'] = item
            elif item == 'eula.txt':
                summary['has_eula'] = True
            elif item == 'server.properties':
                summary['has_properties'] = True
            elif item.startswith('world') and os.path.isdir(item_path):
                summary['worlds'].append(item)
        
        if os.path.exists(self.plugins_dir):
            plugins = [f for f in os.listdir(self.plugins_dir) if f.endswith('.jar')]
            summary['plugins_count'] = len(plugins)
        
        return summary
