"""
Advanced Multi-Level Logging System with Structured Logging and Request Tracing
Provides comprehensive logging capabilities for the Flutter development pipeline
"""

import json
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import traceback
import os


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    PIPELINE = "pipeline"
    LLM = "llm"
    CODE_MOD = "code_modification"
    DART_ANALYSIS = "dart_analysis"
    FILE_OPS = "file_operations"
    PERFORMANCE = "performance"
    ERROR = "error"
    USER = "user"
    SYSTEM = "system"
    FLUTTER = "flutter"


@dataclass
class LogEntry:
    """Structured log entry with comprehensive metadata"""
    timestamp: str
    level: LogLevel
    category: LogCategory
    request_id: Optional[str]
    user_id: Optional[str]
    message: str
    context: Dict[str, Any]
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    stack_trace: Optional[str] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class RequestContext:
    """Thread-local request context for tracking"""
    _context = threading.local()
    
    @classmethod
    def set_request_id(cls, request_id: str):
        cls._context.request_id = request_id
    
    @classmethod
    def get_request_id(cls) -> Optional[str]:
        return getattr(cls._context, 'request_id', None)
    
    @classmethod
    def set_user_id(cls, user_id: str):
        cls._context.user_id = user_id
    
    @classmethod
    def get_user_id(cls) -> Optional[str]:
        return getattr(cls._context, 'user_id', None)
    
    @classmethod
    def clear(cls):
        if hasattr(cls._context, 'request_id'):
            del cls._context.request_id
        if hasattr(cls._context, 'user_id'):
            del cls._context.user_id


