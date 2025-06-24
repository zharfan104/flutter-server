"""
Project Router

API endpoints for project structure and file operations
"""

from flask import Blueprint, jsonify, request
import os
from pathlib import Path
from typing import Dict, Any, List

# Create blueprint for project routes
project_bp = Blueprint('project', __name__, url_prefix='/api')

# Dependencies will be injected
flutter_manager = None


def set_flutter_manager(manager):
    """Set the Flutter manager instance"""
    global flutter_manager
    flutter_manager = manager


def set_dependencies(**services):
    """Standardized dependency injection"""
    if 'flutter_manager' in services:
        set_flutter_manager(services['flutter_manager'])


@project_bp.route('/file/<path:file_path>', methods=['GET'])
def get_file(file_path):
    """Get file contents for editor"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        full_path = os.path.join(flutter_manager.project_path, file_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                "status": "success",
                "content": content,
                "path": file_path
            })
        else:
            return jsonify({"status": "error", "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@project_bp.route('/file/<path:file_path>', methods=['PUT'])
def save_file(file_path):
    """Save file contents from editor"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        data = request.json
        content = data.get('content', '')
        auto_reload = data.get('auto_reload', True)
        
        result = flutter_manager.update_file(file_path, content)
        
        if auto_reload and flutter_manager.is_running and file_path.endswith('.dart'):
            import time
            time.sleep(0.5)
            reload_result = flutter_manager.hot_reload()
            result['reload'] = reload_result
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@project_bp.route('/file-tree', methods=['GET'])
def get_file_tree():
    """Get project file tree structure for editor"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        def build_tree(directory_path, relative_path=""):
            """Recursively build file tree structure"""
            items = []
            
            try:
                for item in sorted(os.listdir(directory_path)):
                    if item.startswith('.'):  # Skip hidden files
                        continue
                        
                    item_path = os.path.join(directory_path, item)
                    relative_item_path = os.path.join(relative_path, item) if relative_path else item
                    
                    if os.path.isdir(item_path):
                        # Skip certain directories
                        if item in ['build', '.dart_tool', '.git', 'node_modules', '.flutter-plugins-dependencies']:
                            continue
                            
                        children = build_tree(item_path, relative_item_path)
                        if children:  # Only include directories that have children
                            items.append({
                                'name': item,
                                'type': 'folder',
                                'path': relative_item_path,
                                'children': children
                            })
                    else:
                        # Only include certain file types
                        if item.endswith(('.dart', '.yaml', '.yml', '.md', '.json', '.xml', '.gradle', '.kt', '.swift')):
                            items.append({
                                'name': item,
                                'type': 'file',
                                'path': relative_item_path.replace(os.sep, '/')
                            })
            except PermissionError:
                # Skip directories we can't read
                pass
                
            return items
        
        project_path = flutter_manager.project_path
        file_tree = build_tree(project_path)
        
        return jsonify({
            "status": "success",
            "file_tree": file_tree
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e)
        }), 500


@project_bp.route('/create-file', methods=['POST'])
def create_file():
    """Create a new file in the project"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        data = request.json
        file_path = data.get('file_path', '')
        content = data.get('content', '')
        
        if not file_path:
            return jsonify({"error": "File path is required"}), 400
        
        full_path = os.path.join(flutter_manager.project_path, file_path)
        
        # Check if file already exists
        if os.path.exists(full_path):
            return jsonify({"error": "File already exists"}), 409
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Create file
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            "status": "success",
            "message": f"File created: {file_path}",
            "path": file_path
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@project_bp.route('/delete-file', methods=['DELETE'])
def delete_file():
    """Delete a file from the project"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        data = request.json
        file_path = data.get('file_path', '')
        
        if not file_path:
            return jsonify({"error": "File path is required"}), 400
        
        full_path = os.path.join(flutter_manager.project_path, file_path)
        
        # Check if file exists
        if not os.path.exists(full_path):
            return jsonify({"error": "File not found"}), 404
        
        # Delete file
        os.remove(full_path)
        
        return jsonify({
            "status": "success",
            "message": f"File deleted: {file_path}"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@project_bp.route('/git-pull', methods=['POST'])
def git_pull():
    """Pull latest changes from git repository"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        import subprocess
        
        # Run git pull in project directory
        result = subprocess.run(
            ["git", "pull"],
            cwd=flutter_manager.project_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Trigger hot reload after successful pull
            if flutter_manager.is_running:
                import time
                time.sleep(1)
                reload_result = flutter_manager.hot_reload()
                
                return jsonify({
                    "status": "success",
                    "message": "Git pull successful",
                    "git_output": result.stdout,
                    "reload_result": reload_result
                })
            else:
                return jsonify({
                    "status": "success",
                    "message": "Git pull successful",
                    "git_output": result.stdout
                })
        else:
            return jsonify({
                "status": "error",
                "error": "Git pull failed",
                "git_output": result.stderr
            }), 400
            
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Git pull timed out"}), 408
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@project_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for project service"""
    try:
        services_available = {
            "flutter_manager": flutter_manager is not None,
            "project_exists": False,
            "project_readable": False,
            "git_available": False
        }
        
        if flutter_manager:
            services_available["project_exists"] = os.path.exists(flutter_manager.project_path)
            services_available["project_readable"] = os.access(flutter_manager.project_path, os.R_OK)
            
            # Check if git is available
            try:
                import subprocess
                subprocess.run(["git", "--version"], capture_output=True, timeout=5)
                services_available["git_available"] = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                pass
        
        all_healthy = all(services_available.values())
        
        return jsonify({
            "healthy": all_healthy,
            "services": services_available,
            "service": "project"
        })
    
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e),
            "service": "project"
        }), 500