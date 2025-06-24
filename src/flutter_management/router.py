"""
Flutter Management Router

API endpoints for Flutter process management operations
"""

from flask import Blueprint, jsonify, request
from .service import FlutterManager
from .exceptions import FlutterManagementError

# Create blueprint for Flutter management routes
flutter_bp = Blueprint('flutter', __name__, url_prefix='/api')

# Initialize Flutter manager instance (will be injected via dependencies later)
flutter_manager = None


def set_flutter_manager(manager: FlutterManager):
    """Set the Flutter manager instance"""
    global flutter_manager
    flutter_manager = manager


def set_dependencies(**services):
    """Standardized dependency injection"""
    if 'flutter_manager' in services:
        set_flutter_manager(services['flutter_manager'])


@flutter_bp.route('/status', methods=['GET'])
def get_status():
    """Get Flutter process status"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        status = flutter_manager.get_status()
        return jsonify(status)
    
    except FlutterManagementError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get status: {str(e)}"}), 500


@flutter_bp.route('/start', methods=['POST'])
def start_flutter():
    """Start Flutter development server"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        result = flutter_manager.start_flutter()
        
        if "error" in result:
            return jsonify(result), 400
        
        return jsonify(result)
    
    except FlutterManagementError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to start Flutter: {str(e)}"}), 500


@flutter_bp.route('/stop', methods=['POST'])
def stop_flutter():
    """Stop Flutter development server"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        # TODO: Implement stop functionality in FlutterManager
        if flutter_manager.flutter_process:
            flutter_manager.flutter_process.terminate()
            flutter_manager.is_running = False
            flutter_manager.ready = False
            return jsonify({"status": "stopped", "message": "Flutter server stopped"})
        else:
            return jsonify({"status": "not_running", "message": "Flutter server was not running"})
    
    except FlutterManagementError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to stop Flutter: {str(e)}"}), 500


@flutter_bp.route('/restart', methods=['POST'])
def restart_flutter():
    """Restart Flutter development server"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        # Stop if running
        if flutter_manager.flutter_process:
            flutter_manager.flutter_process.terminate()
            flutter_manager.is_running = False
            flutter_manager.ready = False
        
        # Start again
        result = flutter_manager.start_flutter()
        
        if "error" in result:
            return jsonify(result), 400
        
        result["message"] = "Flutter server restarted"
        return jsonify(result)
    
    except FlutterManagementError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to restart Flutter: {str(e)}"}), 500


@flutter_bp.route('/logs', methods=['GET'])
def get_flutter_logs():
    """Get Flutter development server logs"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        # Get query parameters
        limit = request.args.get('limit', type=int)
        offset = request.args.get('offset', type=int, default=0)
        
        logs = flutter_manager.output_buffer
        
        # Apply offset and limit
        if offset:
            logs = logs[offset:]
        if limit:
            logs = logs[:limit]
        
        return jsonify({
            "status": "success",
            "logs": logs,
            "total_lines": len(flutter_manager.output_buffer),
            "running": flutter_manager.is_running,
            "ready": flutter_manager.ready
        })
    
    except FlutterManagementError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Failed to get logs: {str(e)}"}), 500


@flutter_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Flutter management"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        status = flutter_manager.get_status()
        
        health_status = {
            "healthy": status.get("running", False),
            "ready": status.get("ready", False),
            "process_id": status.get("pid"),
            "service": "flutter_management"
        }
        
        return jsonify(health_status)
    
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e),
            "service": "flutter_management"
        }), 500