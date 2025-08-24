"""
File Server Routes - Handles file serving for local storage backend
"""

import logging
from flask import Response, request, jsonify, abort
from werkzeug.utils import secure_filename
from tutorial.utils.storage_backend import get_storage_manager

logger = logging.getLogger(__name__)

def _get_max_upload_size() -> int:
    """Get maximum upload size in bytes"""
    from decouple import config
    max_size_mb = config("MAX_UPLOAD_SIZE_MB", default=100, cast=int)
    return max_size_mb * 1024 * 1024

def _is_allowed_file_type(filename: str) -> bool:
    """Check if file type is allowed"""
    if '.' not in filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    allowed_extensions = _get_allowed_extensions()
    return extension in allowed_extensions

def _get_allowed_extensions() -> set:
    """Get set of allowed file extensions"""
    from decouple import config
    extensions_str = config("ALLOWED_FILE_EXTENSIONS", default="wav,json,txt,md,mp3,png,jpg,jpeg")
    return set(ext.strip().lower() for ext in extensions_str.split(','))

def create_file_upload_handler():
    """Create a file upload handler for the storage backend"""
    
    def handle_file_upload(tutorial_section_id: str, filename: str, file_data: bytes) -> dict:
        """Handle file upload with proper error handling and validation"""
        try:
            storage = get_storage_manager()
            
            # Validate file size
            max_size = _get_max_upload_size()
            if len(file_data) > max_size:
                return {
                    'success': False, 
                    'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
                }
            
            # Validate file type
            if not _is_allowed_file_type(filename):
                return {
                    'success': False, 
                    'error': f'File type not allowed: {filename}'
                }
            
            # Save the file
            result = storage.save_recording_file(tutorial_section_id, filename, file_data)
            
            return {'success': True, 'message': 'File uploaded successfully'}
            
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    return handle_file_upload

def register_file_routes(app):
    """Register file serving routes with Flask app"""
    
    @app.route('/api/files/<tutorial_section_id>/<filename>')
    def serve_recording_file(tutorial_section_id, filename):
        """Serve recording files for local storage backend with Range request support"""
        try:
            storage = get_storage_manager()
            
            # Only serve files for local backend
            if storage.get_backend_type() != 'local':
                abort(404, "File serving only available for local storage")
            
            # Validate and secure the filename
            secure_name = secure_filename(filename)
            if not secure_name or secure_name != filename:
                abort(400, "Invalid filename")
            
            # Get file content
            content = storage.get_recording_file(tutorial_section_id, filename)
            if content is None:
                abort(404, "File not found")
            
            # Determine content type based on file extension
            content_type = _get_content_type(filename)
            
            # Handle Range requests for audio seeking
            range_header = request.headers.get('Range')
            if range_header:
                # Parse Range header (e.g., "bytes=0-1023")
                if range_header.startswith('bytes='):
                    ranges = range_header[6:].split(',')[0]  # Take first range
                    if '-' in ranges:
                        start, end = ranges.split('-', 1)
                        start = int(start) if start else 0
                        end = int(end) if end else len(content) - 1
                        
                        # Ensure valid range
                        start = max(0, start)
                        end = min(len(content) - 1, end)
                        
                        if start <= end:
                            # Create partial content response
                            partial_content = content[start:end + 1]
                            response = Response(
                                partial_content,
                                status=206,  # Partial Content
                                mimetype=content_type,
                                headers={
                                    'Content-Range': f'bytes {start}-{end}/{len(content)}',
                                    'Accept-Ranges': 'bytes',
                                    'Content-Length': str(len(partial_content)),
                                    'Content-Disposition': f'inline; filename="{secure_name}"',
                                    'Cache-Control': 'public, max-age=3600',
                                    'Access-Control-Allow-Origin': '*',
                                }
                            )
                            logger.info(f"Served partial file: {tutorial_section_id}/{filename} (bytes {start}-{end})")
                            return response
            
            # Create full response (no Range header or invalid range)
            response = Response(
                content,
                mimetype=content_type,
                headers={
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(len(content)),
                    'Content-Disposition': f'inline; filename="{secure_name}"',
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*',
                }
            )
            
            logger.info(f"Served full file: {tutorial_section_id}/{filename} ({len(content)} bytes)")
            return response
            
        except Exception as e:
            logger.error(f"Error serving file {tutorial_section_id}/{filename}: {str(e)}")
            abort(500, "Internal server error")
    
    @app.route('/api/storage/info')
    def storage_info():
        """Get information about current storage backend"""
        try:
            storage = get_storage_manager()
            info = storage.get_backend_info()
            return jsonify(info)
            
        except Exception as e:
            logger.error(f"Error getting storage info: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/storage/health')
    def storage_health():
        """Health check for storage backend"""
        try:
            storage = get_storage_manager()
            backend_type = storage.get_backend_type()
            
            # Basic health check - try to list files for a dummy section
            test_files = storage.list_recording_files("health-check-dummy")
            
            return jsonify({
                "status": "healthy",
                "backend_type": backend_type,
                "timestamp": _get_timestamp()
            })
            
        except Exception as e:
            logger.error(f"Storage health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": _get_timestamp()
            }), 503

