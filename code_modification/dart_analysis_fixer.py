"""
Dart Analysis Fixer
Comprehensive error recovery system with iterative fixing, command execution, and robust validation
Based on steve-backend patterns but enhanced for Flutter development
"""

import asyncio
import time
import json
import os
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
    from utils.advanced_logger import logger, LogCategory, LogLevel
    from utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


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
            
            attempts_made = attempt
            self.logger.start_attempt(attempt, len(current_analysis.errors))
            
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
                
                self.logger.end_attempt(success, len(new_analysis.errors))
                
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
            
            # Prepare context for the prompt
            context = {
                "project_path": str(self.project_path),
                "attempt_number": attempt,
                "max_attempts": self.config.max_attempts,
                "analysis_output": analysis_result.output,
                "error_count": len(analysis_result.errors),
                "warning_count": len(analysis_result.warnings),
                "categorized_errors": self.dart_analyzer.categorize_errors(analysis_result.issues)
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
                
                if JSON_UTILS_AVAILABLE:
                    fix_data = safe_json_loads(response.text, "AI fix generation", default=None)
                else:
                    try:
                        fix_data = json.loads(response.text.strip())
                    except json.JSONDecodeError:
                        if MONITORING_AVAILABLE:
                            logger.warn(LogCategory.CODE_GENERATION, "Failed to parse AI response as JSON",
                                      context={"session_id": self.session_id, "response_preview": response.text[:200]})
                        fix_data = None
                
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