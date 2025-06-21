"""
Iterative Error Fixer Service
Implements the core fix-analyze loop similar to steve-backend's DartAnalysisFixer
"""

import asyncio
import time
import os
from typing import List, Dict, Set, Optional, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path

from .dart_analysis import DartAnalysisService, AnalysisResult, AnalysisIssue, AnalysisType
from .llm_executor import SimpleLLMExecutor, LLMResponse

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel
    from utils.request_tracer import tracer, EventContext, TraceEventType
    from utils.performance_monitor import performance_monitor, TimingContext
    from utils.error_analyzer import error_analyzer
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Empty context manager for backward compatibility
class EmptyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@dataclass
class FixAttempt:
    """Represents a single fix attempt"""
    attempt_number: int
    errors_before: int
    errors_after: int
    files_modified: List[str]
    success: bool
    time_taken: float
    error_summary: str


@dataclass
class FixingResult:
    """Result of the iterative fixing process"""
    success: bool
    total_attempts: int
    initial_errors: int
    final_errors: int
    files_modified: Set[str]
    attempts: List[FixAttempt]
    total_time: float
    final_analysis: Optional[AnalysisResult] = None
    error_message: Optional[str] = None


class IterativeErrorFixer:
    """
    Service that iteratively analyzes and fixes Dart code errors
    Based on steve-backend's DartAnalysisFixer but adapted for flutter-server
    """
    
    def __init__(self, project_path: str, llm_executor: Optional[SimpleLLMExecutor] = None):
        self.project_path = Path(project_path)
        self.analysis_service = DartAnalysisService(str(self.project_path))
        self.llm_executor = llm_executor or SimpleLLMExecutor()
        
        # Configuration
        self.max_history = 6  # Keep last 6 conversations for context
        self.conversation_history = []
        
        # Status callback for real-time updates
        self.status_callback: Optional[Callable[[str], None]] = None
        
        # Error fixing prompts
        self.fix_errors_prompt = """
You are a Flutter/Dart expert. Fix the compilation errors in the provided code.

Current Analysis Errors:
{error_details}

Current File Contents:
{file_contents}

Instructions:
1. Analyze each error carefully
2. Fix ALL errors while preserving existing functionality
3. Maintain proper Dart/Flutter coding standards
4. Keep imports organized and only include necessary ones
5. Ensure the code follows Material Design patterns if applicable

For each file that needs changes, provide the complete fixed file content:

<files path="lib/example.dart">
// Complete corrected file content here
</files>

Focus on the most critical errors first:
- Undefined methods/variables
- Import errors
- Type errors
- Syntax errors

Provide ONLY the corrected file contents, no explanations.
        """
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates"""
        self.status_callback = callback
    
    def _update_status(self, message: str):
        """Send status update if callback is set"""
        if self.status_callback:
            self.status_callback(message)
        print(f"[IterativeErrorFixer] {message}")
    
    async def fix_all_errors(self, max_attempts: int = 16) -> FixingResult:
        """
        Main method to iteratively fix all errors
        
        Args:
            max_attempts: Maximum number of fix attempts
            
        Returns:
            FixingResult with detailed information about the fixing process
        """
        start_time = time.time()
        attempts = []
        files_modified = set()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, "Starting iterative error fixing process",
                       context={
                           "max_attempts": max_attempts,
                           "project_path": str(self.project_path)
                       })
        
        self._update_status("Starting iterative error fixing process...")
        
        # Step 1: Run flutter pub get to ensure dependencies are up to date
        self._update_status("Running flutter pub get to update dependencies...")
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.ERROR_FIXING, "Running flutter pub get")
        
        pub_get_success, pub_get_output = self.analysis_service.run_flutter_pub_get()
        if not pub_get_success:
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.ERROR_FIXING, f"flutter pub get failed: {pub_get_output}")
            self._update_status(f"Warning: flutter pub get failed: {pub_get_output}")
        else:
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, "Dependencies updated successfully")
            self._update_status("Dependencies updated successfully")
        
        # Step 2: Initial analysis
        self._update_status("Running initial Dart analysis...")
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.ERROR_FIXING, "Running initial Dart analysis")
        
        initial_analysis = self.analysis_service.run_analysis()
        initial_errors = len(initial_analysis.errors)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"Initial analysis completed",
                       context={
                           "initial_errors_count": initial_errors,
                           "warnings_count": len(initial_analysis.warnings),
                           "analysis_success": initial_analysis.success,
                           "analysis_time_seconds": round(initial_analysis.execution_time, 2)
                       })
        
        if initial_analysis.success:
            self._update_status("No errors found! Code is already clean ✅")
            return FixingResult(
                success=True,
                total_attempts=0,
                initial_errors=0,
                final_errors=0,
                files_modified=set(),
                attempts=[],
                total_time=time.time() - start_time,
                final_analysis=initial_analysis
            )
        
        self._update_status(f"Found {initial_errors} errors to fix")
        self._update_status(f"Error summary:\n{self.analysis_service.format_error_summary(initial_analysis.errors)}")
        
        # Step 3: Iterative fixing loop
        current_analysis = initial_analysis
        
        for attempt_num in range(1, max_attempts + 1):
            attempt_start = time.time()
            self._update_status(f"Starting fix attempt {attempt_num}/{max_attempts}")
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Starting fix attempt {attempt_num}",
                           context={
                               "attempt_number": attempt_num,
                               "max_attempts": max_attempts,
                               "current_errors": len(current_analysis.errors)
                           })
            
            errors_before = len(current_analysis.errors)
            
            if errors_before == 0:
                self._update_status("All errors fixed! 🎉")
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, "All errors fixed successfully")
                break
            
            # Generate fixes for current errors
            self._update_status(f"Generating fixes for {errors_before} errors...")
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, f"Generating fixes for {errors_before} errors")
            
            fixes_applied, modified_files = await self._fix_current_errors(current_analysis.errors)
            
            if modified_files:
                files_modified.update(modified_files)
                self._update_status(f"Applied fixes to {len(modified_files)} files: {', '.join(modified_files)}")
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, f"Applied fixes to {len(modified_files)} files",
                               context={"modified_files": list(modified_files)})
            else:
                self._update_status("No fixes could be generated for current errors")
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.ERROR_FIXING, "No fixes could be generated for current errors")
            
            # Re-analyze after fixes
            self._update_status("Re-analyzing code after fixes...")
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.ERROR_FIXING, "Re-analyzing code after fixes")
            
            current_analysis = self.analysis_service.run_analysis()
            errors_after = len(current_analysis.errors)
            
            attempt_time = time.time() - attempt_start
            attempt = FixAttempt(
                attempt_number=attempt_num,
                errors_before=errors_before,
                errors_after=errors_after,
                files_modified=list(modified_files),
                success=errors_after == 0,
                time_taken=attempt_time,
                error_summary=self.analysis_service.format_error_summary(current_analysis.errors) if current_analysis.errors else "No errors"
            )
            attempts.append(attempt)
            
            # Enhanced logging for attempt results
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.ERROR_FIXING, f"Fix attempt {attempt_num} completed",
                           context={
                               "attempt_number": attempt_num,
                               "errors_before": errors_before,
                               "errors_after": errors_after,
                               "errors_fixed": errors_before - errors_after,
                               "files_modified": list(modified_files),
                               "attempt_success": errors_after == 0,
                               "attempt_time_seconds": round(attempt_time, 2),
                               "progress_made": errors_after < errors_before
                           })
            
            if errors_after == 0:
                self._update_status("All errors fixed successfully! ✅")
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, "All errors fixed successfully")
                break
            elif errors_after >= errors_before:
                self._update_status(f"No progress made: {errors_after} errors remain (was {errors_before})")
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.ERROR_FIXING, f"No progress made in attempt {attempt_num}",
                               context={"errors_before": errors_before, "errors_after": errors_after})
                if attempt_num > 3:  # Give it a few tries before considering stagnation
                    self._update_status("Multiple attempts without progress. May need manual intervention.")
                    if MONITORING_AVAILABLE:
                        logger.warn(LogCategory.ERROR_FIXING, "Multiple attempts without progress")
            else:
                progress_msg = f"Progress: {errors_before} → {errors_after} errors ({errors_before - errors_after} fixed)"
                self._update_status(progress_msg)
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.ERROR_FIXING, progress_msg)
        
        # Step 4: Final analysis and web build test
        final_success = len(current_analysis.errors) == 0
        
        if final_success:
            self._update_status("Running final validation build...")
            build_success = await self._test_build()
            if build_success:
                self._update_status("Build test passed! Code is ready 🚀")
            else:
                self._update_status("Warning: Build test failed despite no analysis errors")
                final_success = False
        
        total_time = time.time() - start_time
        
        result = FixingResult(
            success=final_success,
            total_attempts=len(attempts),
            initial_errors=initial_errors,
            final_errors=len(current_analysis.errors),
            files_modified=files_modified,
            attempts=attempts,
            total_time=total_time,
            final_analysis=current_analysis,
            error_message=None if final_success else f"Failed to fix all errors after {max_attempts} attempts"
        )
        
        # Enhanced final logging
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"Iterative error fixing completed",
                       context={
                           "success": final_success,
                           "total_attempts": len(attempts),
                           "initial_errors": initial_errors,
                           "final_errors": len(current_analysis.errors),
                           "errors_fixed": initial_errors - len(current_analysis.errors),
                           "files_modified": list(files_modified),
                           "total_time_seconds": round(total_time, 2),
                           "average_time_per_attempt": round(total_time / len(attempts), 2) if attempts else 0,
                           "max_attempts": max_attempts
                       })
        
        # Final status update
        if final_success:
            self._update_status(f"✅ All errors fixed in {len(attempts)} attempts ({total_time:.1f}s)")
        else:
            self._update_status(f"❌ {len(current_analysis.errors)} errors remain after {max_attempts} attempts")
        
        return result
    
    async def _fix_current_errors(self, errors: List[AnalysisIssue]) -> Tuple[bool, Set[str]]:
        """
        Generate and apply fixes for current errors
        
        Returns:
            Tuple of (fixes_applied, modified_files)
        """
        if not errors:
            return False, set()
        
        # Group errors by file for more efficient fixing
        errors_by_file = {}
        for error in errors:
            file_path = error.file_path
            if file_path not in errors_by_file:
                errors_by_file[file_path] = []
            errors_by_file[file_path].append(error)
        
        modified_files = set()
        
        # Process each file's errors
        for file_path, file_errors in errors_by_file.items():
            try:
                if await self._fix_file_errors(file_path, file_errors):
                    modified_files.add(file_path)
            except Exception as e:
                self._update_status(f"Error fixing {file_path}: {str(e)}")
        
        return len(modified_files) > 0, modified_files
    
    async def _fix_file_errors(self, file_path: str, errors: List[AnalysisIssue]) -> bool:
        """Fix errors in a specific file"""
        
        # Read current file content
        full_file_path = self.project_path / file_path
        if not full_file_path.exists():
            self._update_status(f"File not found: {file_path}")
            return False
        
        try:
            with open(full_file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
        except Exception as e:
            self._update_status(f"Error reading {file_path}: {str(e)}")
            return False
        
        # Format error details for LLM
        error_details = []
        for error in errors:
            error_details.append(
                f"Line {error.line}:{error.column} - {error.type.value}: {error.message}"
            )
        
        error_details_str = "\n".join(error_details)
        
        # Prepare LLM prompt
        messages = [
            {
                "role": "user",
                "content": self.fix_errors_prompt.format(
                    error_details=error_details_str,
                    file_contents=f"=== {file_path} ===\n{current_content}"
                )
            }
        ]
        
        # Add conversation history for context
        if self.conversation_history:
            context_messages = self.conversation_history[-self.max_history:]
            messages = context_messages + messages
        
        try:
            # Get fix from LLM
            response = self.llm_executor.execute(messages)
            
            # Update conversation history
            self.conversation_history.append({
                "role": "user", 
                "content": f"Fix errors in {file_path}: {error_details_str}"
            })
            self.conversation_history.append({
                "role": "assistant", 
                "content": response.text
            })
            
            # Parse and apply the fix
            fixed_content = self._extract_file_content(response.text, file_path)
            
            if fixed_content and fixed_content != current_content:
                # Write the fixed content
                with open(full_file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                self._update_status(f"Applied fixes to {file_path}")
                return True
            else:
                self._update_status(f"No changes generated for {file_path}")
                return False
                
        except Exception as e:
            self._update_status(f"Error generating fix for {file_path}: {str(e)}")
            return False
    
    def _extract_file_content(self, llm_output: str, target_file: str) -> Optional[str]:
        """Extract file content from LLM output using <files> tags"""
        import re
        
        # Look for <files path="target_file">content</files>
        pattern = rf'<files\s+path="{re.escape(target_file)}"\s*>(.*?)</files>'
        match = re.search(pattern, llm_output, re.DOTALL)
        
        if match:
            content = match.group(1).strip()
            # Remove any leading/trailing whitespace but preserve code formatting
            return content
        
        # Fallback: if the entire output looks like code and we only have one file, use it
        if target_file in llm_output and '```' not in llm_output:
            # Remove any explanatory text before the code
            lines = llm_output.split('\n')
            code_lines = []
            in_code = False
            
            for line in lines:
                if 'import ' in line or 'class ' in line or 'void ' in line:
                    in_code = True
                if in_code:
                    code_lines.append(line)
            
            if code_lines:
                return '\n'.join(code_lines)
        
        return None
    
    async def _test_build(self) -> bool:
        """Test if the code builds successfully"""
        try:
            self._update_status("Testing flutter build web --debug...")
            
            import subprocess
            result = subprocess.run(
                ["flutter", "build", "web", "--debug"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            success = result.returncode == 0
            
            if not success:
                error_output = result.stderr + result.stdout
                self._update_status(f"Build failed: {error_output[-500:]}")  # Last 500 chars
            
            return success
            
        except subprocess.TimeoutExpired:
            self._update_status("Build test timed out after 5 minutes")
            return False
        except Exception as e:
            self._update_status(f"Build test error: {str(e)}")
            return False
    
    def get_fixing_statistics(self, result: FixingResult) -> Dict:
        """Generate detailed statistics about the fixing process"""
        if not result.attempts:
            return {"message": "No fixing attempts made"}
        
        stats = {
            "total_time": f"{result.total_time:.1f}s",
            "success": result.success,
            "error_reduction": result.initial_errors - result.final_errors,
            "files_modified": len(result.files_modified),
            "attempts": []
        }
        
        for attempt in result.attempts:
            stats["attempts"].append({
                "attempt": attempt.attempt_number,
                "errors_before": attempt.errors_before,
                "errors_after": attempt.errors_after,
                "progress": attempt.errors_before - attempt.errors_after,
                "time": f"{attempt.time_taken:.1f}s",
                "files_modified": len(attempt.files_modified)
            })
        
        return stats