def _get_content_type(filename: str) -> str:
    """Get MIME content type based on file extension"""
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    content_types = {
        'wav': 'audio/wav',
        'mp3': 'audio/mpeg',
        'json': 'application/json',
        'txt': 'text/plain',
        'md': 'text/markdown',
        'html': 'text/html',
        'css': 'text/css',
        'js': 'application/javascript',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'pdf': 'application/pdf',
        'zip': 'application/zip',
    }
    
    return content_types.get(extension, 'application/octet-stream')

def _get_timestamp():
    """Get current timestamp in ISO format"""
    from datetime import datetime
    return datetime.utcnow().isoformat() + 'Z'

def create_file_upload_handler():
    """Create a file upload handler for the storage backend"""
    
    def handle_file_upload(tutorial_section_id: str, filename: str, file_data: bytes) -> dict:
        """Handle file upload with proper error handling and validation"""
        try:
            storage = get_storage_manager()
            
            # Validate file size
            max_size = _get_max_upload_size()
            if len(file_data) > max_size:
                return {
                    'success': False,
                    'error': f'File too large. Maximum size: {max_size // (1024*1024)}MB'
                }
            
            # Validate file type
            if not _is_allowed_file_type(filename):
                return {
                    'success': False,
                    'error': f'File type not allowed. Allowed types: {_get_allowed_extensions()}'
                }
            
            # Save file
            success = storage.save_recording_file(tutorial_section_id, filename, file_data)
            
            if success:
                # Get file URL for response
                file_url = storage.get_file_url(tutorial_section_id, filename)
                return {
                    'success': True,
                    'file_url': file_url,
                    'backend_type': storage.get_backend_type(),
                    'file_size': len(file_data)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save file'
                }
                
        except Exception as e:
            logger.error(f"File upload error: {str(e)}")
            return {
                'success': False,
                'error': 'Internal server error'
            }
    
    return handle_file_upload

def _get_max_upload_size() -> int:
    """Get maximum upload size in bytes"""
    from decouple import config
    max_size_mb = config("MAX_UPLOAD_SIZE_MB", default=100, cast=int)
    return max_size_mb * 1024 * 1024

def _is_allowed_file_type(filename: str) -> bool:
    """Check if file type is allowed"""
    if '.' not in filename:
        return False
    
    extension = filename.lower().split('.')[-1]
    allowed_extensions = _get_allowed_extensions()
    return extension in allowed_extensions

def _get_allowed_extensions() -> set:
    """Get set of allowed file extensions"""
    from decouple import config
    extensions_str = config("ALLOWED_FILE_EXTENSIONS", default="wav,json,txt,md,mp3,png,jpg,jpeg")
    return set(ext.strip().lower() for ext in extensions_str.split(','))

# Utility function for migration between backends
def migrate_between_backends(source_backend, dest_backend, tutorial_section_ids: list = None) -> dict:
    """
    Migrate data between storage backends
    
    Args:
        source_backend: Source StorageBackend instance
        dest_backend: Destination StorageBackend instance  
        tutorial_section_ids: List of section IDs to migrate (None = migrate all)
        
    Returns:
        dict: Migration results
    """
    results = {
        'migrated_sections': 0,
        'migrated_files': 0,
        'errors': [],
        'skipped': 0
    }
    
    try:
        # If no specific sections provided, we'd need to discover them
        # This is a simplified version - in practice, you'd query the database
        if tutorial_section_ids is None:
            logger.warning("No section IDs provided for migration")
            return results
        
        for section_id in tutorial_section_ids:
            try:
                # Get list of files in source
                files = source_backend.list_recording_files(section_id)
                if not files:
                    results['skipped'] += 1
                    continue
                
                section_migrated = True
                
                # Migrate each file
                for filename in files:
                    try:
                        content = source_backend.get_recording_file(section_id, filename)
                        if content is None:
                            results['errors'].append(f"Could not read {section_id}/{filename} from source")
                            section_migrated = False
                            continue
                        
                        success = dest_backend.save_recording_file(section_id, filename, content)
                        if success:
                            results['migrated_files'] += 1
                        else:
                            results['errors'].append(f"Could not save {section_id}/{filename} to destination")
                            section_migrated = False
                            
                    except Exception as e:
                        results['errors'].append(f"Error migrating {section_id}/{filename}: {str(e)}")
                        section_migrated = False
                
                if section_migrated:
                    results['migrated_sections'] += 1
                    
            except Exception as e:
                results['errors'].append(f"Error processing section {section_id}: {str(e)}")
        
        logger.info(f"Migration completed: {results['migrated_sections']} sections, {results['migrated_files']} files")
        return results
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        results['errors'].append(f"Migration failed: {str(e)}")
        return results