class PerformanceTracker:
    """Track performance metrics for operations"""
    
    def __init__(self):
        self.operation_times: Dict[str, List[float]] = {}
        self.memory_snapshots: List[tuple] = []
        self.lock = threading.Lock()
    
    def start_operation(self, operation_name: str) -> str:
        """Start tracking an operation, returns operation ID"""
        operation_id = str(uuid.uuid4())
        with self.lock:
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
        return operation_id
    
    def end_operation(self, operation_name: str, operation_id: str, start_time: float) -> float:
        """End tracking an operation, returns duration"""
        duration = (time.time() - start_time) * 1000  # Convert to milliseconds
        with self.lock:
            if operation_name in self.operation_times:
                self.operation_times[operation_name].append(duration)
        return duration
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for an operation"""
        with self.lock:
            times = self.operation_times.get(operation_name, [])
            if not times:
                return {}
            
            return {
                "count": len(times),
                "avg_ms": sum(times) / len(times),
                "min_ms": min(times),
                "max_ms": max(times),
                "total_ms": sum(times)
            }


class AdvancedLogger:
    """
    Advanced logging system with structured logging, request tracing, and performance monitoring
    """
    
    def __init__(self, log_level: LogLevel = LogLevel.INFO, max_log_entries: int = 10000):
        self.log_level = log_level
        self.max_log_entries = max_log_entries
        self.log_entries: List[LogEntry] = []
        self.performance_tracker = PerformanceTracker()
        self.subscribers: List[Callable[[LogEntry], None]] = []
        self.lock = threading.Lock()
        
        # Configuration
        self.enable_console_output = True
        self.enable_file_output = False
        self.log_file_path: Optional[Path] = None
        self.enable_performance_tracking = True
        
        # Statistics
        self.stats = {
            "total_logs": 0,
            "logs_by_level": {level.value: 0 for level in LogLevel},
            "logs_by_category": {cat.value: 0 for cat in LogCategory},
            "errors_count": 0,
            "warnings_count": 0
        }
    
    def configure(self, 
                 enable_console: bool = True,
                 enable_file: bool = False,
                 log_file_path: Optional[str] = None,
                 enable_performance: bool = True):
        """Configure logger settings"""
        self.enable_console_output = enable_console
        self.enable_file_output = enable_file
        if log_file_path:
            self.log_file_path = Path(log_file_path)
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.enable_performance_tracking = enable_performance
    
    def subscribe(self, callback: Callable[[LogEntry], None]):
        """Subscribe to log events"""
        self.subscribers.append(callback)
    
    def _should_log(self, level: LogLevel) -> bool:
        """Check if we should log at this level"""
        level_order = {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARN: 2,
            LogLevel.ERROR: 3,
            LogLevel.CRITICAL: 4
        }
        return level_order[level] >= level_order[self.log_level]
    
    def _get_memory_usage(self) -> Optional[float]:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            return None
    
    def _create_log_entry(self,
                         level: LogLevel,
                         category: LogCategory,
                         message: str,
                         context: Optional[Dict[str, Any]] = None,
                         duration_ms: Optional[float] = None,
                         include_stack: bool = False,
                         tags: Optional[List[str]] = None) -> LogEntry:
        """Create a structured log entry"""
        
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            level=level,
            category=category,
            request_id=RequestContext.get_request_id(),
            user_id=RequestContext.get_user_id(),
            message=message,
            context=context or {},
            duration_ms=duration_ms,
            memory_usage_mb=self._get_memory_usage() if self.enable_performance_tracking else None,
            stack_trace=traceback.format_stack() if include_stack else None,
            tags=tags or []
        )
        
        return entry
    
    def _output_log_entry(self, entry: LogEntry):
        """Output log entry to configured destinations"""
        
        # Console output
        if self.enable_console_output:
            console_msg = f"[{entry.timestamp}] {entry.level.value} {entry.category.value}: {entry.message}"
            if entry.request_id:
                console_msg += f" [req:{entry.request_id[:8]}]"
            if entry.duration_ms:
                console_msg += f" ({entry.duration_ms:.1f}ms)"
            print(console_msg)
            
            # Print context if significant
            if entry.context and entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
                print(f"  Context: {json.dumps(entry.context, indent=2)}")
        
        # File output
        if self.enable_file_output and self.log_file_path:
            try:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    json.dump(asdict(entry), f, default=str)
                    f.write('\n')
            except Exception as e:
                print(f"Failed to write to log file: {e}")
    
    def log(self,
           level: LogLevel,
           category: LogCategory,
           message: str,
           context: Optional[Dict[str, Any]] = None,
           duration_ms: Optional[float] = None,
           include_stack: bool = False,
           tags: Optional[List[str]] = None):
        """Log a message with full context"""
        
        if not self._should_log(level):
            return
        
        entry = self._create_log_entry(
            level=level,
            category=category,
            message=message,
            context=context,
            duration_ms=duration_ms,
            include_stack=include_stack,
            tags=tags
        )
        
        with self.lock:
            # Add to log entries
            self.log_entries.append(entry)
            
            # Maintain max entries limit
            if len(self.log_entries) > self.max_log_entries:
                self.log_entries = self.log_entries[-self.max_log_entries:]
            
            # Update statistics
            self.stats["total_logs"] += 1
            self.stats["logs_by_level"][level.value] += 1
            self.stats["logs_by_category"][category.value] += 1
            
            if level == LogLevel.ERROR:
                self.stats["errors_count"] += 1
            elif level == LogLevel.WARN:
                self.stats["warnings_count"] += 1
        
        # Output the log entry
        self._output_log_entry(entry)
        
        # Notify subscribers
        for subscriber in self.subscribers:
            try:
                subscriber(entry)
            except Exception as e:
                print(f"Log subscriber error: {e}")
    
    # Convenience methods
    def debug(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.DEBUG, category, message, **kwargs)
    
    def info(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.INFO, category, message, **kwargs)
    
    def warn(self, category: LogCategory, message: str, **kwargs):
        self.log(LogLevel.WARN, category, message, **kwargs)
    
    def error(self, category: LogCategory, message: str, **kwargs):
        kwargs.setdefault('include_stack', True)
        self.log(LogLevel.ERROR, category, message, **kwargs)
    
    def critical(self, category: LogCategory, message: str, **kwargs):
        kwargs.setdefault('include_stack', True)
        self.log(LogLevel.CRITICAL, category, message, **kwargs)
    
    # Performance tracking methods
    def start_operation(self, operation_name: str, category: LogCategory = LogCategory.PERFORMANCE) -> tuple:
        """Start tracking an operation performance"""
        operation_id = self.performance_tracker.start_operation(operation_name)
        start_time = time.time()
        
        self.debug(category, f"Started operation: {operation_name}", 
                  context={"operation_id": operation_id, "operation_name": operation_name})
        
        return operation_id, start_time
    
    def end_operation(self, operation_name: str, operation_id: str, start_time: float, 
                     category: LogCategory = LogCategory.PERFORMANCE, 
                     success: bool = True, 
                     additional_context: Optional[Dict[str, Any]] = None):
        """End tracking an operation performance"""
        duration = self.performance_tracker.end_operation(operation_name, operation_id, start_time)
        
        context = {
            "operation_id": operation_id,
            "operation_name": operation_name,
            "success": success,
            "duration_ms": duration
        }
        
        if additional_context:
            context.update(additional_context)
        
        level = LogLevel.INFO if success else LogLevel.WARN
        self.log(level, category, f"Completed operation: {operation_name}", 
                context=context, duration_ms=duration)
        
        return duration
    
    # Query methods
    def get_logs(self, 
                request_id: Optional[str] = None,
                category: Optional[LogCategory] = None,
                level: Optional[LogLevel] = None,
                limit: Optional[int] = None,
                tags: Optional[List[str]] = None) -> List[LogEntry]:
        """Query log entries with filters"""
        with self.lock:
            filtered_logs = self.log_entries.copy()
        
        # Apply filters
        if request_id:
            filtered_logs = [log for log in filtered_logs if log.request_id == request_id]
        
        if category:
            filtered_logs = [log for log in filtered_logs if log.category == category]
        
        if level:
            filtered_logs = [log for log in filtered_logs if log.level == level]
        
        if tags:
            filtered_logs = [log for log in filtered_logs 
                           if any(tag in log.tags for tag in tags)]
        
        # Apply limit
        if limit:
            filtered_logs = filtered_logs[-limit:]
        
        return filtered_logs
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        with self.lock:
            stats = self.stats.copy()
        
        # Add performance stats
        perf_stats = {}
        for operation_name in self.performance_tracker.operation_times:
            perf_stats[operation_name] = self.performance_tracker.get_operation_stats(operation_name)
        
        stats["performance"] = perf_stats
        return stats
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors"""
        recent_errors = self.get_logs(level=LogLevel.ERROR, limit=50)
        
        error_patterns = {}
        for error in recent_errors:
            key = f"{error.category.value}:{error.message[:50]}"
            if key not in error_patterns:
                error_patterns[key] = {
                    "count": 0,
                    "first_seen": error.timestamp,
                    "last_seen": error.timestamp,
                    "category": error.category.value,
                    "sample_message": error.message
                }
            
            error_patterns[key]["count"] += 1
            error_patterns[key]["last_seen"] = error.timestamp
        
        return {
            "total_errors": len(recent_errors),
            "error_patterns": error_patterns,
            "recent_errors": [asdict(error) for error in recent_errors[-10:]]
        }


