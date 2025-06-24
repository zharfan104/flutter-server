"""
Hot Reload Router

API endpoints for Flutter hot reload operations
"""

from flask import Blueprint, jsonify, request
from typing import Optional

# Create blueprint for hot reload routes
hot_reload_bp = Blueprint('hot_reload', __name__, url_prefix='/api')

# Flutter manager will be injected
flutter_manager = None


def set_flutter_manager(manager):
    """Set the Flutter manager instance"""
    global flutter_manager
    flutter_manager = manager


def set_dependencies(**services):
    """Standardized dependency injection"""
    if 'flutter_manager' in services:
        set_flutter_manager(services['flutter_manager'])


@hot_reload_bp.route('/hot-reload', methods=['POST'])
def trigger_hot_reload():
    """Trigger Flutter hot reload"""
    try:
        print("🔄 [HOT_RELOAD] Hot reload endpoint triggered")
        
        if not flutter_manager:
            print("❌ [HOT_RELOAD] Flutter manager not initialized")
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        print("✅ [HOT_RELOAD] Flutter manager available")
        
        # Get request parameters
        data = request.json or {}
        with_error_recovery = data.get('with_error_recovery', True)
        max_retries = data.get('max_retries', 3)
        
        print(f"📋 [HOT_RELOAD] Request parameters: with_error_recovery={with_error_recovery}, max_retries={max_retries}")
        
        # Trigger hot reload
        print("🚀 [HOT_RELOAD] Triggering Flutter hot reload...")
        result = flutter_manager.hot_reload(
            with_error_recovery=with_error_recovery,
            max_retries=max_retries
        )
        
        print(f"📊 [HOT_RELOAD] Hot reload result: {result}")
        
        if result.get("error"):
            print(f"❌ [HOT_RELOAD] Hot reload failed with error: {result.get('error')}")
            return jsonify(result), 400
        
        print("✅ [HOT_RELOAD] Hot reload completed successfully")
        return jsonify(result)
    
    except Exception as e:
        print(f"💥 [HOT_RELOAD] Exception during hot reload: {str(e)}")
        return jsonify({"error": f"Hot reload failed: {str(e)}"}), 500


@hot_reload_bp.route('/hot-restart', methods=['POST'])
def trigger_hot_restart():
    """Trigger Flutter hot restart"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        # Check if Flutter is running
        if not flutter_manager.flutter_process or not flutter_manager.is_running:
            return jsonify({"error": "Flutter not running"}), 400
        
        # Send 'R' command for hot restart
        try:
            flutter_manager.flutter_process.stdin.write('R\n')
            flutter_manager.flutter_process.stdin.flush()
            
            return jsonify({
                "status": "hot_restarted",
                "success": True,
                "message": "Hot restart triggered successfully"
            })
        
        except Exception as e:
            return jsonify({"error": f"Hot restart failed: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"error": f"Hot restart failed: {str(e)}"}), 500


@hot_reload_bp.route('/recovery-status', methods=['GET'])
def get_recovery_status():
    """Get hot reload error recovery status"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        # Get recovery context if available
        has_recovery_context = (
            hasattr(flutter_manager, '_chat_manager') and 
            hasattr(flutter_manager, '_recovery_conversation_id')
        )
        
        return jsonify({
            "recovery_enabled": has_recovery_context,
            "chat_manager_available": hasattr(flutter_manager, '_chat_manager'),
            "conversation_id": getattr(flutter_manager, '_recovery_conversation_id', None)
        })
    
    except Exception as e:
        return jsonify({"error": f"Failed to get recovery status: {str(e)}"}), 500


@hot_reload_bp.route('/set-recovery-context', methods=['POST'])
def set_recovery_context():
    """Set chat context for hot reload error recovery"""
    try:
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not initialized"}), 500
        
        data = request.json or {}
        conversation_id = data.get('conversation_id')
        
        if not conversation_id:
            return jsonify({"error": "conversation_id is required"}), 400
        
        # Import chat manager (will be properly dependency injected later)
        try:
            from src.chat.services.chat_manager import chat_manager
            flutter_manager.set_recovery_chat_context(chat_manager, conversation_id)
            
            return jsonify({
                "status": "success",
                "message": "Recovery context set successfully",
                "conversation_id": conversation_id
            })
        
        except ImportError as e:
            return jsonify({"error": f"Chat manager not available: {str(e)}"}), 500
    
    except Exception as e:
        return jsonify({"error": f"Failed to set recovery context: {str(e)}"}), 500


@hot_reload_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for hot reload service"""
    try:
        if not flutter_manager:
            return jsonify({
                "healthy": False,
                "error": "Flutter manager not initialized",
                "service": "hot_reload"
            }), 500
        
        # Check if Flutter is ready for hot reload
        can_hot_reload = (
            flutter_manager.flutter_process is not None and
            flutter_manager.is_running and
            flutter_manager.ready
        )
        
        return jsonify({
            "healthy": True,
            "can_hot_reload": can_hot_reload,
            "flutter_running": flutter_manager.is_running,
            "flutter_ready": flutter_manager.ready,
            "service": "hot_reload"
        })
    
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e),
            "service": "hot_reload"
        }), 500