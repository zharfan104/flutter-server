"""
Hot Reload Recovery Service
Handles automatic error detection and AI-powered fixing for Flutter compilation errors
"""

import os
import time
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel
    from utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Import LLM and prompt loading
from .llm_executor import SimpleLLMExecutor, LLMResponse
from .prompt_loader import PromptLoader
from .project_analyzer import FlutterProjectAnalyzer


@dataclass
class ErrorRecoveryResult:
    """Result of an error recovery attempt"""
    success: bool
    attempts: int
    fix_applied: str
    final_error: Optional[str] = None
    recovery_messages: List[str] = None


@dataclass
class CompilationError:
    """Represents a Flutter compilation error"""
    line: str
    category: str
    cause: str
    file: str
    fix_action: str


class HotReloadRecoveryService:
    """
    Service for automatically recovering from Flutter compilation errors using AI
    """
    
    def __init__(self, project_path: str, flutter_manager=None, chat_manager=None):
        self.project_path = project_path
        self.flutter_manager = flutter_manager
        self.chat_manager = chat_manager
        
        # Initialize components
        self.llm_executor = SimpleLLMExecutor()
        self.prompt_loader = PromptLoader()
        self.project_analyzer = FlutterProjectAnalyzer(project_path)
        
        # Recovery settings
        self.max_retries = 3
        self.recovery_timeout = 180  # 3 minutes max for recovery
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "HotReloadRecoveryService initialized", 
                       context={"project_path": project_path})
    
    async def attempt_recovery(self, error_output: str, conversation_id: Optional[str] = None, 
                             max_retries: int = 3) -> ErrorRecoveryResult:
        """
        Main entry point for error recovery
        
        Args:
            error_output: Flutter compilation error output
            conversation_id: Chat conversation ID for progress updates
            max_retries: Maximum number of recovery attempts
            
        Returns:
            ErrorRecoveryResult with recovery status and details
        """
        start_time = time.time()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"Starting error recovery",
                       context={
                           "max_retries": max_retries,
                           "conversation_id": conversation_id,
                           "error_length": len(error_output)
                       })
        
        recovery_messages = []
        
        try:
            for attempt in range(1, max_retries + 1):
                attempt_start = time.time()
                
                # Send progress message
                progress_msg = f"🔧 **Error Recovery Attempt {attempt}/{max_retries}**\n\nAnalyzing compilation errors..."
                recovery_messages.append(progress_msg)
                self._send_chat_message(conversation_id, progress_msg)
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Recovery attempt {attempt}/{max_retries}")
                
                # Step 1: Analyze errors
                analysis_result = await self._analyze_errors(error_output, attempt)
                if not analysis_result:
                    continue
                
                # Step 2: Apply fixes
                fix_result = await self._apply_fixes(analysis_result, error_output, attempt, max_retries)
                if not fix_result.get("success"):
                    continue
                
                # Step 3: Test the fix
                test_result = await self._test_fix(attempt)
                
                if test_result.get("success"):
                    duration = time.time() - start_time
                    success_msg = f"✅ **Error Recovery Successful!**\n\nFixed in {attempt} attempt(s) ({duration:.1f}s)\n🤖 Applied: {fix_result.get('fix_summary', 'Compilation error fixes')}"
                    recovery_messages.append(success_msg)
                    self._send_chat_message(conversation_id, success_msg)
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.ERROR_FIXING, f"Error recovery successful after {attempt} attempts",
                                   context={"duration_seconds": duration, "attempts": attempt})
                    
                    return ErrorRecoveryResult(
                        success=True,
                        attempts=attempt,
                        fix_applied=fix_result.get('fix_summary', 'Compilation error fixes'),
                        recovery_messages=recovery_messages
                    )
                else:
                    # Get new error output for next iteration
                    error_output = test_result.get("error_output", error_output)
                    
                    attempt_duration = time.time() - attempt_start
                    retry_msg = f"🔄 Attempt {attempt} unsuccessful ({attempt_duration:.1f}s). Analyzing new errors..."
                    recovery_messages.append(retry_msg)
                    self._send_chat_message(conversation_id, retry_msg)
            
            # All attempts failed
            duration = time.time() - start_time
            failure_msg = f"❌ **Error Recovery Failed**\n\nCould not resolve errors after {max_retries} attempts ({duration:.1f}s)\n🔧 Manual intervention required"
            recovery_messages.append(failure_msg)
            self._send_chat_message(conversation_id, failure_msg)
            
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.ERROR_FIXING, f"Error recovery failed after {max_retries} attempts",
                           context={"duration_seconds": duration, "final_error": error_output[:200]})
            
            return ErrorRecoveryResult(
                success=False,
                attempts=max_retries,
                fix_applied="Recovery failed",
                final_error=error_output,
                recovery_messages=recovery_messages
            )
            
        except Exception as e:
            error_msg = f"❌ **Recovery System Error**\n\nUnexpected error during recovery: {str(e)}"
            recovery_messages.append(error_msg)
            self._send_chat_message(conversation_id, error_msg)
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Recovery system error: {e}")
            
            return ErrorRecoveryResult(
                success=False,
                attempts=0,
                fix_applied=f"System error: {str(e)}",
                final_error=str(e),
                recovery_messages=recovery_messages
            )
    
    async def _analyze_errors(self, error_output: str, attempt: int) -> Optional[Dict]:
        """Analyze compilation errors using AI"""
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Analyzing errors (attempt {attempt})")
            
            # Load analysis prompt
            try:
                analysis_prompt = self.prompt_loader.get_prompt_info("Analyze Flutter Compilation Errors for Relace Fixes")["prompt"]
            except KeyError:
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.ERROR_FIXING, "Analysis prompt not found")
                return None
            
            # Prepare prompt context
            context = {
                "project_path": self.project_path,
                "error_output": error_output
            }
            
            # Execute LLM request
            messages = [{"role": "user", "content": analysis_prompt.format(**context)}]
            
            response = self.llm_executor.execute(messages)
            
            if response and response.text:
                # Parse JSON response
                analysis_data = self._extract_json_from_response(response.text)
                if analysis_data:
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.ERROR_FIXING, "Error analysis completed",
                                   context={"errors_found": analysis_data.get("analysis", {}).get("total_errors", 0)})
                    return analysis_data
            
            return None
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Error analysis failed: {e}")
            return None
    
    async def _apply_fixes(self, analysis_result: Dict, error_output: str, attempt: int, max_attempts: int) -> Dict:
        """Apply fixes based on error analysis using Relace API"""
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Generating fix snippets (attempt {attempt})")
            
            # Load fix snippet generation prompt
            try:
                fix_prompt = self.prompt_loader.get_prompt_info("Generate Fix Snippets for Relace API")["prompt"]
            except KeyError:
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.ERROR_FIXING, "Fix snippets prompt not found")
                return {"success": False, "error": "Fix snippets prompt not found"}
            
            # Prepare prompt context
            context = {
                "project_path": self.project_path,
                "attempt_number": attempt,
                "max_attempts": max_attempts,
                "error_analysis": json.dumps(analysis_result, indent=2),
                "error_output": error_output
            }
            
            # Execute LLM request to generate fix snippets
            messages = [{"role": "user", "content": fix_prompt.format(**context)}]
            
            response = self.llm_executor.execute(messages)
            
            if response and response.text:
                # Parse JSON response with fix snippets
                fix_data = self._extract_json_from_response(response.text)
                if fix_data and fix_data.get("fixes"):
                    # Apply fixes using Relace API
                    apply_result = await self._apply_fixes_with_relace(fix_data["fixes"])
                    if apply_result.get("success"):
                        if MONITORING_AVAILABLE:
                            logger.info(LogCategory.ERROR_FIXING, "Relace fixes applied successfully")
                        return {
                            "success": True,
                            "fix_summary": fix_data.get("summary", "Applied targeted error fixes"),
                            "files_modified": apply_result.get("files_modified", 0),
                            "relace_results": apply_result.get("results", [])
                        }
            
            return {"success": False, "error": "Failed to generate or apply fix snippets"}
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Fix application failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _test_fix(self, attempt: int) -> Dict:
        """Test if the fix resolved the compilation errors"""
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Testing fix (attempt {attempt})")
            
            if not self.flutter_manager:
                return {"success": False, "error": "Flutter manager not available"}
            
            # Wait a moment for file changes to be detected
            await asyncio.sleep(2)
            
            # Trigger hot reload without recovery (to avoid infinite recursion)
            reload_result = self.flutter_manager.hot_reload(with_error_recovery=False)
            
            # Wait for reload to complete
            await asyncio.sleep(3)
            
            # Check the output for errors
            recent_output = '\n'.join(self.flutter_manager.output_buffer[-10:])
            
            error_patterns = [
                "Error:",
                "error:",
                "Try again after fixing",
                "failed to compile",
                "compilation failed",
                "Member not found:"
            ]
            
            has_errors = any(pattern in recent_output for pattern in error_patterns)
            
            if has_errors:
                return {
                    "success": False,
                    "error_output": recent_output,
                    "reload_result": reload_result
                }
            else:
                return {
                    "success": True,
                    "reload_result": reload_result
                }
                
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Fix testing failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _apply_fixes_with_relace(self, fixes: List[Dict]) -> Dict:
        """Apply fixes using Relace API"""
        try:
            from .relace_applier import get_relace_applier, RelaceRequest
            import os
            
            relace_applier = get_relace_applier()
            results = []
            files_modified = 0
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Applying {len(fixes)} fixes with Relace API")
            
            for fix in fixes:
                file_path = fix.get("file_path")
                edit_snippet = fix.get("edit_snippet")
                
                if not file_path or not edit_snippet:
                    continue
                
                # Read current file content
                full_file_path = os.path.join(self.project_path, file_path)
                try:
                    with open(full_file_path, 'r', encoding='utf-8') as f:
                        current_content = f.read()
                except FileNotFoundError:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"File not found for fix: {file_path}")
                    continue
                
                # Create Relace request
                relace_request = RelaceRequest(
                    initial_code=current_content,
                    edit_snippet=edit_snippet,
                    file_path=file_path
                )
                
                # Apply fix with Relace
                relace_result = await relace_applier.apply_fix(relace_request)
                results.append(relace_result)
                
                if relace_result.success:
                    # Write modified content back to file
                    try:
                        with open(full_file_path, 'w', encoding='utf-8') as f:
                            f.write(relace_result.modified_code)
                        files_modified += 1
                        
                        if MONITORING_AVAILABLE:
                            logger.info(LogCategory.ERROR_FIXING, f"Successfully applied fix to {file_path}")
                    except Exception as e:
                        if MONITORING_AVAILABLE:
                            logger.error(LogCategory.ERROR_FIXING, f"Failed to write fixed file {file_path}: {e}")
                else:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Relace fix failed for {file_path}: {relace_result.error}")
            
            success = files_modified > 0
            return {
                "success": success,
                "files_modified": files_modified,
                "results": results,
                "total_fixes_attempted": len(fixes)
            }
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Relace fix application failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_json_from_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from LLM response, handling markdown code blocks"""
        try:
            # Import existing JSON utilities
            from .json_utils import safe_json_loads
            return safe_json_loads(response_text, "error recovery", default=None)
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"JSON extraction failed: {e}")
            return None
    
    def _send_chat_message(self, conversation_id: Optional[str], message: str):
        """Send progress message to chat"""
        if conversation_id and self.chat_manager:
            try:
                self.chat_manager.add_message(conversation_id, 'assistant', message)
                if MONITORING_AVAILABLE:
                    logger.debug(LogCategory.ERROR_FIXING, "Progress message sent to chat")
            except Exception as e:
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.ERROR_FIXING, f"Failed to send chat message: {e}")


# Global instance for easy access
_recovery_service = None

def get_recovery_service(project_path: str, flutter_manager=None, chat_manager=None) -> HotReloadRecoveryService:
    """Get or create the global recovery service instance"""
    global _recovery_service
    if _recovery_service is None or _recovery_service.project_path != project_path:
        _recovery_service = HotReloadRecoveryService(project_path, flutter_manager, chat_manager)
    else:
        # Update dependencies
        _recovery_service.flutter_manager = flutter_manager
        _recovery_service.chat_manager = chat_manager
    return _recovery_service