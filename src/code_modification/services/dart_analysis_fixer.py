"""
Dart Analysis Fixer
Comprehensive error recovery system with iterative fixing, command execution, and robust validation
Based on steve-backend patterns but enhanced for Flutter development
"""

import asyncio
import time
import json
import os
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

# Import existing components
from .dart_analysis import DartAnalysisService, AnalysisResult, AnalysisIssue, AnalysisType
from .command_executor import CommandExecutor, CommandType, CommandResult
from .shell_command_parser import ShellCommandParser, get_shell_command_parser
from .error_diff_analyzer import ErrorDiffAnalyzer, ErrorSnapshot, ErrorDiff, get_error_diff_analyzer, reset_error_diff_analyzer
from .comprehensive_logger import ComprehensiveLogger, RecoveryStage, get_comprehensive_logger, reset_comprehensive_logger
from .llm_executor import SimpleLLMExecutor, LLMResponse
from .prompt_loader import PromptLoader
from .flutter_typo_fixer import FlutterTypoFixer

# Import existing utilities
try:
    from .json_utils import safe_json_loads
    JSON_UTILS_AVAILABLE = True
except ImportError:
    JSON_UTILS_AVAILABLE = False

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@dataclass
class AttemptMemory:
    """Memory of previous attempt for token-efficient context"""
    attempt_number: int
    errors_before: int
    errors_after: int
    commands_failed: List[str]
    files_modified: List[str]
    persistent_errors: List[str]  # Error patterns that didn't change
    success: bool
    brief_summary: str  # Max 50 words about what was tried

@dataclass
class FixingConfig:
    """Configuration for the fixing process"""
    max_attempts: int = 5
    max_errors_per_attempt: int = 20
    timeout_per_attempt: int = 300  # 5 minutes
    enable_commands: bool = True
    enable_dart_fix: bool = True
    enable_build_runner: bool = True
    log_file_path: Optional[str] = None
    conversation_id: Optional[str] = None


@dataclass
class FixingResult:
    """Result of the complete fixing process"""
    success: bool
    initial_error_count: int
    final_error_count: int
    attempts_made: int
    commands_executed: List[str]
    fixes_applied: int
    files_modified: List[str]
    total_duration: float
    error_message: Optional[str] = None
    recovery_log: Optional[str] = None


