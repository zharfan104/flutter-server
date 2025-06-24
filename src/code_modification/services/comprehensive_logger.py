"""
Comprehensive Logger for Error Recovery
Enhanced logging with structured data, metrics, and recovery-specific context
"""

import time
import json
import os
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path

# Import existing logging infrastructure
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Import recovery components
from .command_executor import CommandResult
from .error_diff_analyzer import ErrorDiff, ErrorSnapshot


class RecoveryStage(Enum):
    """Stages of error recovery process"""
    INITIALIZATION = "initialization"
    ERROR_CAPTURE = "error_capture"
    ERROR_ANALYSIS = "error_analysis"
    COMMAND_PLANNING = "command_planning"
    COMMAND_EXECUTION = "command_execution"
    FIX_GENERATION = "fix_generation"
    FIX_APPLICATION = "fix_application"
    VALIDATION = "validation"
    PROGRESS_ANALYSIS = "progress_analysis"
    COMPLETION = "completion"
    FAILURE = "failure"


@dataclass
class RecoveryMetrics:
    """Metrics for a recovery session"""
    session_id: str
    start_time: float
    end_time: Optional[float] = None
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    commands_executed: int = 0
    fixes_applied: int = 0
    files_modified: int = 0
    initial_error_count: int = 0
    final_error_count: int = 0
    total_duration: Optional[float] = None
    success: bool = False


