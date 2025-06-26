"""
Main Flask Application

Entry point for the modularized Flutter server application.
Clean, simple orchestration using standardized service registry.
"""

import os
import time
import socket
import subprocess
import logging
from flask import Flask, render_template, jsonify
from flask_cors import CORS

from .services import ServiceRegistry, setup_recovery_context, log_startup_info, log_ready_info


# Custom logging filter to hide non-API requests
class APIOnlyFilter(logging.Filter):
    def filter(self, record):
        # Only show requests that start with /api/ or are error/warning messages
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # Hide successful requests that don't start with /api/
            if '" 200 -' in message and '/api/' not in message:
                return False
            # Show error responses and API requests
            return True
        return True


def print_startup_banner():
    """Print startup banner"""
    print("🚀 Flutter Server (Modular)")
    print("==========================")
    print("Starting Flask server on port 5000...")
    print("Auto-checking Flutter status and starting if needed...")
    print("Access the web interface at: http://localhost:5000")
    print()


def create_flask_app() -> Flask:
    """Create and configure the Flask application"""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    CORS(app)
    
    # Apply logging filter
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(APIOnlyFilter())
    
    # Register template routes
    register_template_routes(app)
    
    return app


def register_template_routes(app: Flask):
    """Register template routes for web interface"""
    
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/editor')
    def editor():
        return render_template('editor.html')

    @app.route('/project')
    def project_overview():
        return render_template('project.html')

    @app.route('/chat')
    def chat():
        return render_template('chat.html')


def register_routers(app: Flask, registry: ServiceRegistry):
    """Register all API routers with dependency injection"""
    
    # Import all routers
    from .flutter_management import router as flutter_router
    from .hot_reload import router as hot_reload_router
    from .code_modification import router as code_mod_router
    from .chat import router as chat_router
    from .static_files import router as static_router
    from .project import router as project_router
    
    # List of router modules for dependency injection
    router_modules = [
        flutter_router,
        hot_reload_router,
        code_mod_router,
        chat_router,
        project_router
    ]
    
    # Inject dependencies into all routers
    registry.inject_dependencies(router_modules)
    
    # Register all blueprints
    app.register_blueprint(flutter_router.flutter_bp)
    app.register_blueprint(hot_reload_router.hot_reload_bp)
    app.register_blueprint(code_mod_router.code_modification_bp)
    app.register_blueprint(chat_router.chat_bp)
    app.register_blueprint(project_router.project_bp)
    app.register_blueprint(static_router.static_files_bp)
    
    # Register special API routes
    register_logs_api(app, registry)


def register_logs_api(app: Flask, registry: ServiceRegistry):
    """Register the special logs API route"""
    
    @app.route('/api/logs', methods=['GET'])
    def get_logs():
        """Get comprehensive logs including Flutter and monitoring logs"""
        try:
            flutter_manager = registry.get('flutter_manager')
            monitoring_available = registry.get('monitoring_available')
            
            monitoring_logs = []
            if monitoring_available and registry.has('monitoring'):
                try:
                    monitoring = registry.get('monitoring')
                    logger = monitoring['logger']
                    advanced_logs = logger.get_logs(limit=100)
                    
                    for log_entry in advanced_logs:
                        monitoring_logs.append({
                            "timestamp": log_entry.timestamp,
                            "level": log_entry.level.value,
                            "category": log_entry.category.value,
                            "message": log_entry.message,
                            "context": log_entry.context,
                            "request_id": log_entry.request_id,
                            "duration_ms": log_entry.duration_ms,
                            "tags": log_entry.tags
                        })
                except Exception as e:
                    print(f"Error getting advanced logs: {e}")
            
            # Combine Flutter logs with monitoring logs
            all_logs = []
            
            # Add Flutter development server logs
            for flutter_log in flutter_manager.output_buffer:
                all_logs.append(flutter_log)
            
            # Add monitoring logs 
            for monitoring_log in monitoring_logs:
                all_logs.append(monitoring_log)
            
            return jsonify({
                "logs": all_logs,
                "flutter_logs": flutter_manager.output_buffer,
                "monitoring_logs": monitoring_logs,
                "running": flutter_manager.is_running,
                "ready": flutter_manager.ready,
                "process_alive": flutter_manager.flutter_process.poll() is None if flutter_manager.flutter_process else False
            })
            
        except Exception as e:
            # Fallback to just Flutter logs if monitoring logs fail
            flutter_manager = registry.get('flutter_manager')
            return jsonify({
                "logs": flutter_manager.output_buffer,
                "flutter_logs": flutter_manager.output_buffer,
                "monitoring_logs": [],
                "running": flutter_manager.is_running,
                "ready": flutter_manager.ready,
                "process_alive": flutter_manager.flutter_process.poll() is None if flutter_manager.flutter_process else False,
                "error": f"Failed to get monitoring logs: {str(e)}"
            })


