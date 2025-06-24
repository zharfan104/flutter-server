import os
import subprocess
import threading
import time
import json
import asyncio
from dataclasses import asdict
from flask import Flask, request, jsonify, Response, send_from_directory, render_template
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Custom logging filter to hide non-API requests (like Flutter package requests)
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

# Apply the filter to Werkzeug logger (Flask's request logger)
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addFilter(APIOnlyFilter())

class FlutterManager:
    def __init__(self):
        self.flutter_process = None
        self.project_path = os.path.join(os.getcwd(), "project")
        self.output_buffer = []
        self.is_running = False
        self.ready = False
        self.repo_url = os.environ.get('REPO_URL')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.dev_mode = os.environ.get('FLUTTER_DEV_MODE', 'fast').lower()  # fast, debug, profile
        
    def setup_project(self):
        """Clone repository or create Flutter project if no repo URL"""
        if self.repo_url:
            print(f"Cloning repository: {self.repo_url}")
            if not os.path.exists(self.project_path):
                # Clone with token if provided
                if self.github_token:
                    # Insert token into URL
                    auth_url = self.repo_url.replace('https://', f'https://{self.github_token}@')
                    subprocess.run(["git", "clone", auth_url, "project"], cwd=os.getcwd(), check=True)
                else:
                    subprocess.run(["git", "clone", self.repo_url, "project"], cwd=os.getcwd(), check=True)
                print("Repository cloned!")
            else:
                print("Repository already exists")
        else:
            # Fallback to creating generic Flutter project
            if not os.path.exists(self.project_path):
                print("Creating generic Flutter project...")
                subprocess.run(["flutter", "create", "project"], cwd=os.getcwd(), check=True)
                print("Flutter project created!")
    
    def start_flutter(self):
        """Start Flutter development server with hot reload"""
        if self.flutter_process:
            return {"error": "Flutter already running"}
        
        self.setup_project()
        
        # Start Flutter development server directly (no build step needed)
        print("Starting Flutter development server...")
        
        # Base command
        cmd = [
            "flutter", "run",
            "-d", "web-server",
            "--web-port=8080",
            "--web-hostname=0.0.0.0"
        ]
        
        # Add performance optimizations based on mode
        if self.dev_mode == 'fast':
            cmd.extend([
                "--dart-define=FLUTTER_WEB_USE_SKIA=false",  # Disable SKIA for faster loading
                "--dart-define=FLUTTER_WEB_USE_EXPERIMENTAL_CANVAS_TEXT=false",
                "--web-browser-flag=--disable-web-security",  # Development only
                "--web-browser-flag=--disable-features=VizDisplayCompositor",
                "--web-browser-flag=--disable-background-timer-throttling",
                "--web-browser-flag=--disable-renderer-backgrounding",
                "--web-browser-flag=--disable-backgrounding-occluded-windows"
            ])
        elif self.dev_mode == 'profile':
            cmd.extend([
                "--profile",
                "--web-renderer=canvaskit"  # Better performance in profile mode
            ])
        # debug mode uses default settings
        
        print(f"Starting Flutter dev server: {' '.join(cmd)}")
        
        try:
            self.flutter_process = subprocess.Popen(
                cmd,
                cwd=self.project_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=0
            )
            
            self.is_running = True
            self.ready = False  # Will be set to True when we detect "Web development server" in output
            
            # Start output reader thread
            threading.Thread(target=self._read_output, daemon=True).start()
            
            # Wait a moment for startup
            time.sleep(2)
            
            return {"status": "starting", "pid": self.flutter_process.pid}
            
        except Exception as e:
            return {"error": f"Failed to start Flutter dev server: {str(e)}"}
    
    def _read_output(self):
        """Read Flutter output continuously"""
        while self.is_running and self.flutter_process:
            try:
                line = self.flutter_process.stdout.readline()
                if line:
                    print(f"Flutter: {line.strip()}")
                    self.output_buffer.append(line.strip())
                    
                    if len(self.output_buffer) > 1000:
                        self.output_buffer = self.output_buffer[-500:]
                    
                    # Detect when Flutter dev server is ready
                    if any(phrase in line.lower() for phrase in [
                        "is being served at",
                        "running application at", 
                        "web development server is available at",
                        "http://",
                        "application started"
                    ]):
                        self.ready = True
                        print("Flutter development server is ready!")
                
                if self.flutter_process.poll() is not None:
                    print("Flutter process ended")
                    self.is_running = False
                    break
                    
            except Exception as e:
                print(f"Error reading output: {e}")
                time.sleep(0.1)
    
    
    def hot_reload(self, with_error_recovery=True, max_retries=3):
        """Trigger hot reload using Flutter's built-in hot reload with optional error recovery"""
        if not self.flutter_process or not self.is_running:
            return {"error": "Flutter not running"}
        
        try:
            print("Triggering Flutter hot reload...")
            
            # Clear recent output buffer to capture fresh reload output
            initial_buffer_length = len(self.output_buffer)
            
            # Send 'r' command to Flutter dev server for hot reload
            self.flutter_process.stdin.write('r\n')
            self.flutter_process.stdin.flush()
            
            print("✓ Hot reload command sent")
            
            # Wait for reload result if error recovery is enabled
            if with_error_recovery:
                reload_result = self._wait_for_reload_result(initial_buffer_length, max_retries)
                return reload_result
            else:
                return {
                    "status": "hot_reloaded",
                    "success": True,
                    "message": "Hot reload triggered successfully"
                }
        
        except Exception as e:
            print(f"Error during hot reload: {e}")
            return {"error": f"Hot reload failed: {str(e)}"}
    
    def _wait_for_reload_result(self, initial_buffer_length, max_retries):
        """Wait for hot reload result and trigger error recovery if needed"""
        import time
        import asyncio
        
        # Wait for Flutter to process the reload
        time.sleep(3)
        
        # Get new output since reload was triggered
        new_output = self.output_buffer[initial_buffer_length:]
        reload_output = '\n'.join(new_output)
        
        print(f"Hot reload output: {reload_output}")
        
        # Check for compilation errors
        error_patterns = [
            "Error:",
            "error:",
            "Try again after fixing",
            "failed to compile",
            "compilation failed",
            "Member not found:",
            "The method",
            "The getter",
            "The setter"
        ]
        
        # Check for success patterns that indicate successful compilation
        success_patterns = [
            "Restarted application in",
            "Hot reload completed",
            "Recompile complete",
            "Application finished"
        ]
        
        has_errors = any(pattern in reload_output for pattern in error_patterns)
        has_success = any(pattern in reload_output for pattern in success_patterns)
        
        # If we have both errors and success, check which came last
        if has_errors and has_success:
            # Find the last occurrence of each type
            last_error_pos = -1
            last_success_pos = -1
            
            for pattern in error_patterns:
                pos = reload_output.rfind(pattern)
                if pos > last_error_pos:
                    last_error_pos = pos
            
            for pattern in success_patterns:
                pos = reload_output.rfind(pattern)
                if pos > last_success_pos:
                    last_success_pos = pos
            
            # Only treat as error if the last error came after the last success
            has_errors = last_error_pos > last_success_pos
        
        # Also ignore errors if the output explicitly shows a successful restart
        if "Restarted application in" in reload_output and "ms" in reload_output:
            has_errors = False
        
        if has_errors:
            print("🔥 Compilation errors detected, starting AI recovery...")
            conversation_id = getattr(self, '_recovery_conversation_id', None)
            chat_manager = getattr(self, '_chat_manager', None)
            
            # Use the new HotReloadRecoveryService
            try:
                from code_modification.hot_reload_recovery import get_recovery_service
                
                recovery_service = get_recovery_service(
                    project_path=self.project_path,
                    flutter_manager=self,
                    chat_manager=chat_manager
                )
                
                # Run recovery in a separate thread to avoid event loop conflicts
                import threading
                import queue
                
                result_queue = queue.Queue()
                
                def run_recovery():
                    try:
                        recovery_result = asyncio.run(
                            recovery_service.attempt_recovery(
                                error_output=reload_output,
                                conversation_id=conversation_id,
                                max_retries=max_retries
                            )
                        )
                        result_queue.put(("success", recovery_result))
                    except Exception as e:
                        result_queue.put(("error", str(e)))
                
                # Start recovery in separate thread
                recovery_thread = threading.Thread(target=run_recovery)
                recovery_thread.start()
                recovery_thread.join(timeout=300)  # 5 minute timeout
                
                if recovery_thread.is_alive():
                    return {
                        "status": "error_recovery_timeout",
                        "success": False,
                        "message": "Error recovery timed out after 5 minutes",
                        "final_error": reload_output,
                        "attempts": 0
                    }
                
                # Get result from queue
                try:
                    result_type, result_data = result_queue.get_nowait()
                    if result_type == "success":
                        recovery_result = result_data
                        if recovery_result.success:
                            return {
                                "status": "error_recovery_success",
                                "success": True,
                                "message": f"Error recovered after {recovery_result.attempts} attempt(s)",
                                "attempts": recovery_result.attempts,
                                "fix_applied": recovery_result.fix_applied
                            }
                        else:
                            return {
                                "status": "error_recovery_failed",
                                "success": False,
                                "message": f"Error recovery failed after {recovery_result.attempts} attempts",
                                "final_error": recovery_result.final_error,
                                "attempts": recovery_result.attempts
                            }
                    else:
                        raise Exception(result_data)
                except queue.Empty:
                    return {
                        "status": "error_recovery_failed",
                        "success": False,
                        "message": "Error recovery failed - no result returned",
                        "final_error": reload_output,
                        "attempts": 0
                    }
                    
            except Exception as e:
                print(f"Error recovery service failed: {e}")
                return {
                    "status": "error_recovery_failed",
                    "success": False,
                    "message": f"Recovery service error: {str(e)}",
                    "final_error": reload_output,
                    "attempts": 0
                }
        else:
            success_patterns = [
                "Restarted application",
                "Hot reload performed",
                "Performing hot restart",
                "Hot reload.",
                "successfully"
            ]
            has_success = any(pattern in reload_output for pattern in success_patterns)
            
            if has_success:
                return {
                    "status": "hot_reloaded",
                    "success": True,
                    "message": "Hot reload completed successfully",
                    "output": reload_output
                }
            else:
                return {
                    "status": "hot_reloaded",
                    "success": True,
                    "message": "Hot reload triggered (status unclear)",
                    "output": reload_output
                }
    
    # Old error recovery methods removed - now using HotReloadRecoveryService
    
    def set_recovery_chat_context(self, chat_manager, conversation_id):
        """Set chat context for sending recovery progress messages"""
        self._chat_manager = chat_manager
        self._recovery_conversation_id = conversation_id
    
    def _send_recovery_message(self, conversation_id, message):
        """Send recovery progress message to chat"""
        if hasattr(self, '_chat_manager') and self._chat_manager:
            self._chat_manager.add_message(conversation_id, 'assistant', message)
    
    def trigger_hot_reload(self):
        """Alias for hot_reload() to match BuildPipelineService interface"""
        return self.hot_reload()
    
    
    def update_file(self, file_path, content):
        """Update a file in the Flutter project"""
        full_path = os.path.join(self.project_path, file_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return {"status": "file_updated", "path": full_path}
    
    def get_status(self):
        """Get Flutter process status"""
        if not self.flutter_process:
            return {"running": False, "ready": False, "recent_output": self.output_buffer[-10:]}
        
        is_alive = self.flutter_process.poll() is None
        
        return {
            "running": is_alive,
            "ready": self.ready,
            "pid": self.flutter_process.pid if is_alive else None,
            "recent_output": self.output_buffer[-10:],
            "output_length": len(self.output_buffer)
        }

# Initialize Flutter manager
flutter_manager = FlutterManager()

# Initialize advanced logging and monitoring systems
try:
    from utils.advanced_logger import logger, LogCategory, RequestTracker
    from utils.request_tracer import tracer
    from utils.performance_monitor import performance_monitor
    from utils.error_analyzer import error_analyzer
    
    # Configure advanced logging
    logger.configure(
        enable_console=True, 
        enable_file=True, 
        log_file_path="logs/flutter_server.log"
    )
    
    # Start performance monitoring
    performance_monitor.start_monitoring()
    
    # Set up performance alert callback
    def alert_callback(alert):
        logger.warn(LogCategory.PERFORMANCE, f"Performance Alert: {alert.message}",
                   context={
                       "alert_id": alert.alert_id,
                       "metric": alert.metric_name,
                       "value": alert.current_value,
                       "threshold": alert.threshold,
                       "level": alert.level.value
                   },
                   tags=["alert", "performance"])
    
    performance_monitor.subscribe_to_alerts(alert_callback)
    
    # Log successful initialization
    logger.info(LogCategory.SYSTEM, "Advanced monitoring systems initialized",
               context={
                   "logging_enabled": True,
                   "performance_monitoring": True,
                   "request_tracing": True,
                   "error_analysis": True
               },
               tags=["startup", "monitoring"])
    
    print("✓ Advanced monitoring and logging systems initialized")
    MONITORING_AVAILABLE = True
    
except ImportError as e:
    print(f"⚠️ Monitoring systems not available: {e}")
    MONITORING_AVAILABLE = False
except Exception as e:
    print(f"❌ Failed to initialize monitoring systems: {e}")
    MONITORING_AVAILABLE = False

# Initialize chat manager
from chat.chat_manager import chat_manager


# API Routes - all prefixed with /api


@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(flutter_manager.get_status())

@app.route('/api/hot-reload', methods=['POST'])
def hot_reload():
    result = flutter_manager.hot_reload()
    return jsonify(result)



@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get comprehensive logs including Flutter and monitoring logs"""
    try:
        from utils.advanced_logger import logger, LogCategory
        
        # Get advanced monitoring logs
        monitoring_logs = []
        try:
            advanced_logs = logger.get_logs(limit=100)  # Get recent 100 logs
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
        return jsonify({
            "logs": flutter_manager.output_buffer,
            "flutter_logs": flutter_manager.output_buffer,
            "monitoring_logs": [],
            "running": flutter_manager.is_running,
            "ready": flutter_manager.ready,
            "process_alive": flutter_manager.flutter_process.poll() is None if flutter_manager.flutter_process else False,
            "error": f"Failed to get monitoring logs: {str(e)}"
        })


@app.route('/api/file/<path:file_path>', methods=['GET'])
def get_file(file_path):
    """Get file contents for editor"""
    try:
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

@app.route('/api/file/<path:file_path>', methods=['PUT'])
def save_file(file_path):
    """Save file contents from editor"""
    try:
        data = request.json
        content = data.get('content', '')
        auto_reload = data.get('auto_reload', True)
        
        result = flutter_manager.update_file(file_path, content)
        
        if auto_reload and flutter_manager.is_running and file_path.endswith('.dart'):
            time.sleep(0.5)
            reload_result = flutter_manager.hot_reload()
            result['reload'] = reload_result
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# Code modification endpoints

@app.route('/api/stream/modify-code', methods=['POST'])
def modify_code_stream():
    """Stream code modifications using Server-Sent Events"""
    try:
        from code_modification.code_modifier import CodeModificationService, ModificationRequest
        import uuid
        import asyncio
        import json
        
        data = request.json
        description = data.get('description', '')
        target_files = data.get('target_files')
        user_id = data.get('user_id', 'anonymous')
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        # Create modification request
        request_id = str(uuid.uuid4())
        modification_request = ModificationRequest(
            description=description,
            target_files=target_files,
            user_id=user_id,
            request_id=request_id
        )
        
        def generate_sse_stream():
            """Generator function for SSE stream"""
            try:
                # Send initial connection event
                yield f"event: connected\ndata: {json.dumps({'request_id': request_id, 'message': 'Connected to streaming service'})}\n\n"
                
                # Initialize code modification service
                code_modifier = CodeModificationService(flutter_manager.project_path)
                
                # Create async event loop for streaming
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_modification():
                    try:
                        # Use the new streaming method (we'll add this next)
                        async for event in code_modifier.modify_code_stream(modification_request):
                            if hasattr(event, 'to_dict'):
                                # StreamProgress object
                                yield f"event: progress\ndata: {json.dumps(event.to_dict())}\n\n"
                            elif isinstance(event, dict):
                                # Status update
                                if 'event_type' in event:
                                    yield f"event: {event['event_type']}\ndata: {json.dumps(event)}\n\n"
                                else:
                                    yield f"event: update\ndata: {json.dumps(event)}\n\n"
                            elif isinstance(event, str):
                                # Text chunk
                                yield f"event: text\ndata: {json.dumps({'text': event})}\n\n"
                    
                    except Exception as e:
                        error_data = {
                            'error': str(e),
                            'stage': 'error',
                            'message': f'Streaming failed: {str(e)}'
                        }
                        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    
                    finally:
                        # Send completion event
                        yield f"event: complete\ndata: {json.dumps({'message': 'Stream ended'})}\n\n"
                
                # Run the async streaming
                async_gen = stream_modification()
                
                try:
                    while True:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                except StopAsyncIteration:
                    pass
                finally:
                    loop.close()
                    
            except Exception as e:
                error_data = {
                    'error': str(e),
                    'stage': 'error',
                    'message': f'Failed to start streaming: {str(e)}'
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        # Return SSE response
        return Response(
            generate_sse_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to start streaming: {str(e)}"}), 500

@app.route('/api/stream/chat', methods=['POST'])
def chat_stream():
    """Stream chat responses using Server-Sent Events"""
    try:
        from chat.chat_service import ChatService, ChatRequest
        import uuid
        import asyncio
        import json
        
        data = request.json
        message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        user_id = data.get('user_id', 'anonymous')
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        def generate_chat_sse_stream():
            """Generator function for chat SSE stream"""
            try:
                # Send initial connection event
                yield f"event: connected\ndata: {json.dumps({'message': 'Connected to chat stream'})}\n\n"
                
                # Initialize chat service
                chat_service = ChatService(flutter_manager, chat_manager)
                
                # Create chat request
                chat_request = ChatRequest(
                    message=message,
                    conversation_id=conversation_id,
                    user_id=user_id
                )
                
                # Create async event loop for streaming
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_chat():
                    try:
                        # Use the new streaming method (we'll add this next)
                        async for event in chat_service.handle_message_stream(chat_request):
                            if hasattr(event, 'to_dict'):
                                # StreamProgress object
                                yield f"event: progress\ndata: {json.dumps(event.to_dict())}\n\n"
                            elif isinstance(event, dict):
                                # Chat response or status update
                                event_type = event.get('event_type', 'chat')
                                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
                            elif isinstance(event, str):
                                # Text chunk
                                yield f"event: text\ndata: {json.dumps({'text': event})}\n\n"
                    
                    except Exception as e:
                        error_data = {
                            'error': str(e),
                            'stage': 'error',
                            'message': f'Chat streaming failed: {str(e)}'
                        }
                        yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                    
                    finally:
                        # Send completion event
                        yield f"event: complete\ndata: {json.dumps({'message': 'Chat stream ended'})}\n\n"
                
                # Run the async streaming
                async_gen = stream_chat()
                
                try:
                    while True:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                except StopAsyncIteration:
                    pass
                finally:
                    loop.close()
                    
            except Exception as e:
                error_data = {
                    'error': str(e),
                    'stage': 'error',
                    'message': f'Failed to start chat streaming: {str(e)}'
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
        
        # Return SSE response
        return Response(
            generate_chat_sse_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to start chat streaming: {str(e)}"}), 500





@app.route('/api/project-structure', methods=['GET'])
def get_project_structure():
    """Get detailed project structure analysis"""
    try:
        from code_modification.project_analyzer import FlutterProjectAnalyzer
        from utils.advanced_logger import logger, LogCategory, RequestTracker
        from utils.performance_monitor import performance_monitor, TimingContext
        
        with RequestTracker() as req:
            with TimingContext("project_structure_analysis"):
                logger.info(LogCategory.SYSTEM, "Project structure analysis requested")
                
                analyzer = FlutterProjectAnalyzer(flutter_manager.project_path)
                project_summary = analyzer.generate_project_summary()
                
                # Get additional metadata
                project_metadata = {
                    "analysis_timestamp": time.time(),
                    "project_path": str(flutter_manager.project_path),
                    "flutter_status": flutter_manager.get_status(),
                    "cache_status": "live_analysis"  # Future: implement caching
                }
                
                logger.info(LogCategory.SYSTEM, "Project structure analysis completed",
                           context={
                               "dart_files": project_summary.get("total_dart_files", 0),
                               "dependencies": len(project_summary.get("dependencies", [])),
                               "architecture": project_summary.get("architecture_pattern", "unknown")
                           })
                
                return jsonify({
                    "status": "success",
                    "project_structure": project_summary,
                    "metadata": project_metadata
                })
        
    except Exception as e:
        from utils.error_analyzer import analyze_error
        error_instance = analyze_error("api", "get_project_structure", e)
        
        return jsonify({
            "status": "error", 
            "error": str(e),
            "error_id": error_instance.error_id
        }), 500








# Chat API endpoints
@app.route('/api/chat/send', methods=['POST'])
def chat_send_message():
    """Send a message to AI chat and get response using the new modular chat service"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Import and use the new chat service
        from chat.chat_service import chat_service, ChatRequest
        
        # Set dependencies if not already set
        chat_service.set_dependencies(flutter_manager=flutter_manager, chat_manager=chat_manager)
        
        # Create chat request
        chat_request = ChatRequest(
            message=message,
            conversation_id=conversation_id
        )
        
        # Handle the message using the modular chat service
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            chat_response = loop.run_until_complete(chat_service.handle_message(chat_request))
        finally:
            loop.close()
        
        # Return immediate response with intent information
        response_data = {
            "status": "success",
            "conversation_id": chat_response.conversation_id,
            "message": chat_response.message,
            "intent": chat_response.intent.value,
            "requires_code_modification": chat_response.requires_code_modification
        }
        
        if chat_response.code_modification_request_id:
            response_data["code_modification_request_id"] = chat_response.code_modification_request_id
        
        if chat_response.metadata:
            response_data["metadata"] = chat_response.metadata
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500

@app.route('/api/chat/history', methods=['GET'])
def chat_get_history():
    """Get conversation history"""
    try:
        conversation_id = request.args.get('conversation_id')
        limit = request.args.get('limit', type=int)
        
        if not conversation_id:
            conversation_id = chat_manager.get_or_create_default_conversation()
        
        messages = chat_manager.get_messages(conversation_id, limit=limit)
        
        return jsonify({
            "status": "success",
            "conversation_id": conversation_id,
            "messages": [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get history: {str(e)}"}), 500

@app.route('/api/chat/new', methods=['POST'])
def chat_new_conversation():
    """Create a new conversation"""
    try:
        data = request.json or {}
        title = data.get('title', 'New Conversation')
        
        conversation_id = chat_manager.create_conversation(title)
        
        return jsonify({
            "status": "success",
            "conversation_id": conversation_id,
            "message": "New conversation created"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create conversation: {str(e)}"}), 500

@app.route('/api/chat/conversations', methods=['GET'])
def chat_list_conversations():
    """Get list of all conversations"""
    try:
        conversations = chat_manager.get_conversation_list()
        stats = chat_manager.get_stats()
        
        return jsonify({
            "status": "success",
            "conversations": conversations,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to list conversations: {str(e)}"}), 500

@app.route('/api/chat/conversation/<conversation_id>', methods=['DELETE'])
def chat_delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        success = chat_manager.delete_conversation(conversation_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Conversation deleted"
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500

@app.route('/api/chat/conversation/<conversation_id>/clear', methods=['POST'])
def chat_clear_conversation(conversation_id):
    """Clear all messages from a conversation"""
    try:
        success = chat_manager.clear_conversation(conversation_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Conversation cleared"
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to clear conversation: {str(e)}"}), 500



# Flutter static assets routing (similar to nginx config)
@app.route('/canvaskit/<path:path>')
@app.route('/assets/<path:path>')
@app.route('/manifest.json')
@app.route('/favicon.ico')
@app.route('/favicon.png') 
@app.route('/icons/<path:path>')
@app.route('/flutter_bootstrap.js')
def flutter_static_assets(filename=None, path=None):
    """Proxy Flutter static assets to the Flutter development server"""
    import requests
    
    try:
        # Build the correct URL based on the request
        request_path = request.path.lstrip('/')
        flutter_url = f'http://127.0.0.1:8080/{request_path}'
        
        resp = requests.get(flutter_url, stream=True, timeout=10)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
                
        # Set proper headers for static assets
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        # Copy important headers from Flutter server
        for header in ['Content-Type', 'Content-Length']:
            if header in resp.headers:
                headers[header] = resp.headers[header]
        
        return Response(generate(), 
                       status=resp.status_code,
                       headers=headers)
    except Exception as e:
        print(f"Error serving static asset {request.path}: {str(e)}")
        return f"Asset not available: {str(e)}", 404

# Handle other JS/CSS/image files with file extensions
@app.route('/<path:filename>')
def static_file_handler(filename):
    """Handle static files like .js, .css, .png, etc."""
    import requests
    
    # Check if this looks like a static asset based on extension
    static_extensions = ['.js', '.js.map', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.ico']
    
    if any(filename.endswith(ext) for ext in static_extensions):
        try:
            flutter_url = f'http://127.0.0.1:8080/{filename}'
            resp = requests.get(flutter_url, stream=True, timeout=10)
            
            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    yield chunk
                    
            # Set proper headers for static assets
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            # Copy important headers from Flutter server
            for header in ['Content-Type', 'Content-Length']:
                if header in resp.headers:
                    headers[header] = resp.headers[header]
            
            return Response(generate(), 
                           status=resp.status_code,
                           headers=headers)
        except Exception as e:
            print(f"Error serving static file {filename}: {str(e)}")
            return f"Asset not available: {str(e)}", 404
    
    # Not a static asset, return 404
    return "Not Found", 404

# Flutter app proxy route
@app.route('/app')
@app.route('/app/')
@app.route('/app/<path:path>')
def flutter_app(path=''):
    """Proxy Flutter app requests to the Flutter development server with caching optimization"""
    import requests
    try:
        flutter_url = f'http://127.0.0.1:8080/{path}'
        resp = requests.get(flutter_url, stream=True)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
        
        # Optimize headers for better performance
        headers = dict(resp.headers)
        
        # Add caching for static assets
        if any(ext in path for ext in ['.js', '.css', '.woff', '.woff2', '.ttf', '.otf']):
            headers['Cache-Control'] = 'public, max-age=3600, immutable'  # 1 hour cache
        elif any(ext in path for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']):
            headers['Cache-Control'] = 'public, max-age=86400'  # 24 hour cache for images
        else:
            headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # No cache for HTML/main app
            
        # Enable compression hint
        if 'content-encoding' not in headers:
            headers['Vary'] = 'Accept-Encoding'
                
        return Response(generate(), 
                       status=resp.status_code,
                       headers=headers)
    except Exception as e:
        return f"Flutter app not available: {str(e)}", 503

# Landing page with instructions and embedded app
@app.route('/')
def index():
    return render_template('index.html')

# Code editor page
@app.route('/editor')
def editor():
    return render_template('editor.html')

# Project overview page
@app.route('/project')
def project_overview():
    return render_template('project.html')

# AI Chat page
@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/api/file-tree', methods=['GET'])
def get_file_tree():
    """Get project file tree structure for editor"""
    try:
        import os
        from pathlib import Path
        
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

def main():
    print("Starting Flask server on port 5000...")
    print("Auto-starting Flutter development server...")
    print("Access the web interface at: http://localhost:5000")
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Log application startup
    if MONITORING_AVAILABLE:
        logger.info(LogCategory.SYSTEM, "Flutter server application starting",
                   context={
                       "port": 5000,
                       "project_path": flutter_manager.project_path,
                       "repo_url": flutter_manager.repo_url is not None,
                       "dev_mode": flutter_manager.dev_mode
                   },
                   tags=["startup", "flask"])
    
    # Auto-start Flutter development server
    try:
        # Check if port 8080 is available
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        port_available = sock.connect_ex(('localhost', 8080)) != 0
        sock.close()
        
        if not port_available:
            print("Warning: Port 8080 is already in use. Attempting to free it...")
            import subprocess
            subprocess.run(["pkill", "-9", "-f", "dart"], stderr=subprocess.DEVNULL)
            time.sleep(1)
        
        result = flutter_manager.start_flutter()
        if result.get('error'):
            print(f"Warning: Flutter auto-start failed: {result['error']}")
            print("You can still start Flutter manually via the web interface or API")
            
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.FLUTTER, "Flutter auto-start failed",
                           context={
                               "error": result['error'],
                               "manual_start_available": True
                           },
                           tags=["startup", "flutter", "failed"])
        else:
            print(f"✓ Flutter development server starting (PID: {result.get('pid')})")
            print("Waiting for Flutter to initialize...")
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.FLUTTER, "Flutter development server auto-started",
                           context={
                               "pid": result.get('pid'),
                               "port": 8080,
                               "dev_mode": flutter_manager.dev_mode
                           },
                           tags=["startup", "flutter", "success"])
            
            # Give Flutter a moment to start up
            time.sleep(2)
    except Exception as e:
        print(f"Warning: Failed to auto-start Flutter: {str(e)}")
        print("You can still start Flutter manually via the web interface or API")
        
        if MONITORING_AVAILABLE:
            error_analyzer.analyze_error(
                component="flutter_startup",
                operation="auto_start_flutter",
                message=str(e),
                context={
                    "manual_start_available": True,
                    "port_checked": True
                }
            )
    
    # Log final startup completion
    if MONITORING_AVAILABLE:
        logger.info(LogCategory.SYSTEM, "Flask server ready to serve requests",
                   context={
                       "host": "0.0.0.0",
                       "port": 5000,
                       "debug_mode": True,
                       "flutter_status": flutter_manager.is_running,
                       "monitoring_active": True
                   },
                   tags=["startup", "ready"])
    
    print("🚀 All systems ready!")
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()