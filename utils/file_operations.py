"""
File Operations Utility
Handles file system operations for the Flutter development server
"""

import os
import shutil
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path


class FileOperations:
    """
    Utility class for safe file operations
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.backup_dir = self.project_path / ".backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        Safely read file contents
        
        Args:
            file_path: Relative path to file
            
        Returns:
            File contents or None if error
        """
        try:
            full_path = self.project_path / file_path
            if full_path.exists() and full_path.is_file():
                with open(full_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        return None
    
    def write_file(self, file_path: str, content: str, create_backup: bool = True) -> bool:
        """
        Safely write file contents with optional backup
        
        Args:
            file_path: Relative path to file
            content: Content to write
            create_backup: Whether to create backup first
            
        Returns:
            Success status
        """
        try:
            full_path = self.project_path / file_path
            
            # Create backup if file exists
            if create_backup and full_path.exists():
                self.create_backup(file_path)
            
            # Create directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        except Exception as e:
            print(f"Error writing file {file_path}: {e}")
            return False
    
    def create_backup(self, file_path: str) -> Optional[str]:
        """
        Create backup of file
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Backup file path or None if error
        """
        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                return None
            
            # Create backup filename with timestamp
            import time
            timestamp = int(time.time())
            backup_name = f"{file_path.replace('/', '_')}_{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup
            shutil.copy2(full_path, backup_path)
            
            return str(backup_path)
        except Exception as e:
            print(f"Error creating backup for {file_path}: {e}")
            return None
    
    def restore_backup(self, file_path: str, backup_path: str) -> bool:
        """
        Restore file from backup
        
        Args:
            file_path: Relative path to file
            backup_path: Path to backup file
            
        Returns:
            Success status
        """
        try:
            full_path = self.project_path / file_path
            backup_full_path = Path(backup_path)
            
            if backup_full_path.exists():
                shutil.copy2(backup_full_path, full_path)
                return True
        except Exception as e:
            print(f"Error restoring backup {backup_path} to {file_path}: {e}")
        return False
    
    def list_files(self, pattern: str = "*.dart", recursive: bool = True) -> List[str]:
        """
        List files matching pattern
        
        Args:
            pattern: Glob pattern to match
            recursive: Whether to search recursively
            
        Returns:
            List of relative file paths
        """
        try:
            if recursive:
                files = list(self.project_path.rglob(pattern))
            else:
                files = list(self.project_path.glob(pattern))
            
            # Return relative paths
            return [str(f.relative_to(self.project_path)) for f in files if f.is_file()]
        except Exception as e:
            print(f"Error listing files with pattern {pattern}: {e}")
            return []
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if file exists
        
        Args:
            file_path: Relative path to file
            
        Returns:
            True if file exists
        """
        full_path = self.project_path / file_path
        return full_path.exists() and full_path.is_file()
    
    def get_file_info(self, file_path: str) -> Optional[Dict]:
        """
        Get file information
        
        Args:
            file_path: Relative path to file
            
        Returns:
            Dictionary with file info or None if error
        """
        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                return None
            
            stat = full_path.stat()
            return {
                "path": file_path,
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "is_file": full_path.is_file(),
                "is_dir": full_path.is_dir(),
                "extension": full_path.suffix
            }
        except Exception as e:
            print(f"Error getting file info for {file_path}: {e}")
            return None
    
    def create_directory(self, dir_path: str) -> bool:
        """
        Create directory
        
        Args:
            dir_path: Relative path to directory
            
        Returns:
            Success status
        """
        try:
            full_path = self.project_path / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating directory {dir_path}: {e}")
            return False
    
    def delete_file(self, file_path: str, create_backup: bool = True) -> bool:
        """
        Delete file with optional backup
        
        Args:
            file_path: Relative path to file
            create_backup: Whether to create backup first
            
        Returns:
            Success status
        """
        try:
            full_path = self.project_path / file_path
            if not full_path.exists():
                return True
            
            # Create backup if requested
            if create_backup:
                self.create_backup(file_path)
            
            # Delete file
            full_path.unlink()
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        Copy file
        
        Args:
            source_path: Relative path to source file
            dest_path: Relative path to destination file
            
        Returns:
            Success status
        """
        try:
            source_full = self.project_path / source_path
            dest_full = self.project_path / dest_path
            
            if not source_full.exists():
                return False
            
            # Create destination directory if needed
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(source_full, dest_full)
            return True
        except Exception as e:
            print(f"Error copying file {source_path} to {dest_path}: {e}")
            return False
    
    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Move file
        
        Args:
            source_path: Relative path to source file
            dest_path: Relative path to destination file
            
        Returns:
            Success status
        """
        try:
            source_full = self.project_path / source_path
            dest_full = self.project_path / dest_path
            
            if not source_full.exists():
                return False
            
            # Create destination directory if needed
            dest_full.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            shutil.move(str(source_full), str(dest_full))
            return True
        except Exception as e:
            print(f"Error moving file {source_path} to {dest_path}: {e}")
            return False
    
    def clean_backups(self, max_age_days: int = 7) -> int:
        """
        Clean old backup files
        
        Args:
            max_age_days: Maximum age of backups to keep
            
        Returns:
            Number of files cleaned
        """
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            cleaned = 0
            for backup_file in self.backup_dir.glob("*.bak"):
                if current_time - backup_file.stat().st_mtime > max_age_seconds:
                    backup_file.unlink()
                    cleaned += 1
            
            return cleaned
        except Exception as e:
            print(f"Error cleaning backups: {e}")
            return 0
    
    def get_project_tree(self, max_depth: int = 3) -> Dict:
        """
        Get project directory tree
        
        Args:
            max_depth: Maximum depth to traverse
            
        Returns:
            Dictionary representing directory tree
        """
        def build_tree(path: Path, current_depth: int = 0) -> Dict:
            if current_depth >= max_depth:
                return {}
            
            tree = {}
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith('.'):
                        continue
                    
                    relative_path = str(item.relative_to(self.project_path))
                    
                    if item.is_dir():
                        tree[item.name] = {
                            "type": "directory",
                            "path": relative_path,
                            "children": build_tree(item, current_depth + 1)
                        }
                    else:
                        tree[item.name] = {
                            "type": "file",
                            "path": relative_path,
                            "size": item.stat().st_size,
                            "extension": item.suffix
                        }
            except PermissionError:
                pass
            
            return tree
        
        return build_tree(self.project_path)