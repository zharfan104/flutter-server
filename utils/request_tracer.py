"""
Request Tracing System for End-to-End Pipeline Tracking
Provides detailed tracing of requests through the entire AI development pipeline
"""

import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict

from .advanced_logger import logger, LogCategory, LogLevel


class TraceEventType(Enum):
    REQUEST_START = "request_start"
    REQUEST_END = "request_end"
    PIPELINE_STEP = "pipeline_step"
    LLM_CALL = "llm_call"
    FILE_OPERATION = "file_operation"
    ANALYSIS = "analysis"
    HOT_RELOAD = "hot_reload"
    ERROR = "error"
    RETRY = "retry"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"


class TraceStatus(Enum):
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


@dataclass
class TraceEvent:
    """Individual trace event in a request"""
    event_id: str
    trace_id: str
    parent_event_id: Optional[str]
    event_type: TraceEventType
    status: TraceStatus
    timestamp: str
    duration_ms: Optional[float]
    component: str
    operation: str
    metadata: Dict[str, Any]
    tags: List[str]
    error_info: Optional[Dict[str, Any]] = None


@dataclass
class RequestTrace:
    """Complete trace for a request"""
    trace_id: str
    request_type: str
    user_id: Optional[str]
    start_time: str
    end_time: Optional[str]
    total_duration_ms: Optional[float]
    status: TraceStatus
    events: List[TraceEvent]
    metadata: Dict[str, Any]
    error_summary: Optional[str] = None
    
    def add_event(self, event: TraceEvent):
        """Add an event to this trace"""
        self.events.append(event)
    
    def get_events_by_type(self, event_type: TraceEventType) -> List[TraceEvent]:
        """Get all events of a specific type"""
        return [event for event in self.events if event.event_type == event_type]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for this trace"""
        if not self.events:
            return {}
        
        # Group events by component
        component_times = defaultdict(float)
        operation_counts = defaultdict(int)
        
        for event in self.events:
            if event.duration_ms:
                component_times[event.component] += event.duration_ms
            operation_counts[f"{event.component}:{event.operation}"] += 1
        
        return {
            "total_duration_ms": self.total_duration_ms,
            "component_times": dict(component_times),
            "operation_counts": dict(operation_counts),
            "event_count": len(self.events),
            "llm_calls": len(self.get_events_by_type(TraceEventType.LLM_CALL)),
            "file_operations": len(self.get_events_by_type(TraceEventType.FILE_OPERATION)),
            "errors": len(self.get_events_by_type(TraceEventType.ERROR))
        }


class RequestTracer:
    """
    Comprehensive request tracing system for the AI development pipeline
    """
    
    def __init__(self, max_traces: int = 1000, cleanup_interval_hours: int = 24):
        self.max_traces = max_traces
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)
        
        # Storage
        self.active_traces: Dict[str, RequestTrace] = {}
        self.completed_traces: Dict[str, RequestTrace] = {}
        self.trace_events: Dict[str, List[TraceEvent]] = defaultdict(list)
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance tracking
        self.performance_baselines: Dict[str, Dict[str, float]] = {}
        self.anomaly_detection_threshold = 2.0  # 2x normal time is anomaly
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "active_requests": 0,
            "completed_requests": 0,
            "failed_requests": 0,
            "average_duration_ms": 0.0,
            "slowest_request_ms": 0.0,
            "fastest_request_ms": float('inf')
        }
    
    def start_trace(self, 
                   request_type: str, 
                   user_id: Optional[str] = None,
                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start a new request trace"""
        trace_id = str(uuid.uuid4())
        
        trace = RequestTrace(
            trace_id=trace_id,
            request_type=request_type,
            user_id=user_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            total_duration_ms=None,
            status=TraceStatus.STARTED,
            events=[],
            metadata=metadata or {}
        )
        
        with self.lock:
            self.active_traces[trace_id] = trace
            self.stats["total_requests"] += 1
            self.stats["active_requests"] += 1
        
        # Log the start
        logger.info(LogCategory.SYSTEM, f"Started request trace: {request_type}",
                   context={
                       "trace_id": trace_id,
                       "request_type": request_type,
                       "user_id": user_id,
                       "metadata": metadata
                   },
                   tags=["trace", "request_start"])
        
        # Add start event
        self.add_event(
            trace_id=trace_id,
            event_type=TraceEventType.REQUEST_START,
            component="tracer",
            operation="start_trace",
            metadata={"request_type": request_type, "user_id": user_id}
        )
        
        return trace_id
    
    def end_trace(self, 
                 trace_id: str, 
                 status: TraceStatus = TraceStatus.COMPLETED,
                 error_summary: Optional[str] = None) -> Optional[RequestTrace]:
        """End a request trace"""
        with self.lock:
            trace = self.active_traces.pop(trace_id, None)
            if not trace:
                logger.warn(LogCategory.SYSTEM, f"Attempted to end non-existent trace: {trace_id}")
                return None
            
            # Update trace
            end_time = datetime.now()
            trace.end_time = end_time.isoformat()
            trace.status = status
            trace.error_summary = error_summary
            
            # Calculate duration
            start_time = datetime.fromisoformat(trace.start_time)
            trace.total_duration_ms = (end_time - start_time).total_seconds() * 1000
            
            # Move to completed traces
            self.completed_traces[trace_id] = trace
            
            # Update statistics
            self.stats["active_requests"] -= 1
            self.stats["completed_requests"] += 1
            
            if status == TraceStatus.FAILED:
                self.stats["failed_requests"] += 1
            
            # Update duration statistics
            if trace.total_duration_ms:
                total_completed = self.stats["completed_requests"]
                current_avg = self.stats["average_duration_ms"]
                self.stats["average_duration_ms"] = ((current_avg * (total_completed - 1)) + trace.total_duration_ms) / total_completed
                
                self.stats["slowest_request_ms"] = max(self.stats["slowest_request_ms"], trace.total_duration_ms)
                self.stats["fastest_request_ms"] = min(self.stats["fastest_request_ms"], trace.total_duration_ms)
        
        # Add end event
        self.add_event(
            trace_id=trace_id,
            event_type=TraceEventType.REQUEST_END,
            component="tracer",
            operation="end_trace",
            metadata={
                "status": status.value,
                "duration_ms": trace.total_duration_ms,
                "error_summary": error_summary
            }
        )
        
        # Log completion
        level = LogLevel.INFO if status == TraceStatus.COMPLETED else LogLevel.WARN
        logger.log(level, LogCategory.SYSTEM, f"Completed request trace: {trace.request_type}",
                  context={
                      "trace_id": trace_id,
                      "status": status.value,
                      "duration_ms": trace.total_duration_ms,
                      "error_summary": error_summary
                  },
                  tags=["trace", "request_end"])
        
        # Check for performance anomalies
        self._check_performance_anomaly(trace)
        
        # Cleanup old traces
        self._cleanup_old_traces()
        
        return trace
    
    def add_event(self,
                 trace_id: str,
                 event_type: TraceEventType,
                 component: str,
                 operation: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 parent_event_id: Optional[str] = None,
                 duration_ms: Optional[float] = None,
                 status: TraceStatus = TraceStatus.COMPLETED,
                 tags: Optional[List[str]] = None,
                 error_info: Optional[Dict[str, Any]] = None) -> str:
        """Add an event to a trace"""
        
        event_id = str(uuid.uuid4())
        
        event = TraceEvent(
            event_id=event_id,
            trace_id=trace_id,
            parent_event_id=parent_event_id,
            event_type=event_type,
            status=status,
            timestamp=datetime.now().isoformat(),
            duration_ms=duration_ms,
            component=component,
            operation=operation,
            metadata=metadata or {},
            tags=tags or [],
            error_info=error_info
        )
        
        with self.lock:
            # Add to active or completed trace
            trace = self.active_traces.get(trace_id) or self.completed_traces.get(trace_id)
            if trace:
                trace.add_event(event)
            
            # Add to events index
            self.trace_events[trace_id].append(event)
        
        # Log the event
        log_level = LogLevel.ERROR if event_type == TraceEventType.ERROR else LogLevel.DEBUG
        logger.log(log_level, LogCategory.SYSTEM, f"Trace event: {component}.{operation}",
                  context={
                      "trace_id": trace_id,
                      "event_id": event_id,
                      "event_type": event_type.value,
                      "component": component,
                      "operation": operation,
                      "duration_ms": duration_ms,
                      "metadata": metadata,
                      "error_info": error_info
                  },
                  tags=["trace", "event"] + (tags or []))
        
        return event_id
    
    def get_trace(self, trace_id: str) -> Optional[RequestTrace]:
        """Get a specific trace"""
        with self.lock:
            return self.active_traces.get(trace_id) or self.completed_traces.get(trace_id)
    
    def get_active_traces(self) -> List[RequestTrace]:
        """Get all active traces"""
        with self.lock:
            return list(self.active_traces.values())
    
    def get_recent_traces(self, limit: int = 50) -> List[RequestTrace]:
        """Get recent completed traces"""
        with self.lock:
            traces = list(self.completed_traces.values())
            # Sort by start time, most recent first
            traces.sort(key=lambda t: t.start_time, reverse=True)
            return traces[:limit]
    
    def get_traces_by_type(self, request_type: str, limit: int = 20) -> List[RequestTrace]:
        """Get traces by request type"""
        with self.lock:
            traces = [t for t in self.completed_traces.values() if t.request_type == request_type]
            traces.sort(key=lambda t: t.start_time, reverse=True)
            return traces[:limit]
    
    def get_failed_traces(self, limit: int = 20) -> List[RequestTrace]:
        """Get recent failed traces"""
        with self.lock:
            failed = [t for t in self.completed_traces.values() if t.status == TraceStatus.FAILED]
            failed.sort(key=lambda t: t.start_time, reverse=True)
            return failed[:limit]
    
    def get_performance_baselines(self) -> Dict[str, Dict[str, float]]:
        """Get performance baselines for different request types"""
        return self.performance_baselines.copy()
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get comprehensive trace statistics"""
        with self.lock:
            stats = self.stats.copy()
            
            # Add request type breakdown
            request_type_counts = defaultdict(int)
            request_type_durations = defaultdict(list)
            
            for trace in self.completed_traces.values():
                request_type_counts[trace.request_type] += 1
                if trace.total_duration_ms:
                    request_type_durations[trace.request_type].append(trace.total_duration_ms)
            
            # Calculate averages by request type
            request_type_stats = {}
            for req_type, durations in request_type_durations.items():
                if durations:
                    request_type_stats[req_type] = {
                        "count": len(durations),
                        "avg_duration_ms": sum(durations) / len(durations),
                        "min_duration_ms": min(durations),
                        "max_duration_ms": max(durations)
                    }
            
            stats.update({
                "request_type_counts": dict(request_type_counts),
                "request_type_performance": request_type_stats,
                "performance_baselines": self.performance_baselines
            })
            
            return stats
    
    def _check_performance_anomaly(self, trace: RequestTrace):
        """Check if this trace represents a performance anomaly"""
        if not trace.total_duration_ms:
            return
        
        request_type = trace.request_type
        
        # Update performance baseline
        if request_type not in self.performance_baselines:
            self.performance_baselines[request_type] = {
                "avg_duration_ms": trace.total_duration_ms,
                "count": 1,
                "total_duration_ms": trace.total_duration_ms
            }
        else:
            baseline = self.performance_baselines[request_type]
            baseline["count"] += 1
            baseline["total_duration_ms"] += trace.total_duration_ms
            baseline["avg_duration_ms"] = baseline["total_duration_ms"] / baseline["count"]
        
        # Check for anomaly
        baseline_avg = self.performance_baselines[request_type]["avg_duration_ms"]
        if trace.total_duration_ms > baseline_avg * self.anomaly_detection_threshold:
            logger.warn(LogCategory.PERFORMANCE, f"Performance anomaly detected for {request_type}",
                       context={
                           "trace_id": trace.trace_id,
                           "actual_duration_ms": trace.total_duration_ms,
                           "baseline_avg_ms": baseline_avg,
                           "anomaly_threshold": self.anomaly_detection_threshold,
                           "performance_factor": trace.total_duration_ms / baseline_avg
                       },
                       tags=["performance", "anomaly"])
    
    def _cleanup_old_traces(self):
        """Cleanup old completed traces to prevent memory leaks"""
        if len(self.completed_traces) <= self.max_traces:
            return
        
        with self.lock:
            # Sort by start time and keep only the most recent
            traces = list(self.completed_traces.items())
            traces.sort(key=lambda x: x[1].start_time, reverse=True)
            
            # Keep only max_traces
            to_keep = dict(traces[:self.max_traces])
            to_remove = dict(traces[self.max_traces:])
            
            self.completed_traces = to_keep
            
            # Also cleanup trace events
            for trace_id in to_remove.keys():
                self.trace_events.pop(trace_id, None)
            
            if to_remove:
                logger.info(LogCategory.SYSTEM, f"Cleaned up {len(to_remove)} old traces",
                           context={"removed_traces": len(to_remove), "kept_traces": len(to_keep)})


# Global tracer instance
tracer = RequestTracer()


# Context managers for easy tracing
class TraceContext:
    """Context manager for request tracing"""
    
    def __init__(self, 
                 request_type: str, 
                 user_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        self.request_type = request_type
        self.user_id = user_id
        self.metadata = metadata
        self.trace_id: Optional[str] = None
    
    def __enter__(self):
        self.trace_id = tracer.start_trace(self.request_type, self.user_id, self.metadata)
        return self.trace_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.trace_id:
            status = TraceStatus.FAILED if exc_type else TraceStatus.COMPLETED
            error_summary = f"{exc_type.__name__}: {exc_val}" if exc_type else None
            tracer.end_trace(self.trace_id, status, error_summary)


class EventContext:
    """Context manager for trace events"""
    
    def __init__(self,
                 trace_id: str,
                 event_type: TraceEventType,
                 component: str,
                 operation: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 tags: Optional[List[str]] = None):
        self.trace_id = trace_id
        self.event_type = event_type
        self.component = component
        self.operation = operation
        self.metadata = metadata
        self.tags = tags
        self.start_time = None
        self.event_id: Optional[str] = None
    
    def __enter__(self):
        self.start_time = time.time()
        
        # Add start event for long-running operations
        if self.event_type in [TraceEventType.PIPELINE_STEP, TraceEventType.LLM_CALL, TraceEventType.ANALYSIS]:
            self.event_id = tracer.add_event(
                trace_id=self.trace_id,
                event_type=self.event_type,
                component=self.component,
                operation=self.operation,
                metadata=self.metadata,
                status=TraceStatus.IN_PROGRESS,
                tags=self.tags
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else None
        
        status = TraceStatus.FAILED if exc_type else TraceStatus.COMPLETED
        error_info = None
        
        if exc_type:
            error_info = {
                "error_type": exc_type.__name__,
                "error_message": str(exc_val),
                "traceback": str(exc_tb) if exc_tb else None
            }
        
        # Add completion event
        tracer.add_event(
            trace_id=self.trace_id,
            event_type=self.event_type,
            component=self.component,
            operation=self.operation,
            metadata=self.metadata,
            duration_ms=duration_ms,
            status=status,
            tags=self.tags,
            error_info=error_info
        )
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata during operation"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata[key] = value