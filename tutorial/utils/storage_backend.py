"""
Abstract Storage Backend - Supports both S3 and Local File Storage
Provides a unified interface for file operations regardless of storage backend
"""

import os
import json
import shutil
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from werkzeug.utils import secure_filename
from decouple import config

logger = logging.getLogger(__name__)

class StorageBackend(ABC):
    """Abstract base class for storage backends"""
    
    @abstractmethod
    def save_recording_file(self, tutorial_section_id: str, filename: str, content: bytes) -> bool:
        """Save a recording file"""
        pass
    
    @abstractmethod
    def get_recording_file(self, tutorial_section_id: str, filename: str) -> Optional[bytes]:
        """Get a recording file"""
        pass
    
    @abstractmethod
    def list_recording_files(self, tutorial_section_id: str) -> List[str]:
        """List all files for a tutorial section"""
        pass
    
    @abstractmethod
    def delete_recording_section(self, tutorial_section_id: str) -> bool:
        """Delete all files for a tutorial section"""
        pass
    
    @abstractmethod
    def copy_recording_section(self, source_id: str, dest_id: str) -> bool:
        """Copy all files from one section to another"""
        pass
    
    @abstractmethod
    def save_user_layout(self, user_id: int, tutorial_id: str, role: str, layout_data: Dict[str, Any]) -> bool:
        """Save user layout"""
        pass
    
    @abstractmethod
    def get_user_layout(self, user_id: int, tutorial_id: str, role: str) -> Optional[Dict[str, Any]]:
        """Get user layout"""
        pass
    
    @abstractmethod
    def get_file_url(self, tutorial_section_id: str, filename: str, expires_in: int = 3600) -> Optional[str]:
        """Get a URL to access the file (for serving to client)"""
        pass
    
    @abstractmethod
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about the storage backend"""
        pass

class LocalStorageBackend(StorageBackend):
    """Local file system storage implementation"""
    
    def __init__(self, recordings_path: str = "storage/recordings", layouts_path: str = "storage/layouts"):
        self.recordings_path = Path(recordings_path)
        self.layouts_path = Path(layouts_path)
        self._ensure_directories()
        logger.info(f"Initialized Local Storage: recordings={self.recordings_path}, layouts={self.layouts_path}")
    
    def _ensure_directories(self):
        """Create storage directories if they don't exist"""
        self.recordings_path.mkdir(parents=True, exist_ok=True)
        self.layouts_path.mkdir(parents=True, exist_ok=True)
    
    def _validate_path_security(self, path: str) -> bool:
        """Validate path to prevent directory traversal attacks"""
        clean_path = os.path.normpath(path)
        return not (".." in clean_path or path.startswith("/") or "\\" in path)
    
    def save_recording_file(self, tutorial_section_id: str, filename: str, content: bytes) -> bool:
        try:
            if not self._validate_path_security(tutorial_section_id) or not self._validate_path_security(filename):
                logger.error(f"Invalid path detected: {tutorial_section_id}/{filename}")
                return False
            
            section_dir = self.recordings_path / tutorial_section_id
            section_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = section_dir / secure_filename(filename)
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Saved local file: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving local file {tutorial_section_id}/{filename}: {str(e)}")
            return False
    
    def get_recording_file(self, tutorial_section_id: str, filename: str) -> Optional[bytes]:
        try:
            if not self._validate_path_security(tutorial_section_id) or not self._validate_path_security(filename):
                return None
            
            file_path = self.recordings_path / tutorial_section_id / secure_filename(filename)
            if not file_path.exists():
                return None
            
            with open(file_path, 'rb') as f:
                return f.read()
                
        except Exception as e:
            logger.error(f"Error reading local file {tutorial_section_id}/{filename}: {str(e)}")
            return None
    
    def list_recording_files(self, tutorial_section_id: str) -> List[str]:
        try:
            if not self._validate_path_security(tutorial_section_id):
                return []
            
            section_dir = self.recordings_path / tutorial_section_id
            if not section_dir.exists():
                return []
            
            return [f.name for f in section_dir.iterdir() if f.is_file()]
            
        except Exception as e:
            logger.error(f"Error listing local files for {tutorial_section_id}: {str(e)}")
            return []
    
    def delete_recording_section(self, tutorial_section_id: str) -> bool:
        try:
            if not self._validate_path_security(tutorial_section_id):
                return False
            
            section_dir = self.recordings_path / tutorial_section_id
            if section_dir.exists():
                shutil.rmtree(section_dir)
                logger.info(f"Deleted local section: {section_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting local section {tutorial_section_id}: {str(e)}")
            return False
    
    def copy_recording_section(self, source_id: str, dest_id: str) -> bool:
        try:
            if not self._validate_path_security(source_id) or not self._validate_path_security(dest_id):
                return False
            
            source_dir = self.recordings_path / source_id
            dest_dir = self.recordings_path / dest_id
            
            if not source_dir.exists():
                return False
            
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in source_dir.iterdir():
                if file_path.is_file():
                    dest_file = dest_dir / file_path.name
                    shutil.copy2(file_path, dest_file)
            
            logger.info(f"Copied local section: {source_dir} -> {dest_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying local section {source_id} -> {dest_id}: {str(e)}")
            return False
    
    def save_user_layout(self, user_id: int, tutorial_id: str, role: str, layout_data: Dict[str, Any]) -> bool:
        try:
            if not all(self._validate_path_security(str(p)) for p in [user_id, tutorial_id, role]):
                return False
            
            layout_dir = self.layouts_path / str(user_id) / tutorial_id / role
            layout_dir.mkdir(parents=True, exist_ok=True)
            
            layout_file = layout_dir / "layout.json"
            with open(layout_file, 'w', encoding='utf-8') as f:
                json.dump(layout_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved local layout: {layout_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving local layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return False
    
    def get_user_layout(self, user_id: int, tutorial_id: str, role: str) -> Optional[Dict[str, Any]]:
        try:
            if not all(self._validate_path_security(str(p)) for p in [user_id, tutorial_id, role]):
                return None
            
            layout_file = self.layouts_path / str(user_id) / tutorial_id / role / "layout.json"
            if not layout_file.exists():
                return None
            
            with open(layout_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error reading local layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return None
    
    def get_file_url(self, tutorial_section_id: str, filename: str, expires_in: int = 3600) -> Optional[str]:
        """Return a local URL path for file serving"""
        if not self._validate_path_security(tutorial_section_id) or not self._validate_path_security(filename):
            return None
        
        file_path = self.recordings_path / tutorial_section_id / secure_filename(filename)
        if file_path.exists():
            # Return a URL that can be handled by Flask route
            return f"/api/files/{tutorial_section_id}/{filename}"
        return None
    
    def get_backend_info(self) -> Dict[str, Any]:
        def get_dir_size(path: Path) -> int:
            if not path.exists():
                return 0
            total = 0
            for item in path.rglob('*'):
                if item.is_file():
                    total += item.stat().st_size
            return total
        
        recordings_size = get_dir_size(self.recordings_path)
        layouts_size = get_dir_size(self.layouts_path)
        
        return {
            'backend_type': 'local',
            'recordings_path': str(self.recordings_path),
            'layouts_path': str(self.layouts_path),
            'recordings_size_bytes': recordings_size,
            'layouts_size_bytes': layouts_size,
            'total_size_mb': round((recordings_size + layouts_size) / (1024 * 1024), 2)
        }

class S3StorageBackend(StorageBackend):
    """AWS S3 storage implementation"""
    
    def __init__(self, access_key_id: str, secret_access_key: str, 
                 recordings_bucket: str, layouts_bucket: str, region: str = 'us-east-1'):
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError, ClientError
            
            self.recordings_bucket = recordings_bucket
            self.layouts_bucket = layouts_bucket
            
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region
            )
            
            self.s3_resource = boto3.resource(
                's3',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                region_name=region
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=recordings_bucket)
            if layouts_bucket:
                self.s3_client.head_bucket(Bucket=layouts_bucket)
            
            logger.info(f"Initialized S3 Storage: recordings={recordings_bucket}, layouts={layouts_bucket}")
            
        except ImportError:
            raise RuntimeError("boto3 is required for S3 storage. Install with: pip install boto3")
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"S3 connection failed: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"S3 initialization error: {str(e)}")
    
    def save_recording_file(self, tutorial_section_id: str, filename: str, content: bytes) -> bool:
        try:
            from io import BytesIO
            
            key = f"{tutorial_section_id}/{filename}"
            self.s3_client.upload_fileobj(
                BytesIO(content), 
                self.recordings_bucket, 
                key
            )
            logger.info(f"Saved S3 file: s3://{self.recordings_bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving S3 file {tutorial_section_id}/{filename}: {str(e)}")
            return False
    
    def get_recording_file(self, tutorial_section_id: str, filename: str) -> Optional[bytes]:
        try:
            key = f"{tutorial_section_id}/{filename}"
            response = self.s3_client.get_object(Bucket=self.recordings_bucket, Key=key)
            return response['Body'].read()
            
        except self.s3_client.exceptions.NoSuchKey:
            logger.warning(f"S3 file not found: s3://{self.recordings_bucket}/{tutorial_section_id}/{filename}")
            return None
        except Exception as e:
            logger.error(f"Error reading S3 file {tutorial_section_id}/{filename}: {str(e)}")
            return None
    
    def list_recording_files(self, tutorial_section_id: str) -> List[str]:
        try:
            prefix = f"{tutorial_section_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.recordings_bucket, 
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return []
            
            files = []
            for obj in response['Contents']:
                # Extract filename from key (remove prefix)
                filename = obj['Key'][len(prefix):]
                if filename:  # Skip directory entries
                    files.append(filename)
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing S3 files for {tutorial_section_id}: {str(e)}")
            return []
    
    def delete_recording_section(self, tutorial_section_id: str) -> bool:
        try:
            prefix = f"{tutorial_section_id}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.recordings_bucket, 
                Prefix=prefix
            )
            
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                self.s3_client.delete_objects(
                    Bucket=self.recordings_bucket,
                    Delete={'Objects': objects}
                )
                logger.info(f"Deleted S3 section: s3://{self.recordings_bucket}/{prefix}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting S3 section {tutorial_section_id}: {str(e)}")
            return False
    
    def copy_recording_section(self, source_id: str, dest_id: str) -> bool:
        try:
            # List source files
            source_files = self.list_recording_files(source_id)
            
            for filename in source_files:
                source_key = f"{source_id}/{filename}"
                dest_key = f"{dest_id}/{filename}"
                
                copy_source = {
                    'Bucket': self.recordings_bucket,
                    'Key': source_key
                }
                
                self.s3_resource.meta.client.copy(
                    copy_source, 
                    self.recordings_bucket, 
                    dest_key
                )
            
            logger.info(f"Copied S3 section: {source_id} -> {dest_id} ({len(source_files)} files)")
            return True
            
        except Exception as e:
            logger.error(f"Error copying S3 section {source_id} -> {dest_id}: {str(e)}")
            return False
    
    def save_user_layout(self, user_id: int, tutorial_id: str, role: str, layout_data: Dict[str, Any]) -> bool:
        try:
            from io import BytesIO
            
            if not self.layouts_bucket:
                logger.error("Layouts bucket not configured")
                return False
            
            key = f"{user_id}/{tutorial_id}/{role}/layout.json"
            content = json.dumps(layout_data, indent=2, ensure_ascii=False).encode('utf-8')
            
            self.s3_client.upload_fileobj(
                BytesIO(content),
                self.layouts_bucket,
                key
            )
            
            logger.info(f"Saved S3 layout: s3://{self.layouts_bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving S3 layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return False
    
    def get_user_layout(self, user_id: int, tutorial_id: str, role: str) -> Optional[Dict[str, Any]]:
        try:
            if not self.layouts_bucket:
                return None
            
            key = f"{user_id}/{tutorial_id}/{role}/layout.json"
            response = self.s3_client.get_object(Bucket=self.layouts_bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
            
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            logger.error(f"Error reading S3 layout {user_id}/{tutorial_id}/{role}: {str(e)}")
            return None
    
    def get_file_url(self, tutorial_section_id: str, filename: str, expires_in: int = 3600) -> Optional[str]:
        """Generate presigned URL for S3 file access"""
        try:
            key = f"{tutorial_section_id}/{filename}"
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.recordings_bucket, 'Key': key},
                ExpiresIn=expires_in
            )
            return url
            
        except Exception as e:
            logger.error(f"Error generating S3 presigned URL {tutorial_section_id}/{filename}: {str(e)}")
            return None
    
    def get_backend_info(self) -> Dict[str, Any]:
        try:
            # Get bucket information
            recordings_info = self.s3_client.head_bucket(Bucket=self.recordings_bucket)
            layouts_info = None
            if self.layouts_bucket:
                layouts_info = self.s3_client.head_bucket(Bucket=self.layouts_bucket)
            
            return {
                'backend_type': 's3',
                'recordings_bucket': self.recordings_bucket,
                'layouts_bucket': self.layouts_bucket,
                'region': self.s3_client.meta.region_name,
                'recordings_accessible': bool(recordings_info),
                'layouts_accessible': bool(layouts_info) if self.layouts_bucket else None
            }
            
        except Exception as e:
            return {
                'backend_type': 's3',
                'error': str(e)
            }

class StorageManager:
    """Storage manager that provides unified access to different storage backends"""
    
    def __init__(self):
        self.backend: Optional[StorageBackend] = None
        self._initialize_backend()
    
    def _initialize_backend(self):
        """Initialize storage backend based on configuration"""
        try:
            # Check configuration to determine backend
            storage_type = config("STORAGE_TYPE", default="auto").lower()
            
            if storage_type == "local":
                self._init_local_backend()
            elif storage_type == "s3":
                self._init_s3_backend()
            elif storage_type == "auto":
                # Try S3 first, fallback to local
                if self._try_s3_backend():
                    logger.info("Auto-detected S3 storage backend")
                else:
                    self._init_local_backend()
                    logger.info("Auto-selected local storage backend")
            else:
                raise ValueError(f"Unknown storage type: {storage_type}")
                
        except Exception as e:
            logger.error(f"Failed to initialize storage backend: {str(e)}")
            # Fallback to local storage
            self._init_local_backend()
            logger.info("Fallback to local storage backend")
    
    def _try_s3_backend(self) -> bool:
        """Try to initialize S3 backend, return True if successful"""
        try:
            access_key_id = config("ACCESS_KEY_ID", default="")
            secret_access_key = config("SECRET_ACCESS_KEY", default="")
            recordings_bucket = config("S3_BUCKET_NAME", default="")
            layouts_bucket = config("S3_LEARNER_BUCKET_NAME", default="")
            region = config("AWS_REGION", default="us-east-1")
            
            if not all([access_key_id, secret_access_key, recordings_bucket]):
                return False
            
            self.backend = S3StorageBackend(
                access_key_id=access_key_id,
                secret_access_key=secret_access_key,
                recordings_bucket=recordings_bucket,
                layouts_bucket=layouts_bucket,
                region=region
            )
            return True
            
        except Exception as e:
            logger.warning(f"S3 backend initialization failed: {str(e)}")
            return False
    
    def _init_s3_backend(self):
        """Force initialize S3 backend"""
        if not self._try_s3_backend():
            raise RuntimeError("S3 backend could not be initialized. Check your configuration.")
    
    def _init_local_backend(self):
        """Initialize local storage backend"""
        recordings_path = config("LOCAL_STORAGE_RECORDINGS_PATH", default="storage/recordings")
        layouts_path = config("LOCAL_STORAGE_LAYOUTS_PATH", default="storage/layouts")
        
        self.backend = LocalStorageBackend(
            recordings_path=recordings_path,
            layouts_path=layouts_path
        )
    
    def get_backend_type(self) -> str:
        """Get the type of current backend"""
        if isinstance(self.backend, LocalStorageBackend):
            return "local"
        elif isinstance(self.backend, S3StorageBackend):
            return "s3"
        else:
            return "unknown"
    
    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about current backend"""
        if self.backend:
            return self.backend.get_backend_info()
        return {"error": "No backend initialized"}
    
    # Delegate all storage operations to the backend
    def save_recording_file(self, tutorial_section_id: str, filename: str, content: bytes) -> bool:
        return self.backend.save_recording_file(tutorial_section_id, filename, content) if self.backend else False
    
    def get_recording_file(self, tutorial_section_id: str, filename: str) -> Optional[bytes]:
        return self.backend.get_recording_file(tutorial_section_id, filename) if self.backend else None
    
    def list_recording_files(self, tutorial_section_id: str) -> List[str]:
        return self.backend.list_recording_files(tutorial_section_id) if self.backend else []
    
    def delete_recording_section(self, tutorial_section_id: str) -> bool:
        return self.backend.delete_recording_section(tutorial_section_id) if self.backend else False
    
    def copy_recording_section(self, source_id: str, dest_id: str) -> bool:
        return self.backend.copy_recording_section(source_id, dest_id) if self.backend else False
    
    def save_user_layout(self, user_id: int, tutorial_id: str, role: str, layout_data: Dict[str, Any]) -> bool:
        return self.backend.save_user_layout(user_id, tutorial_id, role, layout_data) if self.backend else False
    
    def get_user_layout(self, user_id: int, tutorial_id: str, role: str) -> Optional[Dict[str, Any]]:
        return self.backend.get_user_layout(user_id, tutorial_id, role) if self.backend else None
    
    def get_file_url(self, tutorial_section_id: str, filename: str, expires_in: int = 3600) -> Optional[str]:
        return self.backend.get_file_url(tutorial_section_id, filename, expires_in) if self.backend else None

# Global storage manager instance
_storage_manager: Optional[StorageManager] = None

def get_storage_manager() -> StorageManager:
    """Get or create global storage manager instance"""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager

def reset_storage_manager():
    """Reset global storage manager (useful for testing)"""
    global _storage_manager
    _storage_manager = None