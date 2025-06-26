"""
Hot Reload Recovery Service
Enhanced automatic error detection and AI-powered fixing for Flutter compilation errors
Now integrates with the comprehensive DartAnalysisFixer system for robust recovery
"""

import os
import time
import json
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Import new robust recovery system
from .dart_analysis_fixer import DartAnalysisFixer, FixingConfig, FixingResult
from .comprehensive_logger import get_comprehensive_logger, reset_comprehensive_logger

# Import existing components for backward compatibility
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
        
        # Initialize legacy components for backward compatibility
        self.llm_executor = SimpleLLMExecutor()
        self.prompt_loader = PromptLoader()
        self.project_analyzer = FlutterProjectAnalyzer(project_path)
        
        # Initialize new robust recovery system
        self.dart_analysis_fixer = None  # Initialized per recovery session
        
        # Recovery settings (enhanced)
        self.max_retries = 5  # Increased for better success rate
        self.recovery_timeout = 300  # 5 minutes max for recovery
        self.enable_robust_recovery = True  # Use new system by default
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "HotReloadRecoveryService initialized (Enhanced)", 
                       context={
                           "project_path": project_path,
                           "robust_recovery": self.enable_robust_recovery,
                           "max_retries": self.max_retries
                       })
    
    async def attempt_recovery(self, error_output: str, conversation_id: Optional[str] = None, 
                             max_retries: int = None) -> ErrorRecoveryResult:
        """
        Enhanced main entry point for error recovery using the robust DartAnalysisFixer system
        
        Args:
            error_output: Flutter compilation error output (may be used for fallback)
            conversation_id: Chat conversation ID for progress updates
            max_retries: Maximum number of recovery attempts (defaults to service setting)
            
        Returns:
            ErrorRecoveryResult with recovery status and details
        """
        if max_retries is None:
            max_retries = self.max_retries
            
        start_time = time.time()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"Starting enhanced error recovery",
                       context={
                           "max_retries": max_retries,
                           "conversation_id": conversation_id,
                           "robust_recovery": self.enable_robust_recovery,
                           "error_output_length": len(error_output)
                       })
        
        recovery_messages = []
        
        # Initialize recovery session
        self._send_chat_message(conversation_id, "🔧 **Starting Comprehensive Error Recovery**\n\nInitializing robust analysis and fixing system...")
        
        try:
            if self.enable_robust_recovery:
                # Use the new robust DartAnalysisFixer system
                return await self._robust_recovery(conversation_id, max_retries, recovery_messages, start_time)
            else:
                # Fallback to legacy recovery for compatibility
                return await self._legacy_recovery(error_output, conversation_id, max_retries, recovery_messages, start_time)
                
        except Exception as e:
            error_msg = f"❌ **Recovery System Error**\n\nUnexpected error during recovery: {str(e)}"
            recovery_messages.append(error_msg)
            self._send_chat_message(conversation_id, error_msg)
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Recovery system error: {e}",
                           context={"conversation_id": conversation_id})
            
            return ErrorRecoveryResult(
                success=False,
                attempts=0,
                fix_applied=f"System error: {str(e)}",
                final_error=str(e),
                recovery_messages=recovery_messages
            )
    
    async def _robust_recovery(self, conversation_id: Optional[str], max_retries: int, 
                             recovery_messages: List[str], start_time: float) -> ErrorRecoveryResult:
        """Use the new robust DartAnalysisFixer system"""
        try:
            # Create fixing configuration
            log_file_path = f"logs/recovery_{int(start_time)}.json" if MONITORING_AVAILABLE else None
            config = FixingConfig(
                max_attempts=max_retries,
                enable_commands=True,
                enable_dart_fix=True,
                enable_build_runner=True,
                log_file_path=log_file_path,
                conversation_id=conversation_id
            )
            
            # Initialize the DartAnalysisFixer
            self.dart_analysis_fixer = DartAnalysisFixer(self.project_path, config)
            
            # Send progress update
            progress_msg = "🔍 **Running Comprehensive Dart Analysis**\n\nAnalyzing project structure and identifying all errors..."
            recovery_messages.append(progress_msg)
            self._send_chat_message(conversation_id, progress_msg)
            
            # Run the comprehensive fixing process
            fixing_result: FixingResult = await self.dart_analysis_fixer.fix_all_errors()
            
            # Create progress messages based on the result
            if fixing_result.success:
                duration = fixing_result.total_duration
                success_msg = (
                    f"✅ **Error Recovery Successful!**\n\n"
                    f"📊 **Results:**\n"
                    f"• Duration: {duration:.1f}s\n"
                    f"• Attempts: {fixing_result.attempts_made}\n"
                    f"• Errors Fixed: {fixing_result.initial_error_count} → {fixing_result.final_error_count}\n"
                    f"• Commands Executed: {len(fixing_result.commands_executed)}\n"
                    f"• Files Modified: {len(fixing_result.files_modified)}\n"
                    f"• Fixes Applied: {fixing_result.fixes_applied}\n\n"
                    f"🤖 **Applied comprehensive error recovery with command execution and targeted code fixes**"
                )
                recovery_messages.append(success_msg)
                self._send_chat_message(conversation_id, success_msg)
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Robust error recovery successful",
                               context={
                                   "duration_seconds": duration,
                                   "attempts": fixing_result.attempts_made,
                                   "errors_fixed": fixing_result.initial_error_count - fixing_result.final_error_count,
                                   "commands_executed": len(fixing_result.commands_executed),
                                   "files_modified": len(fixing_result.files_modified)
                               })
                
                return ErrorRecoveryResult(
                    success=True,
                    attempts=fixing_result.attempts_made,
                    fix_applied=f"Comprehensive recovery: {fixing_result.initial_error_count} → {fixing_result.final_error_count} errors",
                    recovery_messages=recovery_messages
                )
            else:
                duration = fixing_result.total_duration
                failure_msg = (
                    f"❌ **Error Recovery Incomplete**\n\n"
                    f"📊 **Results:**\n"
                    f"• Duration: {duration:.1f}s\n"
                    f"• Attempts: {fixing_result.attempts_made}\n"
                    f"• Errors Remaining: {fixing_result.final_error_count}/{fixing_result.initial_error_count}\n"
                    f"• Commands Executed: {len(fixing_result.commands_executed)}\n"
                    f"• Files Modified: {len(fixing_result.files_modified)}\n"
                    f"• Fixes Applied: {fixing_result.fixes_applied}\n\n"
                    f"🔧 Some progress made, but manual intervention may be required for remaining errors."
                )
                recovery_messages.append(failure_msg)
                self._send_chat_message(conversation_id, failure_msg)
                
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.ERROR_FIXING, f"Robust error recovery partially successful",
                               context={
                                   "duration_seconds": duration,
                                   "attempts": fixing_result.attempts_made,
                                   "errors_remaining": fixing_result.final_error_count,
                                   "error_message": fixing_result.error_message
                               })
                
                return ErrorRecoveryResult(
                    success=False,
                    attempts=fixing_result.attempts_made,
                    fix_applied=f"Partial recovery: {fixing_result.initial_error_count} → {fixing_result.final_error_count} errors",
                    final_error=fixing_result.error_message,
                    recovery_messages=recovery_messages
                )
                
        except Exception as e:
            error_msg = f"Robust recovery system failed: {str(e)}"
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, error_msg,
                           context={"conversation_id": conversation_id})
            
            # Fallback to legacy system
            fallback_msg = "🔄 **Falling back to legacy recovery system**"
            recovery_messages.append(fallback_msg)
            self._send_chat_message(conversation_id, fallback_msg)
            
            return await self._legacy_recovery("", conversation_id, max_retries, recovery_messages, start_time)
    
    async def _legacy_recovery(self, error_output: str, conversation_id: Optional[str], 
                             max_retries: int, recovery_messages: List[str], start_time: float) -> ErrorRecoveryResult:
        """Fallback to the original recovery system"""
        try:
            for attempt in range(1, max_retries + 1):
                attempt_start = time.time()
                
                # Send progress message
                progress_msg = f"🔧 **Legacy Recovery Attempt {attempt}/{max_retries}**\n\nAnalyzing compilation errors..."
                recovery_messages.append(progress_msg)
                self._send_chat_message(conversation_id, progress_msg)
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Legacy recovery attempt {attempt}/{max_retries}")
                
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
                    success_msg = f"✅ **Legacy Recovery Successful!**\n\nFixed in {attempt} attempt(s) ({duration:.1f}s)\n🤖 Applied: {fix_result.get('fix_summary', 'Compilation error fixes')}"
                    recovery_messages.append(success_msg)
                    self._send_chat_message(conversation_id, success_msg)
                    
                    return ErrorRecoveryResult(
                        success=True,
                        attempts=attempt,
                        fix_applied=fix_result.get('fix_summary', 'Legacy compilation error fixes'),
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
    
    def enable_robust_recovery_system(self, enable: bool = True):
        """Enable or disable the robust recovery system"""
        self.enable_robust_recovery = enable
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, f"Robust recovery system {'enabled' if enable else 'disabled'}",
                       context={"project_path": self.project_path})
    
    def get_recovery_status(self) -> Dict[str, Any]:
        """Get current recovery system status"""
        return {
            "robust_recovery_enabled": self.enable_robust_recovery,
            "max_retries": self.max_retries,
            "recovery_timeout": self.recovery_timeout,
            "project_path": self.project_path,
            "dart_analysis_fixer_initialized": self.dart_analysis_fixer is not None
        }
    
    async def _analyze_errors(self, error_output: str, attempt: int) -> Optional[Dict]:
        """Analyze compilation errors using AI"""
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Analyzing errors (attempt {attempt})")
            
            # Load analysis prompt
            try:
                analysis_prompt = self.prompt_loader.get_prompt_info("Analyze Flutter Compilation Errors")["prompt"]
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
        """Apply fixes based on error analysis using direct file writing"""
        try:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Generating fix snippets (attempt {attempt})")
            
            # Load fix snippet generation prompt
            try:
                fix_prompt = self.prompt_loader.get_prompt_info("Generate Fixed Files")["prompt"]
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
                    # Apply fixes using direct file writing
                    apply_result = await self._apply_fixes_direct(fix_data["fixes"])
                    if apply_result.get("success"):
                        if MONITORING_AVAILABLE:
                            logger.info(LogCategory.ERROR_FIXING, "Direct file fixes applied successfully")
                        return {
                            "success": True,
                            "fix_summary": fix_data.get("summary", "Applied targeted error fixes"),
                            "files_modified": apply_result.get("files_modified", 0),
                            "fix_results": apply_result.get("results", [])
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
    
    async def _apply_fixes_direct(self, fixes: List[Dict]) -> Dict:
        """Apply fixes using direct file writing"""
        try:
            import os
            from pathlib import Path
            
            results = []
            files_modified = 0
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Applying {len(fixes)} fixes with direct file writing")
            
            for fix in fixes:
                file_path = fix.get("file_path")
                file_content = fix.get("file_content") or fix.get("edit_snippet")  # Support both formats
                
                if not file_path or not file_content:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Skipping invalid fix: missing file_path or content")
                    continue
                
                # Resolve full file path
                full_file_path = Path(self.project_path) / file_path
                
                # Create backup before modifying
                backup_content = None
                try:
                    if full_file_path.exists():
                        with open(full_file_path, 'r', encoding='utf-8') as f:
                            backup_content = f.read()
                except Exception as e:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Could not read file for backup: {e}")
                
                # Write new content
                try:
                    # Ensure directory exists
                    full_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    
                    files_modified += 1
                    
                    # Create a success result object
                    result = {
                        "success": True,
                        "file_path": file_path,
                        "modified_code": file_content,
                        "error": None
                    }
                    results.append(result)
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.ERROR_FIXING, f"Successfully applied fix to {file_path}")
                        
                except Exception as e:
                    error_msg = f"Failed to write file {file_path}: {str(e)}"
                    
                    # Attempt to restore backup if we have one
                    if backup_content:
                        try:
                            with open(full_file_path, 'w', encoding='utf-8') as f:
                                f.write(backup_content)
                            if MONITORING_AVAILABLE:
                                logger.info(LogCategory.ERROR_FIXING, f"Restored backup for {file_path}")
                        except:
                            pass  # Backup restore failed, but original error is more important
                    
                    # Create a failure result object
                    result = {
                        "success": False,
                        "file_path": file_path,
                        "modified_code": None,
                        "error": error_msg
                    }
                    results.append(result)
                    
                    if MONITORING_AVAILABLE:
                        logger.error(LogCategory.ERROR_FIXING, error_msg)
            
            success = files_modified > 0
            return {
                "success": success,
                "files_modified": files_modified,
                "results": results,
                "total_fixes_attempted": len(fixes)
            }
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Direct fix application failed: {e}")
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