@dataclass
class AttemptLog:
    """Log entry for a single recovery attempt"""
    attempt_number: int
    stage: RecoveryStage
    timestamp: float
    duration: Optional[float] = None
    success: bool = False
    error_count_before: Optional[int] = None
    error_count_after: Optional[int] = None
    commands_executed: List[str] = None
    fixes_applied: int = 0
    files_modified: List[str] = None
    error_message: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ComprehensiveLogger:
    """
    Enhanced logger for error recovery with structured data and metrics
    """
    
    def __init__(self, session_id: Optional[str] = None, log_file_path: Optional[str] = None):
        self.session_id = session_id or f"recovery_{int(time.time())}"
        self.start_time = time.time()
        
        # Initialize metrics
        self.metrics = RecoveryMetrics(
            session_id=self.session_id,
            start_time=self.start_time
        )
        
        # Initialize logs
        self.attempt_logs: List[AttemptLog] = []
        self.stage_logs: List[Dict[str, Any]] = []
        self.command_logs: List[Dict[str, Any]] = []
        self.current_attempt: Optional[int] = None
        self.current_stage: Optional[RecoveryStage] = None
        
        # File logging
        self.log_file_path = log_file_path
        if self.log_file_path:
            self._ensure_log_directory()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, f"ComprehensiveLogger initialized",
                       context={
                           "session_id": self.session_id,
                           "log_file": self.log_file_path
                       })
        
        self.log_recovery_start()
    
    def _ensure_log_directory(self):
        """Ensure log directory exists"""
        if self.log_file_path:
            log_dir = Path(self.log_file_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_recovery_start(self, initial_error_count: Optional[int] = None):
        """Log the start of recovery session"""
        if initial_error_count is not None:
            self.metrics.initial_error_count = initial_error_count
        
        self.log_stage(RecoveryStage.INITIALIZATION, {
            "session_id": self.session_id,
            "initial_error_count": initial_error_count,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat()
        })
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"🔧 Recovery session started",
                       context={
                           "session_id": self.session_id,
                           "initial_errors": initial_error_count
                       })
    
    def log_recovery_end(self, success: bool, final_error_count: Optional[int] = None,
                        error_message: Optional[str] = None):
        """Log the end of recovery session"""
        self.metrics.end_time = time.time()
        self.metrics.total_duration = self.metrics.end_time - self.metrics.start_time
        self.metrics.success = success
        
        if final_error_count is not None:
            self.metrics.final_error_count = final_error_count
        
        stage = RecoveryStage.COMPLETION if success else RecoveryStage.FAILURE
        
        self.log_stage(stage, {
            "session_id": self.session_id,
            "success": success,
            "final_error_count": final_error_count,
            "total_duration": self.metrics.total_duration,
            "error_message": error_message,
            "metrics": asdict(self.metrics)
        })
        
        if MONITORING_AVAILABLE:
            status_emoji = "✅" if success else "❌"
            logger.info(LogCategory.ERROR_FIXING, 
                       f"{status_emoji} Recovery session {'completed' if success else 'failed'}",
                       context={
                           "session_id": self.session_id,
                           "success": success,
                           "duration_seconds": round(self.metrics.total_duration, 2),
                           "attempts": self.metrics.total_attempts,
                           "final_errors": final_error_count,
                           "error_message": error_message
                       })
        
        # Write final log to file
        if self.log_file_path:
            self._write_session_log()
    
    def start_attempt(self, attempt_number: int, error_count_before: Optional[int] = None):
        """Start logging a new recovery attempt"""
        self.current_attempt = attempt_number
        self.metrics.total_attempts = max(self.metrics.total_attempts, attempt_number)
        
        attempt_log = AttemptLog(
            attempt_number=attempt_number,
            stage=RecoveryStage.ERROR_ANALYSIS,
            timestamp=time.time(),
            error_count_before=error_count_before,
            commands_executed=[],
            files_modified=[]
        )
        
        self.attempt_logs.append(attempt_log)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, f"🔄 Starting recovery attempt {attempt_number}",
                       context={
                           "session_id": self.session_id,
                           "attempt_number": attempt_number,
                           "errors_before": error_count_before
                       })
    
    def end_attempt(self, success: bool, error_count_after: Optional[int] = None,
                   error_message: Optional[str] = None):
        """End the current recovery attempt"""
        if not self.attempt_logs:
            return
        
        attempt_log = self.attempt_logs[-1]
        attempt_log.success = success
        attempt_log.duration = time.time() - attempt_log.timestamp
        attempt_log.error_count_after = error_count_after
        attempt_log.error_message = error_message
        
        if success:
            self.metrics.successful_attempts += 1
        else:
            self.metrics.failed_attempts += 1
        
        if MONITORING_AVAILABLE:
            status_emoji = "✅" if success else "❌"
            logger.info(LogCategory.ERROR_FIXING, 
                       f"{status_emoji} Attempt {self.current_attempt} {'succeeded' if success else 'failed'}",
                       context={
                           "session_id": self.session_id,
                           "attempt_number": self.current_attempt,
                           "success": success,
                           "duration_seconds": round(attempt_log.duration, 2),
                           "errors_after": error_count_after,
                           "error_message": error_message
                       })
        
        self.current_attempt = None
    
    def log_stage(self, stage: RecoveryStage, context: Optional[Dict[str, Any]] = None):
        """Log a recovery stage"""
        self.current_stage = stage
        
        stage_log = {
            "stage": stage.value,
            "timestamp": time.time(),
            "session_id": self.session_id,
            "attempt_number": self.current_attempt,
            "context": context or {}
        }
        
        self.stage_logs.append(stage_log)
        
        if MONITORING_AVAILABLE:
            stage_name = stage.value.replace("_", " ").title()
            logger.debug(LogCategory.ERROR_FIXING, f"📋 Stage: {stage_name}",
                        context={
                            "session_id": self.session_id,
                            "stage": stage.value,
                            "attempt_number": self.current_attempt,
                            "stage_context": context
                        })
    
    def log_command_execution(self, command_result: CommandResult, context: Optional[str] = None):
        """Log command execution result"""
        self.metrics.commands_executed += 1
        
        # Add to current attempt if active
        if self.attempt_logs and self.current_attempt:
            attempt_log = self.attempt_logs[-1]
            attempt_log.commands_executed.append(command_result.command)
        
        command_log = {
            "timestamp": time.time(),
            "session_id": self.session_id,
            "attempt_number": self.current_attempt,
            "command": command_result.command,
            "args": command_result.args,
            "success": command_result.success,
            "exit_code": command_result.exit_code,
            "execution_time": command_result.execution_time,
            "timeout": command_result.timeout,
            "error_message": command_result.error_message,
            "context": context,
            "stdout_length": len(command_result.stdout),
            "stderr_length": len(command_result.stderr)
        }
        
        self.command_logs.append(command_log)
        
        if MONITORING_AVAILABLE:
            status_emoji = "✅" if command_result.success else "❌"
            logger.info(LogCategory.SHELL_CMD, 
                       f"{status_emoji} {command_result.command} ({command_result.execution_time:.1f}s)",
                       context={
                           "session_id": self.session_id,
                           "attempt_number": self.current_attempt,
                           "command": command_result.command,
                           "success": command_result.success,
                           "exit_code": command_result.exit_code,
                           "execution_time_seconds": round(command_result.execution_time, 2),
                           "context": context
                       })
    
    def log_fix_application(self, file_path: str, success: bool, error_message: Optional[str] = None):
        """Log fix application result"""
        if success:
            self.metrics.fixes_applied += 1
            self.metrics.files_modified += 1
        
        # Add to current attempt if active
        if self.attempt_logs and self.current_attempt:
            attempt_log = self.attempt_logs[-1]
            if success:
                attempt_log.fixes_applied += 1
                attempt_log.files_modified.append(file_path)
        
        if MONITORING_AVAILABLE:
            status_emoji = "✅" if success else "❌"
            logger.info(LogCategory.ERROR_FIXING, 
                       f"{status_emoji} Fix {'applied' if success else 'failed'}: {file_path}",
                       context={
                           "session_id": self.session_id,
                           "attempt_number": self.current_attempt,
                           "file_path": file_path,
                           "success": success,
                           "error_message": error_message
                       })
    
    def log_error_snapshot(self, snapshot: ErrorSnapshot):
        """Log error snapshot"""
        self.log_stage(RecoveryStage.ERROR_ANALYSIS, {
            "snapshot": {
                "attempt_number": snapshot.attempt_number,
                "total_errors": snapshot.total_errors,
                "total_warnings": snapshot.total_warnings,
                "error_categories": snapshot.error_categories,
                "context": snapshot.context
            }
        })
    
    def log_error_diff(self, diff: ErrorDiff):
        """Log error diff analysis"""
        self.log_stage(RecoveryStage.PROGRESS_ANALYSIS, {
            "diff": {
                "from_attempt": diff.from_snapshot.attempt_number,
                "to_attempt": diff.to_snapshot.attempt_number,
                "progress_score": diff.progress_score,
                "regression_score": diff.regression_score,
                "summary": diff.summary,
                "changes_count": len(diff.changes)
            }
        })
        
        if MONITORING_AVAILABLE:
            from .error_diff_analyzer import ErrorDiffAnalyzer
            analyzer = ErrorDiffAnalyzer()
            summary_text = analyzer.format_diff_summary(diff)
            logger.info(LogCategory.ERROR_FIXING, f"📊 {summary_text}",
                       context={
                           "session_id": self.session_id,
                           "diff_summary": diff.summary,
                           "progress_score": diff.progress_score,
                           "regression_score": diff.regression_score
                       })
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get comprehensive session summary"""
        current_time = time.time()
        duration = current_time - self.start_time
        
        return {
            "session_id": self.session_id,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration_seconds": round(duration, 2),
            "metrics": asdict(self.metrics),
            "total_attempts": len(self.attempt_logs),
            "total_stages": len(self.stage_logs),
            "total_commands": len(self.command_logs),
            "successful_commands": sum(1 for cmd in self.command_logs if cmd["success"]),
            "failed_commands": sum(1 for cmd in self.command_logs if not cmd["success"]),
            "files_modified": self.metrics.files_modified,
            "latest_attempt": self.attempt_logs[-1] if self.attempt_logs else None
        }
    
    def _write_session_log(self):
        """Write complete session log to file"""
        if not self.log_file_path:
            return
        
        try:
            session_data = {
                "session_summary": self.get_session_summary(),
                "attempt_logs": [asdict(log) for log in self.attempt_logs],
                "stage_logs": self.stage_logs,
                "command_logs": self.command_logs,
                "export_timestamp": datetime.now().isoformat()
            }
            
            with open(self.log_file_path, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, default=str)
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.SYSTEM, f"Session log written to {self.log_file_path}")
                
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SYSTEM, f"Failed to write session log: {e}")
    
    def format_progress_summary(self) -> str:
        """Format a human-readable progress summary"""
        if not self.attempt_logs:
            return "No attempts logged"
        
        latest = self.attempt_logs[-1]
        duration = (time.time() - self.start_time)
        
        status_emoji = "🔄" if self.current_attempt else ("✅" if self.metrics.success else "❌")
        
        parts = [
            f"{status_emoji} Session {self.session_id}",
            f"Duration: {duration:.1f}s",
            f"Attempts: {len(self.attempt_logs)}",
            f"Commands: {self.metrics.commands_executed}",
            f"Fixes: {self.metrics.fixes_applied}"
        ]
        
        if latest.error_count_before is not None and latest.error_count_after is not None:
            change = latest.error_count_before - latest.error_count_after
            if change > 0:
                parts.append(f"Errors: {latest.error_count_before} → {latest.error_count_after} (-{change})")
            elif change < 0:
                parts.append(f"Errors: {latest.error_count_before} → {latest.error_count_after} (+{abs(change)})")
            else:
                parts.append(f"Errors: {latest.error_count_after} (no change)")
        
        return " | ".join(parts)


# Global instance for easy access
_comprehensive_logger = None

def get_comprehensive_logger(session_id: Optional[str] = None, 
                           log_file_path: Optional[str] = None) -> ComprehensiveLogger:
    """Get or create the global comprehensive logger instance"""
    global _comprehensive_logger
    if _comprehensive_logger is None or (_comprehensive_logger.session_id != session_id and session_id is not None):
        _comprehensive_logger = ComprehensiveLogger(session_id, log_file_path)
    return _comprehensive_logger

def reset_comprehensive_logger():
    """Reset the global logger (for new recovery sessions)"""
    global _comprehensive_logger
    _comprehensive_logger = None