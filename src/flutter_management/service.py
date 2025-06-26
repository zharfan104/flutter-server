"""
Flutter Management Service

Core service for managing Flutter development server processes, including:
- Project setup and initialization
- Flutter process lifecycle management
- Output monitoring and buffering
- Process health monitoring
"""

import os
import subprocess
import threading
import time
import queue
import asyncio
from typing import Dict, Any, Optional


class FlutterManager:
    """Main service for managing Flutter development server processes"""
    
    def __init__(self):
        self.flutter_process = None
        self.project_path = os.path.join(os.getcwd(), "project")
        self.output_buffer = []
        self.is_running = False
        self.ready = False
        self.repo_url = os.environ.get('REPO_URL')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.dev_mode = os.environ.get('FLUTTER_DEV_MODE', 'fast').lower()  # fast, debug, profile
        
    def setup_project(self) -> None:
        """Clone repository or check project existence (simplified - no auto-creation)"""
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
            # Check if Flutter project exists, but don't auto-create
            if not os.path.exists(self.project_path):
                print("⚠️ No Flutter project found at './project' - Please create one manually or use the web interface")
                return
            else:
                print("✅ Using existing Flutter project at './project'")
    
    def start_flutter(self) -> Dict[str, Any]:
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
    
    def _read_output(self) -> None:
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
    
    def hot_reload(self, with_error_recovery: bool = True, max_retries: int = 3) -> Dict[str, Any]:
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
    
    def _wait_for_reload_result(self, initial_buffer_length: int, max_retries: int) -> Dict[str, Any]:
        """Wait for hot reload result and trigger error recovery if needed"""
        
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
                from src.code_modification.services.hot_reload_recovery import get_recovery_service
                
                recovery_service = get_recovery_service(
                    project_path=self.project_path,
                    flutter_manager=self,
                    chat_manager=chat_manager
                )
                
                # Run recovery in a separate thread to avoid event loop conflicts
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
    
    def set_recovery_chat_context(self, chat_manager, conversation_id: str) -> None:
        """Set chat context for sending recovery progress messages"""
        self._chat_manager = chat_manager
        self._recovery_conversation_id = conversation_id
    
    def _send_recovery_message(self, conversation_id: str, message: str) -> None:
        """Send recovery progress message to chat"""
        if hasattr(self, '_chat_manager') and self._chat_manager:
            self._chat_manager.add_message(conversation_id, 'assistant', message)
    
    def trigger_hot_reload(self) -> Dict[str, Any]:
        """Alias for hot_reload() to match BuildPipelineService interface"""
        return self.hot_reload()
    
    def update_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Update a file in the Flutter project"""
        full_path = os.path.join(self.project_path, file_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return {"status": "file_updated", "path": full_path}
    
    def get_status(self) -> Dict[str, Any]:
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