"""
Local File Storage Utility - Replacement for AWS S3
Provides file operations for tutorial recordings and user layouts
"""

import os
import json
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from werkzeug.utils import secure_filename
import uuid
import logging

logger = logging.getLogger(__name__)

class LocalStorageManager:
    """Manages local file storage operations"""
    
    def __init__(self, recordings_path: str = "storage/recordings", layouts_path: str = "storage/layouts"):
        """
        Initialize local storage manager
        
        Args:
            recordings_path: Path for tutorial recordings and metadata
            layouts_path: Path for user layouts
        """
        self.recordings_path = Path(recordings_path)
        self.layouts_path = Path(layouts_path)
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        self.recordings_path.mkdir(parents=True, exist_ok=True)
        self.layouts_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Storage directories initialized: {self.recordings_path}, {self.layouts_path}")
    
    def _validate_path_security(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks"""
        # Remove any potential directory traversal attempts
        clean_path = os.path.normpath(path)
        return not (".." in clean_path or path.startswith("/") or "\\" in path)
    
    # Recording Storage Methods (replaces S3_BUCKET_NAME operations)
    
    def save_recording_file(self, tutorial_section_id: str, filename: str, content: bytes) -> bool:
        """
        Save a file for a tutorial section
        
        Args:
            tutorial_section_id: UUID of the tutorial section
            filename: Name of the file to save
            content: File content as bytes
            
        Returns:
            bool: Success status
        """
        try:
            if not self._validate_path_security(tutorial_section_id) or not self._validate_path_security(filename):
                logger.error(f"Invalid path detected: {tutorial_section_id}/{filename}")
                return False
                
            # Create section directory
            section_dir = self.recordings_path / tutorial_section_id
            section_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = section_dir / secure_filename(filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Saved recording file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving recording file {tutorial_section_id}/{filename}: {str(e)}")
            return False
    
    def get_recording_file(self, tutorial_section_id: str, filename: str) -> Optional[bytes]:
        """
        Retrieve a file for a tutorial section
        
        Args:
            tutorial_section_id: UUID of the tutorial section
            filename: Name of the file to retrieve
            
        Returns:
            bytes: File content or None if not found
        """
        try:
            if not self._validate_path_security(tutorial_section_id) or not self._validate_path_security(filename):
                logger.error(f"Invalid path detected: {tutorial_section_id}/{filename}")
                return None
                
            file_path = self.recordings_path / tutorial_section_id / secure_filename(filename)
            
            if not file_path.exists():
                logger.warning(f"Recording file not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                content = f.read()
            
            logger.info(f"Retrieved recording file: {file_path}")
            return content
            
        except Exception as e:
            logger.error(f"Error retrieving recording file {tutorial_section_id}/{filename}: {str(e)}")
            return None
    
    def list_recording_files(self, tutorial_section_id: str) -> List[str]:
        """
        List all files for a tutorial section
        
        Args:
            tutorial_section_id: UUID of the tutorial section
            
        Returns:
            List[str]: List of filenames
        """
        try:
            if not self._validate_path_security(tutorial_section_id):
                logger.error(f"Invalid path detected: {tutorial_section_id}")
                return []
                
            section_dir = self.recordings_path / tutorial_section_id
            
            if not section_dir.exists():
                return []
            
            files = [f.name for f in section_dir.iterdir() if f.is_file()]
            logger.info(f"Listed {len(files)} files for section {tutorial_section_id}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing recording files for {tutorial_section_id}: {str(e)}")
            return []
    
    def delete_recording_section(self, tutorial_section_id: str) -> bool:
        """
        Delete all files for a tutorial section
        
        Args:
            tutorial_section_id: UUID of the tutorial section
            
        Returns:
            bool: Success status
        """
        try:
            if not self._validate_path_security(tutorial_section_id):
                logger.error(f"Invalid path detected: {tutorial_section_id}")
                return False
                
            section_dir = self.recordings_path / tutorial_section_id
            
            if section_dir.exists():
                shutil.rmtree(section_dir)
                logger.info(f"Deleted recording section: {section_dir}")
                return True
            else:
                logger.warning(f"Recording section directory not found: {section_dir}")
                return True  # Already deleted
                
        except Exception as e:
            logger.error(f"Error deleting recording section {tutorial_section_id}: {str(e)}")
            return False
    
    def copy_recording_section(self, source_id: str, dest_id: str) -> bool:
        """
        Copy all files from one tutorial section to another
        
        Args:
            source_id: Source tutorial section UUID
            dest_id: Destination tutorial section UUID
            
        Returns:
            bool: Success status
        """
        try:
            if not self._validate_path_security(source_id) or not self._validate_path_security(dest_id):
                logger.error(f"Invalid path detected: {source_id} -> {dest_id}")
                return False
                
            source_dir = self.recordings_path / source_id
            dest_dir = self.recordings_path / dest_id
            
            if not source_dir.exists():
                logger.error(f"Source recording section not found: {source_dir}")
                return False
            
            # Create destination directory
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy all files
            for file_path in source_dir.iterdir():
                if file_path.is_file():
                    dest_file = dest_dir / file_path.name
                    shutil.copy2(file_path, dest_file)
            
            logger.info(f"Copied recording section: {source_dir} -> {dest_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying recording section {source_id} -> {dest_id}: {str(e)}")
            return False
    
    # Layout Storage Methods (replaces S3_LEARNER_BUCKET_NAME operations)
    
    def save_user_layout(self, user_id: int, tutorial_id: str, role: str, layout_data: Dict[str, Any]) -> bool:
        """
        Save user layout configuration
        
        Args:
            user_id: User ID
            tutorial_id: Tutorial UUID
            role: User role (author/learner)
            layout_data: Layout configuration data
            
        Returns:
            bool: Success status
        """
        try:
            if not self._validate_path_security(str(user_id)) or not self._validate_path_security(tutorial_id) or not self._validate_path_security(role):
                logger.error(f"Invalid path detected: {user_id}/{tutorial_id}/{role}")
                return False
                
            # Create user/tutorial/role directory structure
            layout_dir = self.layouts_path / str(user_id) / tutorial_id / role
            layout_dir.mkdir(parents=True, exist_ok=True)
            
            # Save layout as JSON
            layout_file = layout_dir / "layout.json"
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved user layout: {layout_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving user layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return False
    
    def get_user_layout(self, user_id: int, tutorial_id: str, role: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user layout configuration
        
        Args:
            user_id: User ID
            tutorial_id: Tutorial UUID
            role: User role (author/learner)
            
        Returns:
            Dict[str, Any]: Layout data or None if not found
        """
        try:
            if not self._validate_path_security(str(user_id)) or not self._validate_path_security(tutorial_id) or not self._validate_path_security(role):
                logger.error(f"Invalid path detected: {user_id}/{tutorial_id}/{role}")
                return None
                
            layout_file = self.layouts_path / str(user_id) / tutorial_id / role / "layout.json"
            
            if not layout_file.exists():
                logger.warning(f"User layout not found: {layout_file}")
                return None
            
            with open(layout_file, 'r', encoding='utf-8') as f:
                layout_data = json.load(f)
            
            logger.info(f"Retrieved user layout: {layout_file}")
            return layout_data
            
        except Exception as e:
            logger.error(f"Error retrieving user layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return None
    
    # Utility Methods
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        Get storage usage statistics
        
        Returns:
            Dict[str, Any]: Storage statistics
        """
        try:
            def get_dir_size(path: Path) -> int:
                total = 0
                for item in path.rglob('*'):
                    if item.is_file():
                        total += item.stat().st_size
                return total
            
            recordings_size = get_dir_size(self.recordings_path) if self.recordings_path.exists() else 0
            layouts_size = get_dir_size(self.layouts_path) if self.layouts_path.exists() else 0
            
            return {
                'recordings_path': str(self.recordings_path),
                'layouts_path': str(self.layouts_path),
                'recordings_size_bytes': recordings_size,
                'layouts_size_bytes': layouts_size,
                'total_size_bytes': recordings_size + layouts_size,
                'recordings_size_mb': round(recordings_size / (1024 * 1024), 2),
                'layouts_size_mb': round(layouts_size / (1024 * 1024), 2),
                'total_size_mb': round((recordings_size + layouts_size) / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {str(e)}")
            return {
                'error': str(e)
            }
    
    def cleanup_empty_directories(self) -> int:
        """
        Remove empty directories from storage
        
        Returns:
            int: Number of directories removed
        """
        removed_count = 0
        try:
            # Clean recordings
            for root, dirs, files in os.walk(self.recordings_path, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):  # Directory is empty
                            dir_path.rmdir()
                            removed_count += 1
                    except OSError:
                        pass  # Directory not empty or other issue
            
            # Clean layouts
            for root, dirs, files in os.walk(self.layouts_path, topdown=False):
                for dir_name in dirs:
                    dir_path = Path(root) / dir_name
                    try:
                        if not any(dir_path.iterdir()):  # Directory is empty
                            dir_path.rmdir()
                            removed_count += 1
                    except OSError:
                        pass  # Directory not empty or other issue
                        
            logger.info(f"Cleaned up {removed_count} empty directories")
            return removed_count
            
        except Exception as e:
            logger.error(f"Error cleaning up directories: {str(e)}")
            return removed_count

# Global instance
storage_manager = None

def get_storage_manager(recordings_path: str = "storage/recordings", layouts_path: str = "storage/layouts") -> LocalStorageManager:
    """Get or create global storage manager instance"""
    global storage_manager
    if storage_manager is None:
        storage_manager = LocalStorageManager(recordings_path, layouts_path)
    return storage_manager