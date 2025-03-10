"""
Grid backup and restore functionality for Infoblox Mock Server
"""

import os
import json
import logging
import threading
import time
import zipfile
import shutil
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

# Backup and restore tasks
backup_tasks = {}
restore_tasks = {}

class BackupManager:
    """Manager for grid backup and restore operations"""
    
    @staticmethod
    def create_backup(name, backup_type="full", include_members=None, comment=None):
        """Create a new backup"""
        from infoblox_mock.db import export_db
        
        # Generate a unique ID
        backup_id = str(uuid.uuid4())
        
        # Create backup directory if it doesn't exist
        backup_dir = os.path.join('data', 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create backup metadata
        backup_data = {
            'id': backup_id,
            'name': name,
            'type': backup_type,
            'include_members': include_members or ['all'],
            'comment': comment,
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'file_path': None,
            'file_size': 0,
            'error': None
        }
        
        # Add to tracking
        backup_tasks[backup_id] = backup_data
        
        # Run backup in a separate thread
        def run_backup():
            try:
                # Update status
                backup_data['status'] = 'running'
                
                # Get database content
                db_content = export_db()
                
                # Create a timestamped filename
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                filename = f"{name.replace(' ', '_')}_{timestamp}.zip"
                filepath = os.path.join(backup_dir, filename)
                
                # Create a temporary directory for backup files
                temp_dir = os.path.join('data', 'temp', backup_id)
                os.makedirs(temp_dir, exist_ok=True)
                
                # Write DB content to a file
                db_file = os.path.join(temp_dir, 'db.json')
                with open(db_file, 'w') as f:
                    json.dump(db_content, f, indent=2)
                
                # Write metadata to a file
                meta_file = os.path.join(temp_dir, 'metadata.json')
                with open(meta_file, 'w') as f:
                    json.dump({
                        'backup_id': backup_id,
                        'name': name,
                        'type': backup_type,
                        'include_members': include_members or ['all'],
                        'comment': comment,
                        'created': datetime.now().isoformat()
                    }, f, indent=2)
                
                # Create a zip file
                with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add DB file
                    zipf.write(db_file, arcname='db.json')
                    # Add metadata file
                    zipf.write(meta_file, arcname='metadata.json')
                
                # Get file size
                file_size = os.path.getsize(filepath)
                
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Update backup data
                backup_data['status'] = 'completed'
                backup_data['end_time'] = datetime.now().isoformat()
                backup_data['file_path'] = filepath
                backup_data['file_size'] = file_size
                
                logger.info(f"Backup completed: {name} ({backup_id})")
            
            except Exception as e:
                logger.error(f"Error creating backup {name} ({backup_id}): {str(e)}")
                backup_data['status'] = 'failed'
                backup_data['end_time'] = datetime.now().isoformat()
                backup_data['error'] = str(e)
        
        # Start backup thread
        thread = threading.Thread(target=run_backup)
        thread.daemon = True
        thread.start()
        
        return backup_id
    
    @staticmethod
    def get_backup(backup_id):
        """Get a backup by ID"""
        return backup_tasks.get(backup_id)
    
    @staticmethod
    def get_all_backups():
        """Get all backups"""
        return backup_tasks
    
    @staticmethod
    def restore_backup(backup_id, include_members=None):
        """Restore from a backup"""
        # Check if backup exists
        backup = backup_tasks.get(backup_id)
        if not backup:
            logger.warning(f"Backup not found for restore: {backup_id}")
            return None, "Backup not found"
        
        # Check if backup is completed
        if backup['status'] != 'completed':
            logger.warning(f"Cannot restore from incomplete backup: {backup_id}")
            return None, "Backup is not completed"
        
        # Check if backup file exists
        if not backup['file_path'] or not os.path.exists(backup['file_path']):
            logger.warning(f"Backup file not found: {backup['file_path']}")
            return None, "Backup file not found"
        
        # Generate a unique ID
        restore_id = str(uuid.uuid4())
        
        # Create restore metadata
        restore_data = {
            'id': restore_id,
            'backup_id': backup_id,
            'backup_name': backup['name'],
            'include_members': include_members or backup['include_members'],
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'end_time': None,
            'error': None
        }
        
        # Add to tracking
        restore_tasks[restore_id] = restore_data
        
        # Run restore in a separate thread
        def run_restore():
            try:
                # Update status
                restore_data['status'] = 'running'
                
                # Create a temporary directory for extracted files
                temp_dir = os.path.join('data', 'temp', restore_id)
                os.makedirs(temp_dir, exist_ok=True)
                
                # Extract the backup zip
                with zipfile.ZipFile(backup['file_path'], 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                # Read the database content
                db_file = os.path.join(temp_dir, 'db.json')
                with open(db_file, 'r') as f:
                    db_content = json.load(f)
                
                # Restore the database
                from infoblox_mock.db import db, db_lock
                
                with db_lock:
                    # Replace the entire database
                    for key, value in db_content.items():
                        db[key] = value
                
                # Clean up temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Simulate delay for restarting services
                time.sleep(5)
                
                # Update restore data
                restore_data['status'] = 'completed'
                restore_data['end_time'] = datetime.now().isoformat()
                
                logger.info(f"Restore completed: {backup['name']} ({backup_id})")
                
                # Send webhook notification
                from infoblox_mock.webhooks import webhook_manager
                webhook_manager.notify_webhook('grid:restore', {
                    'restore_id': restore_id,
                    'backup_id': backup_id,
                    'backup_name': backup['name'],
                    'status': 'completed'
                })
            
            except Exception as e:
                logger.error(f"Error restoring backup {backup['name']} ({backup_id}): {str(e)}")
                restore_data['status'] = 'failed'
                restore_data['end_time'] = datetime.now().isoformat()
                restore_data['error'] = str(e)
                
                # Send webhook notification for failure
                from infoblox_mock.webhooks import webhook_manager
                webhook_manager.notify_webhook('grid:restore', {
                    'restore_id': restore_id,
                    'backup_id': backup_id,
                    'backup_name': backup['name'],
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Start restore thread
        thread = threading.Thread(target=run_restore)
        thread.daemon = True
        thread.start()
        
        return restore_id, None
    
    @staticmethod
    def get_restore(restore_id):
        """Get a restore task by ID"""
        return restore_tasks.get(restore_id)
    
    @staticmethod
    def get_all_restores():
        """Get all restore tasks"""
        return restore_tasks