# Global logger instance
logger = AdvancedLogger()


# Context managers for request tracking
class RequestTracker:
    """Context manager for tracking requests"""
    
    def __init__(self, request_id: Optional[str] = None, user_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())
        self.user_id = user_id
        self.start_time = time.time()
    
    def __enter__(self):
        RequestContext.set_request_id(self.request_id)
        if self.user_id:
            RequestContext.set_user_id(self.user_id)
        
        logger.info(LogCategory.SYSTEM, f"Started request tracking", 
                   context={"request_id": self.request_id, "user_id": self.user_id})
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.time() - self.start_time) * 1000
        
        if exc_type:
            logger.error(LogCategory.SYSTEM, f"Request failed: {exc_type.__name__}: {exc_val}",
                        context={"request_id": self.request_id, "duration_ms": duration},
                        include_stack=True)
        else:
            logger.info(LogCategory.SYSTEM, f"Request completed successfully",
                       context={"request_id": self.request_id, "duration_ms": duration})
        
        RequestContext.clear()


class OperationTracker:
    """Context manager for tracking operations"""
    
    def __init__(self, operation_name: str, category: LogCategory = LogCategory.PERFORMANCE):
        self.operation_name = operation_name
        self.category = category
        self.operation_id = None
        self.start_time = None
    
    def __enter__(self):
        self.operation_id, self.start_time = logger.start_operation(self.operation_name, self.category)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        success = exc_type is None
        additional_context = {}
        
        if exc_type:
            additional_context = {
                "error_type": exc_type.__name__,
                "error_message": str(exc_val)
            }
        
        logger.end_operation(
            self.operation_name, 
            self.operation_id, 
            self.start_time, 
            self.category, 
            success, 
            additional_context
        )