def check_and_start_flutter(registry: ServiceRegistry):
    """Check Flutter status and start if not running"""
    flutter_manager = registry.get('flutter_manager')
    monitoring_available = registry.get('monitoring_available')
    
    try:
        # First check if Flutter is already running by checking the manager status
        if flutter_manager.is_running and flutter_manager.flutter_process:
            if flutter_manager.flutter_process.poll() is None:
                print("✅ Flutter is already running")
                return
            else:
                print("🔄 Flutter process was terminated, restarting...")
                flutter_manager.is_running = False
                flutter_manager.flutter_process = None
        
        # Check if port 8080 is in use by another process
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        port_in_use = sock.connect_ex(('localhost', 8080)) == 0
        sock.close()
        
        if port_in_use:
            print("📡 Port 8080 is in use - checking if it's our Flutter process...")
            # If port is in use but our manager says Flutter isn't running,
            # it might be from a previous session or another process
            if not flutter_manager.is_running:
                print("⚠️ Port 8080 in use by unknown process - Flutter may already be running externally")
                return
        
        print("🚀 Starting Flutter development server...")
        result = flutter_manager.start_flutter()
        
        if result.get('error'):
            print(f"❌ Flutter start failed: {result['error']}")
            print("💡 You can start Flutter manually via the web interface")
            
            if monitoring_available and registry.has('monitoring'):
                monitoring = registry.get('monitoring')
                logger = monitoring['logger']
                try:
                    from src.utils.advanced_logger import LogCategory
                    logger.warn(LogCategory.FLUTTER, "Flutter auto-start failed",
                               context={
                                   "error": result['error'],
                                   "manual_start_available": True
                               },
                               tags=["startup", "flutter", "failed"])
                except Exception as e:
                    print(f"Warning: Could not log Flutter failure: {e}")
        else:
            print(f"✅ Flutter started successfully (PID: {result.get('pid')})")
            print("⏳ Waiting for Flutter to initialize...")
            
            if monitoring_available and registry.has('monitoring'):
                monitoring = registry.get('monitoring')
                logger = monitoring['logger']
                try:
                    from src.utils.advanced_logger import LogCategory
                    logger.info(LogCategory.FLUTTER, "Flutter development server started",
                               context={
                                   "pid": result.get('pid'),
                                   "port": 8080,
                                   "dev_mode": flutter_manager.dev_mode
                               },
                               tags=["startup", "flutter", "success"])
                except Exception as e:
                    print(f"Warning: Could not log Flutter success: {e}")
            
            # Give Flutter time to start up
            time.sleep(3)
            print("🎯 Flutter should now be accessible at http://localhost:8080")
            
    except Exception as e:
        print(f"❌ Error checking/starting Flutter: {str(e)}")
        print("💡 You can start Flutter manually via the web interface")
        
        if monitoring_available and registry.has('monitoring'):
            monitoring = registry.get('monitoring')
            error_analyzer = monitoring['error_analyzer']
            error_analyzer.analyze_error(
                component="flutter_startup",
                operation="check_and_start_flutter",
                message=str(e),
                context={
                    "manual_start_available": True,
                    "port_checked": True
                }
            )


def create_app():
    """Create the application with service registry (for compatibility)"""
    registry = ServiceRegistry()
    
    if not registry.initialize_all():
        return None, None, False
    
    app = create_flask_app()
    register_routers(app, registry)
    
    # Set up recovery context
    setup_recovery_context(registry)
    
    flutter_manager = registry.get('flutter_manager')
    monitoring_available = registry.get('monitoring_available')
    
    return app, flutter_manager, monitoring_available


def main():
    """Main entry point - simple and clean"""
    print_startup_banner()
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # 1. Create service registry and initialize all services
    registry = ServiceRegistry()
    if not registry.initialize_all():
        print("❌ Failed to initialize services")
        return 1
    
    # 2. Create and configure Flask app
    app = create_flask_app()
    
    # 3. Register all routers with dependency injection
    register_routers(app, registry)
    
    # 4. Set up recovery context
    setup_recovery_context(registry)
    
    # 5. Log startup info
    log_startup_info(registry)
    
    # 6. Check and start Flutter if needed
    check_and_start_flutter(registry)
    
    # 7. Log ready info
    log_ready_info(registry)
    
    # 8. Display final status
    flutter_manager = registry.get('flutter_manager')
    flutter_status = "🟢 Running" if flutter_manager.is_running else "🔴 Not Running"
    print(f"📊 Final Status - Flutter: {flutter_status}")
    print("🚀 All systems ready!")
    
    # 9. Start server
    app.run(host='0.0.0.0', port=5000, debug=True)


if __name__ == '__main__':
    main()