class DartAnalysisFixer:
    """
    Comprehensive Dart analysis and fixing system with iterative recovery
    """
    
    def __init__(self, project_path: str, config: Optional[FixingConfig] = None):
        self.project_path = Path(project_path)
        self.config = config or FixingConfig()
        
        # Initialize components
        self.dart_analyzer = DartAnalysisService(str(self.project_path))
        self.command_executor = CommandExecutor(str(self.project_path))
        self.shell_parser = get_shell_command_parser(str(self.project_path), config.enable_commands)
        self.llm_executor = SimpleLLMExecutor()
        self.prompt_loader = PromptLoader()
        self.typo_fixer = FlutterTypoFixer()
        
        # Initialize session components
        self.session_id = f"dart_fix_{int(time.time())}"
        self.diff_analyzer: Optional[ErrorDiffAnalyzer] = None
        self.logger: Optional[ComprehensiveLogger] = None
        
        # Attempt memory for token-efficient context
        self.attempt_history: List[AttemptMemory] = []
        self.repeated_errors: Dict[str, int] = {}  # Track error frequency
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "DartAnalysisFixer initialized",
                       context={
                           "project_path": str(self.project_path),
                           "session_id": self.session_id,
                           "config": self.config.__dict__
                       })
    
    async def fix_all_errors(self, target_path: Optional[str] = None) -> FixingResult:
        """
        Main entry point for comprehensive error fixing
        
        Args:
            target_path: Specific path to analyze (defaults to lib/)
            
        Returns:
            FixingResult with complete fixing session details
        """
        start_time = time.time()
        
        # Initialize session components
        self._initialize_session()
        
        try:
            # Step 1: Initial analysis
            initial_analysis = await self._run_initial_analysis(target_path)
            if not initial_analysis:
                return self._create_error_result("Failed to run initial analysis", start_time)
            
            initial_error_count = len(initial_analysis.errors)
            self.logger.log_recovery_start(initial_error_count)
            
            if initial_error_count == 0:
                self.logger.log_recovery_end(True, 0)
                return FixingResult(
                    success=True,
                    initial_error_count=0,
                    final_error_count=0,
                    attempts_made=0,
                    commands_executed=[],
                    fixes_applied=0,
                    files_modified=[],
                    total_duration=time.time() - start_time,
                    recovery_log=self.logger.get_session_summary()
                )
            
            # Step 1.5: Quick typo fixing (before expensive AI pipeline)
            typo_fixes_applied = await self._apply_quick_typo_fixes(initial_analysis, target_path)
            
            # Re-analyze after typo fixes
            if typo_fixes_applied > 0:
                post_typo_analysis = await self._run_dart_analysis(target_path)
                if post_typo_analysis and len(post_typo_analysis.errors) < initial_error_count:
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.ERROR_FIXING, f"Typo fixes reduced errors: {initial_error_count} → {len(post_typo_analysis.errors)}",
                                  context={"session_id": self.session_id, "typo_fixes": typo_fixes_applied})
                    initial_analysis = post_typo_analysis
            
            # Step 2: Iterative fixing
            fixing_result = await self._iterative_fixing_loop(initial_analysis, target_path)
            
            # Step 3: Final validation
            final_analysis = await self._run_final_validation(target_path)
            final_error_count = len(final_analysis.errors) if final_analysis else initial_error_count
            
            # Complete session logging
            success = final_error_count == 0
            self.logger.log_recovery_end(success, final_error_count)
            
            total_duration = time.time() - start_time
            
            return FixingResult(
                success=success,
                initial_error_count=initial_error_count,
                final_error_count=final_error_count,
                attempts_made=fixing_result["attempts_made"],
                commands_executed=fixing_result["commands_executed"],
                fixes_applied=fixing_result["fixes_applied"],
                files_modified=fixing_result["files_modified"],
                total_duration=total_duration,
                recovery_log=self.logger.get_session_summary()
            )
            
        except Exception as e:
            error_msg = f"Unexpected error during fixing: {str(e)}"
            self.logger.log_recovery_end(False, error_message=error_msg)
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, error_msg,
                           context={"session_id": self.session_id, "error": str(e)})
            
            return self._create_error_result(error_msg, start_time)
    
    async def fix_all_errors_stream(self, target_path: Optional[str] = None):
        """
        Stream error fixing process with real-time progress updates
        
        Args:
            target_path: Specific path to analyze (defaults to lib/)
            
        Yields:
            StreamProgress objects with fixing progress and results
        """
        from .llm_executor import StreamProgress
        
        start_time = time.time()
        
        # Initialize session components
        self._initialize_session()
        
        try:
            # Initial progress
            yield StreamProgress(
                stage="analyzing",
                message="Starting Dart error analysis...",
                progress_percent=0.0,
                metadata={"session_id": self.session_id}
            )
            
            # Step 1: Initial analysis
            yield StreamProgress(
                stage="analyzing",
                message="Running initial Dart analysis...",
                progress_percent=10.0
            )
            
            initial_analysis = await self._run_initial_analysis(target_path)
            if not initial_analysis:
                yield StreamProgress(
                    stage="error",
                    message="Failed to run initial analysis",
                    progress_percent=0.0
                )
                return
            
            initial_error_count = len(initial_analysis.errors)
            self.logger.log_recovery_start(initial_error_count)
            
            yield StreamProgress(
                stage="analyzing",
                message=f"Found {initial_error_count} errors to fix",
                progress_percent=20.0,
                metadata={"initial_errors": initial_error_count}
            )
            
            if initial_error_count == 0:
                yield StreamProgress(
                    stage="complete",
                    message="No errors found - project is healthy!",
                    progress_percent=100.0,
                    metadata={"success": True, "errors_fixed": 0}
                )
                return
            
            # Step 1.5: Quick typo fixing
            yield StreamProgress(
                stage="analyzing",
                message="Checking for quick typo fixes...",
                progress_percent=25.0
            )
            
            typo_fixes_applied = await self._apply_quick_typo_fixes(initial_analysis, target_path)
            
            if typo_fixes_applied > 0:
                yield StreamProgress(
                    stage="analyzing",
                    message=f"Applied {typo_fixes_applied} typo fixes, re-analyzing...",
                    progress_percent=30.0,
                    metadata={"typo_fixes": typo_fixes_applied}
                )
                
                post_typo_analysis = await self._run_dart_analysis(target_path)
                if post_typo_analysis and len(post_typo_analysis.errors) < initial_error_count:
                    initial_analysis = post_typo_analysis
                    yield StreamProgress(
                        stage="analyzing",
                        message=f"Typo fixes reduced errors to {len(initial_analysis.errors)}",
                        progress_percent=35.0,
                        metadata={"errors_after_typos": len(initial_analysis.errors)}
                    )
            
            # Step 2: Iterative fixing with streaming
            yield StreamProgress(
                stage="generating",
                message="Starting AI-powered error fixing...",
                progress_percent=40.0
            )
            
            async for progress in self._iterative_fixing_loop_stream(initial_analysis, target_path):
                yield progress
            
            # Step 3: Final validation
            yield StreamProgress(
                stage="validating",
                message="Running final validation...",
                progress_percent=90.0
            )
            
            final_analysis = await self._run_final_validation(target_path)
            final_error_count = len(final_analysis.errors) if final_analysis else initial_error_count
            
            # Complete session logging
            success = final_error_count == 0
            self.logger.log_recovery_end(success, final_error_count)
            
            total_duration = time.time() - start_time
            errors_fixed = initial_error_count - final_error_count
            
            yield StreamProgress(
                stage="complete" if success else "partial",
                message=f"Error fixing completed! Fixed {errors_fixed} of {initial_error_count} errors" if success else f"Fixed {errors_fixed} errors, {final_error_count} remaining",
                progress_percent=100.0,
                metadata={
                    "success": success,
                    "initial_errors": initial_error_count,
                    "final_errors": final_error_count,
                    "errors_fixed": errors_fixed,
                    "duration": total_duration,
                    "session_id": self.session_id
                }
            )
            
            # Send final result as structured event
            yield {
                "event_type": "result",
                "success": success,
                "initial_error_count": initial_error_count,
                "final_error_count": final_error_count,
                "errors_fixed": errors_fixed,
                "duration": total_duration,
                "session_id": self.session_id
            }
            
        except Exception as e:
            error_msg = f"Unexpected error during fixing: {str(e)}"
            self.logger.log_recovery_end(False, error_message=error_msg)
            
            yield StreamProgress(
                stage="error",
                message=error_msg,
                progress_percent=0.0,
                metadata={"error": str(e), "session_id": self.session_id}
            )
    
    async def _iterative_fixing_loop_stream(self, initial_analysis: AnalysisResult, 
                                          target_path: Optional[str] = None):
        """Stream the iterative fixing loop with progress updates"""
        from .llm_executor import StreamProgress
        
        current_analysis = initial_analysis
        attempts_made = 0
        
        for attempt in range(1, self.config.max_attempts + 1):
            if len(current_analysis.errors) == 0:
                break  # No more errors to fix
            
            # Check for early exit conditions
            current_error_messages = [str(error) for error in current_analysis.errors[:10]]
            should_exit, exit_reason = self._should_exit_early(current_error_messages, attempt)
            if should_exit:
                yield StreamProgress(
                    stage="generating",
                    message=f"Early exit: {exit_reason}",
                    progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0,
                    metadata={"attempt": attempt, "exit_reason": exit_reason}
                )
                break
            
            attempts_made = attempt
            errors_before = len(current_analysis.errors)
            
            yield StreamProgress(
                stage="generating",
                message=f"Attempt {attempt}/{self.config.max_attempts}: Fixing {errors_before} errors...",
                progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0,
                metadata={"attempt": attempt, "errors_before": errors_before}
            )
            
            try:
                # Step 1: Execute helpful commands
                if self.config.enable_commands:
                    yield StreamProgress(
                        stage="generating",
                        message=f"Attempt {attempt}: Running helpful commands...",
                        progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 5.0
                    )
                    
                    commands_result = await self._execute_helpful_commands(current_analysis)
                    attempt_commands = commands_result["commands_executed"]
                    
                    if attempt_commands:
                        yield StreamProgress(
                            stage="generating",
                            message=f"Attempt {attempt}: Executed {len(attempt_commands)} commands",
                            progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 10.0,
                            metadata={"commands_executed": attempt_commands}
                        )
                
                # Step 2: Apply AI-generated fixes with streaming
                yield StreamProgress(
                    stage="generating", 
                    message=f"Attempt {attempt}: AI is generating fixes...",
                    progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 15.0
                )
                
                async for ai_progress in self._apply_ai_fixes_stream(current_analysis, attempt):
                    yield ai_progress
                
                # Get the actual fixes result
                fixes_result = await self._apply_ai_fixes(current_analysis, attempt)
                
                # Step 3: Re-analyze
                yield StreamProgress(
                    stage="generating",
                    message=f"Attempt {attempt}: Re-analyzing after fixes...",
                    progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 35.0
                )
                
                new_analysis = self.dart_analyzer.run_analysis(target_path)
                
                if new_analysis.success or new_analysis.errors:
                    errors_after = len(new_analysis.errors)
                    error_reduction = errors_before - errors_after
                    
                    yield StreamProgress(
                        stage="generating",
                        message=f"Attempt {attempt}: Reduced errors by {error_reduction} ({errors_before} → {errors_after})",
                        progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 40.0,
                        metadata={
                            "attempt": attempt,
                            "errors_before": errors_before,
                            "errors_after": errors_after,
                            "error_reduction": error_reduction
                        }
                    )
                    
                    # Update tracking with attempt memory
                    old_error_msgs = set(str(e) for e in current_analysis.errors[:10])
                    new_error_msgs = set(str(e) for e in new_analysis.errors[:10])
                    persistent_errors = list(old_error_msgs & new_error_msgs)
                    
                    success = error_reduction > 0 or errors_after == 0
                    attempt_memory = self._create_attempt_memory(
                        attempt=attempt,
                        errors_before=errors_before,
                        errors_after=errors_after,
                        commands_failed=[],  # Would need to track this properly
                        files_modified=fixes_result.get("files_modified", []),
                        persistent_errors=persistent_errors,
                        success=success
                    )
                    self.attempt_history.append(attempt_memory)
                    
                    current_analysis = new_analysis
                else:
                    yield StreamProgress(
                        stage="generating",
                        message=f"Attempt {attempt}: Analysis failed, retrying...",
                        progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0 + 20.0,
                        metadata={"attempt": attempt, "analysis_failed": True}
                    )
                
            except Exception as e:
                yield StreamProgress(
                    stage="error",
                    message=f"Attempt {attempt} failed: {str(e)}",
                    progress_percent=40.0 + (attempt / self.config.max_attempts) * 45.0,
                    metadata={"attempt": attempt, "error": str(e)}
                )
                continue
    
    async def _apply_ai_fixes_stream(self, analysis_result: AnalysisResult, attempt: int):
        """Stream the AI fix generation process"""
        from .llm_executor import StreamProgress
        
        yield StreamProgress(
            stage="generating",
            message="Preparing context for AI...",
            progress_percent=45.0,
            metadata={"attempt": attempt}
        )
        
        try:
            # Load the comprehensive fixing prompt
            try:
                fix_prompt_info = self.prompt_loader.get_prompt_info("Dart Analysis Command Fixer")
                fix_prompt = fix_prompt_info["prompt"]
            except KeyError:
                fix_prompt_info = self.prompt_loader.get_prompt_info("Generate Fixed Files")
                fix_prompt = fix_prompt_info["prompt"]
            
            # Limit analysis output to most relevant errors (token efficiency)
            limited_output = self._limit_analysis_output(analysis_result.output, max_errors=10)
            
            # Prepare context for the prompt
            context = {
                "project_path": str(self.project_path),
                "attempt_number": attempt,
                "max_attempts": self.config.max_attempts,
                "analysis_output": limited_output,
                "error_count": len(analysis_result.errors),
                "warning_count": len(analysis_result.warnings),
                "categorized_errors": self.dart_analyzer.categorize_errors(analysis_result.issues),
                "previous_attempts": self._get_relevant_history_context()
            }
            
            yield StreamProgress(
                stage="generating",
                message="AI is analyzing errors and generating fixes...",
                progress_percent=50.0,
                metadata={"attempt": attempt, "errors_to_fix": len(analysis_result.errors)}
            )
            
            # Execute LLM request with streaming
            messages = [{"role": "user", "content": fix_prompt.format(**context)}]
            
            accumulated_text = ""
            async for event in self.llm_executor.execute_stream_with_progress(messages):
                if hasattr(event, 'to_dict'):
                    # Forward StreamProgress objects with context
                    progress = event
                    progress.metadata = progress.metadata or {}
                    progress.metadata.update({
                        "attempt": attempt,
                        "fixing_stage": "ai_generation"
                    })
                    yield progress
                elif isinstance(event, str):
                    accumulated_text += event
                    # Show partial content as it streams
                    yield StreamProgress(
                        stage="generating",
                        message="AI is writing fix code...",
                        progress_percent=55.0,
                        partial_content=accumulated_text[-200:],  # Last 200 chars
                        metadata={
                            "attempt": attempt,
                            "text_length": len(accumulated_text)
                        }
                    )
            
            yield StreamProgress(
                stage="generating",
                message="AI completed generating fixes, parsing results...",
                progress_percent=65.0,
                metadata={"attempt": attempt, "response_length": len(accumulated_text)}
            )
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"AI fix generation failed: {str(e)}",
                progress_percent=0.0,
                metadata={"attempt": attempt, "error": str(e)}
            )
    
    def _create_attempt_memory(self, attempt: int, errors_before: int, errors_after: int, 
                             commands_failed: List[str], files_modified: List[str], 
                             persistent_errors: List[str], success: bool) -> AttemptMemory:
        """Create memory of current attempt"""
        # Generate brief summary (max 50 words)
        summary_parts = []
        if commands_failed:
            summary_parts.append(f"Commands failed: {', '.join(commands_failed[:2])}")
        if files_modified:
            summary_parts.append(f"Modified: {', '.join([f.split('/')[-1] for f in files_modified[:2]])}")
        if persistent_errors:
            summary_parts.append(f"Persistent: {len(persistent_errors)} errors")
        
        brief_summary = "; ".join(summary_parts) if summary_parts else "No changes made"
        if len(brief_summary) > 200:  # Truncate if too long
            brief_summary = brief_summary[:197] + "..."
        
        return AttemptMemory(
            attempt_number=attempt,
            errors_before=errors_before,
            errors_after=errors_after,
            commands_failed=commands_failed,
            files_modified=files_modified,
            persistent_errors=persistent_errors,
            success=success,
            brief_summary=brief_summary
        )
    
    def _get_relevant_history_context(self, max_tokens: int = 300) -> str:
        """Get relevant attempt history context, token-efficient"""
        if not self.attempt_history:
            return ""
        
        # Include only last 2-3 attempts and focus on failures
        recent_attempts = self.attempt_history[-3:]
        context_parts = []
        
        for memory in recent_attempts:
            if not memory.success or memory.commands_failed or memory.persistent_errors:
                context_line = f"Attempt {memory.attempt_number}: {memory.brief_summary}"
                if memory.commands_failed:
                    context_line += f" (Failed commands: {', '.join(memory.commands_failed[:2])})"
                context_parts.append(context_line)
        
        context = "\n".join(context_parts)
        
        # Truncate if too long (estimate ~4 chars per token)
        if len(context) > max_tokens * 4:
            context = context[:max_tokens * 4 - 20] + "..."
        
        return context
    
    def _should_exit_early(self, current_errors: List[str], attempt: int) -> Tuple[bool, str]:
        """Check if we should exit early based on patterns"""
        # Exit if same error repeats 3 times
        current_error_patterns = set(current_errors[:10])  # Check top 10 errors
        
        for error_pattern in current_error_patterns:
            self.repeated_errors[error_pattern] = self.repeated_errors.get(error_pattern, 0) + 1
            if self.repeated_errors[error_pattern] >= 3:
                return True, f"Error pattern repeated 3 times: {error_pattern[:100]}..."
        
        # Exit if no progress after 5 attempts
        if attempt >= 5 and len(self.attempt_history) >= 2:
            recent_attempts = self.attempt_history[-2:]
            if all(not attempt.success for attempt in recent_attempts):
                return True, "No progress in last 2 attempts"
        
        # Exit if error count not decreasing for multiple attempts
        if len(self.attempt_history) >= 3:
            recent_error_counts = [mem.errors_after for mem in self.attempt_history[-3:]]
            if recent_error_counts[0] == recent_error_counts[1] == recent_error_counts[2]:
                return True, "Error count not decreasing for 3 attempts"
        
        return False, ""
    
    def _parse_ai_response_json(self, response_text: str) -> Optional[Dict]:
        """Enhanced JSON parsing with multiple fallback strategies"""
        if not response_text:
            return None
        
        # Strategy 1: Try direct JSON parsing (with JSON_UTILS if available)
        if JSON_UTILS_AVAILABLE:
            result = safe_json_loads(response_text, "AI fix generation", default=None)
            if result:
                return result
        else:
            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError:
                pass
        
        # Strategy 2: Extract JSON from markdown code blocks
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    return json.loads(match.strip())
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Find the largest JSON-like object in the response
        brace_count = 0
        json_start = -1
        
        for i, char in enumerate(response_text):
            if char == '{':
                if brace_count == 0:
                    json_start = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and json_start != -1:
                    json_candidate = response_text[json_start:i+1]
                    try:
                        result = json.loads(json_candidate)
                        if isinstance(result, dict) and result:
                            return result
                    except json.JSONDecodeError:
                        continue
        
        # Strategy 4: Regex-based extraction for common patterns
        try:
            # Look for code_fixes array
            code_fixes_match = re.search(r'"code_fixes"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
            if code_fixes_match:
                # Try to construct a minimal valid JSON
                minimal_json = f'{{"code_fixes": [{code_fixes_match.group(1)}]}}'
                try:
                    return json.loads(minimal_json)
                except json.JSONDecodeError:
                    pass
            
            # Look for shell_commands array
            shell_match = re.search(r'"shell_commands"\s*:\s*\[(.*?)\]', response_text, re.DOTALL)
            if shell_match:
                minimal_json = f'{{"shell_commands": [{shell_match.group(1)}]}}'
                try:
                    return json.loads(minimal_json)
                except json.JSONDecodeError:
                    pass
        
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.CODE_GENERATION, f"Regex extraction failed: {e}",
                           context={"session_id": self.session_id})
        
        # Strategy failure - log and return None
        if MONITORING_AVAILABLE:
            logger.warn(LogCategory.CODE_GENERATION, "All JSON parsing strategies failed",
                       context={"session_id": self.session_id, "response_preview": response_text[:300]})
        
        return None
    
    def _limit_analysis_output(self, output: str, max_errors: int = 10) -> str:
        """Limit analysis output to most relevant errors for token efficiency"""
        if not output:
            return output
        
        lines = output.split('\n')
        error_lines = []
        other_lines = []
        
        # Separate error lines from other output
        for line in lines:
            if ' error:' in line.lower() or ' warning:' in line.lower():
                error_lines.append(line)
            else:
                other_lines.append(line)
        
        # Take only the first max_errors error lines
        limited_errors = error_lines[:max_errors]
        
        # Combine with summary info
        result_lines = []
        
        # Add summary line if we have more errors
        if len(error_lines) > max_errors:
            result_lines.append(f"[Showing {max_errors} of {len(error_lines)} total errors]")
        
        # Add limited errors
        result_lines.extend(limited_errors)
        
        # Add final summary line if present
        for line in other_lines[-3:]:  # Last few lines often contain summary
            if 'error' in line.lower() and 'found' in line.lower():
                result_lines.append(line)
                break
        
        return '\n'.join(result_lines)
    
    def _initialize_session(self):
        """Initialize session components"""
        # Reset and initialize global instances
        reset_error_diff_analyzer()
        reset_comprehensive_logger()
        
        self.diff_analyzer = get_error_diff_analyzer()
        
        log_file_path = None
        if self.config.log_file_path:
            log_file_path = self.config.log_file_path
        elif MONITORING_AVAILABLE:
            log_file_path = f"logs/dart_analysis_recovery_{self.session_id}.json"
        
        self.logger = get_comprehensive_logger(self.session_id, log_file_path)
    
    async def _run_initial_analysis(self, target_path: Optional[str] = None) -> Optional[AnalysisResult]:
        """Run initial Dart analysis"""
        self.logger.log_stage(RecoveryStage.ERROR_CAPTURE)
        
        # Ensure dependencies are up to date first
        if self.config.enable_commands:
            pub_get_result = await self.command_executor.execute_flutter_pub_get()
            self.logger.log_command_execution(pub_get_result, "Initial pub get")
        
        # Run dart analyze
        analysis_result = self.dart_analyzer.run_analysis(target_path)
        
        if analysis_result.success or analysis_result.errors:
            # Take initial snapshot
            snapshot = self.diff_analyzer.take_snapshot(analysis_result, 0, "Initial analysis")
            self.logger.log_error_snapshot(snapshot)
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Initial analysis completed",
                           context={
                               "session_id": self.session_id,
                               "total_errors": len(analysis_result.errors),
                               "total_warnings": len(analysis_result.warnings),
                               "analysis_success": analysis_result.success
                           })
            
            return analysis_result
        else:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, "Initial dart analysis failed",
                           context={"session_id": self.session_id, "output": analysis_result.output})
            return None
    
    async def _iterative_fixing_loop(self, initial_analysis: AnalysisResult, 
                                   target_path: Optional[str] = None) -> Dict[str, Any]:
        """Main iterative fixing loop"""
        current_analysis = initial_analysis
        attempts_made = 0
        total_commands_executed = []
        total_fixes_applied = 0
        total_files_modified = []
        
        for attempt in range(1, self.config.max_attempts + 1):
            if len(current_analysis.errors) == 0:
                break  # No more errors to fix
            
            # Check for early exit conditions
            current_error_messages = [str(error) for error in current_analysis.errors[:10]]
            should_exit, exit_reason = self._should_exit_early(current_error_messages, attempt)
            if should_exit:
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Early exit: {exit_reason}",
                               context={"session_id": self.session_id, "attempt": attempt})
                break
            
            attempts_made = attempt
            errors_before = len(current_analysis.errors)
            self.logger.start_attempt(attempt, errors_before)
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Starting fixing attempt {attempt}/{self.config.max_attempts}",
                           context={
                               "session_id": self.session_id,
                               "errors_to_fix": len(current_analysis.errors),
                               "warnings": len(current_analysis.warnings)
                           })
            
            try:
                # Step 1: Analyze what commands might help
                attempt_commands = []
                if self.config.enable_commands:
                    commands_result = await self._execute_helpful_commands(current_analysis)
                    attempt_commands.extend(commands_result["commands_executed"])
                
                # Step 2: Apply AI-generated fixes (includes shell command execution)
                fixes_result = await self._apply_ai_fixes(current_analysis, attempt)
                
                # Update tracking with AI-executed commands
                attempt_commands.extend(fixes_result.get("commands_executed", []))
                
                # Step 3: Run dart analyze again
                new_analysis = self.dart_analyzer.run_analysis(target_path)
                
                # Step 4: Analyze progress
                if new_analysis.success or new_analysis.errors:
                    snapshot = self.diff_analyzer.take_snapshot(new_analysis, attempt, f"After attempt {attempt}")
                    self.logger.log_error_snapshot(snapshot)
                    
                    diff = self.diff_analyzer.analyze_diff()
                    if diff:
                        self.logger.log_error_diff(diff)
                else:
                    new_analysis = current_analysis  # Fallback if analysis failed
                
                # Update tracking
                total_commands_executed.extend(attempt_commands)
                total_fixes_applied += fixes_result.get("fixes_applied", 0)
                total_files_modified.extend(fixes_result.get("files_modified", []))
                
                # Check if we made progress
                error_reduction = len(current_analysis.errors) - len(new_analysis.errors)
                success = error_reduction > 0 or len(new_analysis.errors) == 0
                errors_after = len(new_analysis.errors)
                
                # Identify persistent errors (same error messages)
                old_error_msgs = set(str(e) for e in current_analysis.errors[:10])
                new_error_msgs = set(str(e) for e in new_analysis.errors[:10])
                persistent_errors = list(old_error_msgs & new_error_msgs)
                
                # Track failed commands
                failed_commands = [cmd for cmd, exec_result in zip(attempt_commands, []) 
                                 if hasattr(exec_result, 'success') and not exec_result.success]
                
                # Create and store attempt memory
                attempt_memory = self._create_attempt_memory(
                    attempt=attempt,
                    errors_before=errors_before,
                    errors_after=errors_after,
                    commands_failed=failed_commands,
                    files_modified=fixes_result.get("files_modified", []),
                    persistent_errors=persistent_errors,
                    success=success
                )
                self.attempt_history.append(attempt_memory)
                
                self.logger.end_attempt(success, errors_after)
                current_analysis = new_analysis
                
                # If no progress and we have diff data, consider stopping early
                if not success and diff and diff.progress_score < 0.1 and attempt > 2:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Low progress score, considering early termination",
                                   context={
                                       "session_id": self.session_id,
                                       "attempt": attempt,
                                       "progress_score": diff.progress_score
                                   })
                    # Continue for now, but this could be a stopping condition
                
            except Exception as e:
                error_msg = f"Error in attempt {attempt}: {str(e)}"
                self.logger.end_attempt(False, error_message=error_msg)
                
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.ERROR_FIXING, error_msg,
                               context={"session_id": self.session_id, "attempt": attempt})
                continue
        
        return {
            "attempts_made": attempts_made,
            "commands_executed": total_commands_executed,
            "fixes_applied": total_fixes_applied,
            "files_modified": total_files_modified
        }
    
    async def _execute_helpful_commands(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """Execute commands that might help fix the errors"""
        self.logger.log_stage(RecoveryStage.COMMAND_PLANNING)
        
        commands_executed = []
        
        # Get command suggestions based on error output
        suggestions = self.command_executor.get_command_suggestions(analysis_result.output)
        
        self.logger.log_stage(RecoveryStage.COMMAND_EXECUTION)
        
        for command_type, args in suggestions:
            try:
                result = await self.command_executor.execute_command(command_type, args)
                commands_executed.append(result.command)
                self.logger.log_command_execution(result, f"Suggested command for error fixing")
                
                # Small delay between commands
                await asyncio.sleep(1)
                
            except Exception as e:
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.SHELL_CMD, f"Failed to execute suggested command {command_type}: {e}",
                               context={"session_id": self.session_id})
        
        # Always try dart fix if enabled
        if self.config.enable_dart_fix:
            try:
                dart_fix_result = await self.command_executor.execute_dart_fix(apply=True)
                commands_executed.append(dart_fix_result.command)
                self.logger.log_command_execution(dart_fix_result, "Automatic dart fix")
            except Exception as e:
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.SHELL_CMD, f"Failed to run dart fix: {e}",
                               context={"session_id": self.session_id})
        
        return {"commands_executed": commands_executed}
    
    async def _apply_ai_fixes(self, analysis_result: AnalysisResult, attempt: int) -> Dict[str, Any]:
        """Apply AI-generated fixes using LLM and direct file writing"""
        self.logger.log_stage(RecoveryStage.FIX_GENERATION)
        
        fixes_applied = 0
        files_modified = []
        attempt_commands = []
        
        try:
            # Load the comprehensive fixing prompt
            try:
                fix_prompt_info = self.prompt_loader.get_prompt_info("Dart Analysis Command Fixer")
                fix_prompt = fix_prompt_info["prompt"]
            except KeyError:
                # Fallback to existing prompt
                fix_prompt_info = self.prompt_loader.get_prompt_info("Generate Fixed Files")
                fix_prompt = fix_prompt_info["prompt"]
            
            # Limit analysis output to most relevant errors (token efficiency)
            limited_output = self._limit_analysis_output(analysis_result.output, max_errors=10)
            
            # Prepare context for the prompt
            context = {
                "project_path": str(self.project_path),
                "attempt_number": attempt,
                "max_attempts": self.config.max_attempts,
                "analysis_output": limited_output,
                "error_count": len(analysis_result.errors),
                "warning_count": len(analysis_result.warnings),
                "categorized_errors": self.dart_analyzer.categorize_errors(analysis_result.issues),
                "previous_attempts": self._get_relevant_history_context()
            }
            
            # Execute LLM request
            messages = [{"role": "user", "content": fix_prompt.format(**context)}]
            
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Requesting AI fixes for {len(analysis_result.errors)} errors",
                           context={"session_id": self.session_id, "attempt": attempt})
            
            response = self.llm_executor.execute(messages)
            
            if response and response.text:
                # First, parse and execute any shell commands in the response
                shell_commands, shell_executions = await self.shell_parser.parse_and_execute(response.text)
                
                # Log shell command executions
                for execution in shell_executions:
                    # Create a fake CommandResult for logging compatibility
                    fake_result = CommandResult(
                        success=execution.success,
                        command=execution.command,
                        args=[],
                        exit_code=execution.exit_code,
                        stdout=execution.stdout,
                        stderr=execution.stderr,
                        execution_time=execution.execution_time,
                        error_message=execution.error_message
                    )
                    self.logger.log_command_execution(fake_result, "AI-suggested shell command")
                
                # Update tracking with shell commands
                attempt_commands.extend([exec.command for exec in shell_executions])
                
                # Then parse the response for code fixes
                if MONITORING_AVAILABLE:
                    logger.debug(LogCategory.CODE_GENERATION, f"AI response for parsing: {response.text[:500]}...",
                               context={"session_id": self.session_id, "attempt": attempt})
                
                # Enhanced JSON parsing with fallback mechanisms
                fix_data = self._parse_ai_response_json(response.text)
                
                # Check for both possible formats: "fixes" or "code_fixes"
                fixes_to_apply = None
                if fix_data:
                    fixes_to_apply = fix_data.get("code_fixes") or fix_data.get("fixes")
                    
                    if MONITORING_AVAILABLE:
                        logger.debug(LogCategory.CODE_GENERATION, f"Parsed fix data keys: {list(fix_data.keys()) if fix_data else 'None'}",
                                   context={"session_id": self.session_id, "fixes_found": len(fixes_to_apply) if fixes_to_apply else 0})
                
                if fixes_to_apply:
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.CODE_GENERATION, f"Applying {len(fixes_to_apply)} code fixes",
                                  context={"session_id": self.session_id, "attempt": attempt})
                    
                    # Apply fixes
                    self.logger.log_stage(RecoveryStage.FIX_APPLICATION)
                    apply_result = await self._apply_fixes_direct(fixes_to_apply)
                    
                    fixes_applied = apply_result.get("fixes_applied", 0)
                    files_modified = apply_result.get("files_modified", [])
                else:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.CODE_GENERATION, "No code fixes found in AI response, only shell commands",
                                  context={"session_id": self.session_id, "shell_commands_executed": len(shell_executions)})
                    
                    # If no structured fixes but shell commands were executed, that's still progress
                    fixes_applied = len([exec for exec in shell_executions if exec.success])
                    files_modified = []
        
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"AI fix generation failed: {e}",
                           context={"session_id": self.session_id, "attempt": attempt})
        
        return {
            "fixes_applied": fixes_applied,
            "files_modified": files_modified,
            "commands_executed": attempt_commands
        }
    
    async def _apply_fixes_direct(self, fixes: List[Dict]) -> Dict[str, Any]:
        """Apply fixes by writing complete file contents directly"""
        fixes_applied = 0
        files_modified = []
        
        try:
            for fix in fixes:
                file_path = fix.get("file_path")
                file_content = fix.get("file_content") or fix.get("edit_snippet")  # Support both formats
                
                if not file_path or not file_content:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Skipping invalid fix: missing file_path or content",
                                  context={"session_id": self.session_id, "fix": fix})
                    continue
                
                # Resolve full file path
                full_file_path = self.project_path / file_path
                
                # Create backup before modifying
                backup_content = None
                try:
                    if full_file_path.exists():
                        with open(full_file_path, 'r', encoding='utf-8') as f:
                            backup_content = f.read()
                except Exception as e:
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, f"Could not read file for backup: {e}",
                                  context={"session_id": self.session_id, "file_path": file_path})
                
                # Write new content
                try:
                    # Ensure directory exists
                    full_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(full_file_path, 'w', encoding='utf-8') as f:
                        f.write(file_content)
                    
                    fixes_applied += 1
                    files_modified.append(file_path)
                    self.logger.log_fix_application(file_path, True)
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.CODE_MOD, f"File written successfully: {file_path}",
                                  context={"session_id": self.session_id, "content_length": len(file_content)})
                        
                except Exception as e:
                    error_msg = f"Failed to write file {file_path}: {str(e)}"
                    self.logger.log_fix_application(file_path, False, error_msg)
                    
                    # Attempt to restore backup if we have one
                    if backup_content:
                        try:
                            with open(full_file_path, 'w', encoding='utf-8') as f:
                                f.write(backup_content)
                            if MONITORING_AVAILABLE:
                                logger.info(LogCategory.ERROR_FIXING, f"Restored backup for {file_path}")
                        except:
                            pass  # Backup restore failed, but original error is more important
                    
                    if MONITORING_AVAILABLE:
                        logger.error(LogCategory.ERROR_FIXING, error_msg,
                                   context={"session_id": self.session_id})
            
            return {
                "fixes_applied": fixes_applied,
                "files_modified": files_modified,
                "total_fixes_attempted": len(fixes)
            }
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Direct fix application failed: {e}",
                           context={"session_id": self.session_id})
            return {"fixes_applied": 0, "files_modified": []}
    
    async def _apply_quick_typo_fixes(self, analysis_result: AnalysisResult, target_path: Optional[str] = None) -> int:
        """
        Apply quick typo fixes before running the expensive AI pipeline
        Returns number of fixes applied
        """
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, "Running quick typo detection and fixes",
                       context={"session_id": self.session_id, "errors": len(analysis_result.errors)})
        
        fixes_applied = 0
        
        try:
            # Analyze the dart analyze output for typos
            typo_analysis = self.typo_fixer.analyze_dart_errors(analysis_result.output)
            
            if typo_analysis["typos_found"] > 0:
                auto_fixable_typos = typo_analysis["auto_fixable"]
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Found {len(auto_fixable_typos)} auto-fixable typos",
                               context={"session_id": self.session_id})
                
                # Apply each auto-fixable typo fix
                for typo in auto_fixable_typos:
                    file_path = self.project_path / typo["file"]
                    
                    if file_path.exists():
                        fix_result = self.typo_fixer.fix_specific_typo(
                            file_path, 
                            typo["line"], 
                            typo["original"], 
                            typo["corrected"]
                        )
                        
                        if fix_result["success"]:
                            fixes_applied += 1
                            if MONITORING_AVAILABLE:
                                logger.info(LogCategory.ERROR_FIXING, f"Fixed typo: {typo['original']} → {typo['corrected']}",
                                           context={
                                               "session_id": self.session_id,
                                               "file": typo["file"],
                                               "line": typo["line"]
                                           })
                        else:
                            if MONITORING_AVAILABLE:
                                logger.warn(LogCategory.ERROR_FIXING, f"Failed to fix typo: {fix_result.get('error', 'Unknown error')}",
                                           context={"session_id": self.session_id, "typo": typo})
            
            # Also try general file-based typo fixes for common patterns
            dart_files = list(self.project_path.glob("lib/**/*.dart"))
            for dart_file in dart_files:
                file_fix_result = self.typo_fixer.fix_typos_in_file(dart_file)
                if file_fix_result["success"] and file_fix_result["file_modified"]:
                    fixes_applied += file_fix_result["fixes_applied"]
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.ERROR_FIXING, f"Applied {file_fix_result['fixes_applied']} pattern fixes to {dart_file.name}",
                                   context={"session_id": self.session_id})
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.ERROR_FIXING, f"Quick typo fixing failed: {e}",
                           context={"session_id": self.session_id})
        
        return fixes_applied
    
    async def _run_final_validation(self, target_path: Optional[str] = None) -> Optional[AnalysisResult]:
        """Run final validation analysis"""
        self.logger.log_stage(RecoveryStage.VALIDATION)
        
        # Wait a moment for file system changes
        await asyncio.sleep(2)
        
        # Run final analysis
        final_analysis = self.dart_analyzer.run_analysis(target_path)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"Final validation completed",
                       context={
                           "session_id": self.session_id,
                           "final_errors": len(final_analysis.errors),
                           "final_warnings": len(final_analysis.warnings),
                           "analysis_success": final_analysis.success
                       })
        
        return final_analysis
    
    def _create_error_result(self, error_message: str, start_time: float) -> FixingResult:
        """Create an error result"""
        return FixingResult(
            success=False,
            initial_error_count=0,
            final_error_count=0,
            attempts_made=0,
            commands_executed=[],
            fixes_applied=0,
            files_modified=[],
            total_duration=time.time() - start_time,
            error_message=error_message,
            recovery_log=self.logger.get_session_summary() if self.logger else None
        )


# Utility functions for easy access
async def fix_dart_errors(project_path: str, config: Optional[FixingConfig] = None) -> FixingResult:
    """Convenience function to fix Dart errors in a project"""
    fixer = DartAnalysisFixer(project_path, config)
    return await fixer.fix_all_errors()

def create_fixing_config(max_attempts: int = 5, enable_commands: bool = True, 
                        log_file_path: Optional[str] = None) -> FixingConfig:
    """Create a fixing configuration"""
    return FixingConfig(
        max_attempts=max_attempts,
        enable_commands=enable_commands,
        log_file_path=log_file_path
    )