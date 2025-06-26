"""
Performance Monitoring System for AI Development Pipeline
Provides real-time performance monitoring, resource tracking, and alerting
"""

import time
import threading
import psutil
import gc
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, NamedTuple
from dataclasses import dataclass
from enum import Enum
from collections import deque, defaultdict
import statistics

from .advanced_logger import logger, LogCategory, LogLevel


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Individual metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str]
    metric_type: MetricType


@dataclass
class Alert:
    """Performance alert"""
    alert_id: str
    level: AlertLevel
    metric_name: str
    threshold: float
    current_value: float
    message: str
    timestamp: datetime
    resolved: bool = False


class ResourceSnapshot(NamedTuple):
    """System resource snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    open_files: int
    thread_count: int


class PerformanceThreshold:
    """Performance threshold configuration"""
    
    def __init__(self,
                 warning_threshold: float,
                 critical_threshold: float,
                 metric_type: MetricType = MetricType.GAUGE,
                 operator: str = "gt"):  # gt, lt, eq
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.metric_type = metric_type
        self.operator = operator
    
    def check_threshold(self, value: float) -> Optional[AlertLevel]:
        """Check if value crosses threshold"""
        if self.operator == "gt":
            if value >= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value >= self.warning_threshold:
                return AlertLevel.WARNING
        elif self.operator == "lt":
            if value <= self.critical_threshold:
                return AlertLevel.CRITICAL
            elif value <= self.warning_threshold:
                return AlertLevel.WARNING
        
        return None


class MetricCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self, max_points: int = 1000):
        self.max_points = max_points
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self.lock = threading.RLock()
    
    def add_metric(self, metric: Metric):
        """Add a metric data point"""
        with self.lock:
            self.metrics[metric.name].append(metric)
    
    def get_recent_metrics(self, metric_name: str, limit: int = 100) -> List[Metric]:
        """Get recent metrics for a name"""
        with self.lock:
            metrics_deque = self.metrics.get(metric_name, deque())
            return list(metrics_deque)[-limit:]
    
    def get_metric_stats(self, metric_name: str, window_minutes: int = 5) -> Dict[str, float]:
        """Get statistical summary for a metric over time window"""
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        
        with self.lock:
            recent_metrics = [
                m for m in self.metrics.get(metric_name, [])
                if m.timestamp >= cutoff_time
            ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "p95": statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values),
            "p99": statistics.quantiles(values, n=100)[98] if len(values) >= 100 else max(values)
        }


class SystemMonitor:
    """Monitor system resources"""
    
    def __init__(self, collection_interval: float = 5.0):
        self.collection_interval = collection_interval
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.snapshots: deque = deque(maxlen=1000)
        self.process = psutil.Process()
        
        # Network and disk IO baselines
        self.last_network = psutil.net_io_counters()
        self.last_disk = psutil.disk_io_counters()
        self.last_snapshot_time = time.time()
    
    def start(self):
        """Start system monitoring"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        logger.info(LogCategory.PERFORMANCE, "Started system monitoring",
                   context={"collection_interval": self.collection_interval})
    
    def stop(self):
        """Stop system monitoring"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        logger.info(LogCategory.PERFORMANCE, "Stopped system monitoring")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                snapshot = self._collect_snapshot()
                self.snapshots.append(snapshot)
                
                # Log significant changes
                if len(self.snapshots) > 1:
                    self._check_resource_changes(snapshot)
                
            except Exception as e:
                logger.error(LogCategory.PERFORMANCE, f"Error collecting system snapshot: {e}")
            
            time.sleep(self.collection_interval)
    
    def _collect_snapshot(self) -> ResourceSnapshot:
        """Collect current system resource snapshot"""
        current_time = time.time()
        
        # CPU and Memory
        cpu_percent = self.process.cpu_percent()
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()
        
        # Network and Disk IO (calculate rates)
        current_network = psutil.net_io_counters()
        current_disk = psutil.disk_io_counters()
        
        time_delta = current_time - self.last_snapshot_time
        
        # Network rates (MB/s)
        network_sent_mb = (current_network.bytes_sent - self.last_network.bytes_sent) / (1024 * 1024 * time_delta)
        network_recv_mb = (current_network.bytes_recv - self.last_network.bytes_recv) / (1024 * 1024 * time_delta)
        
        # Disk IO rates (MB/s) 
        disk_read_mb = (current_disk.read_bytes - self.last_disk.read_bytes) / (1024 * 1024 * time_delta)
        disk_write_mb = (current_disk.write_bytes - self.last_disk.write_bytes) / (1024 * 1024 * time_delta)
        
        # Update baselines
        self.last_network = current_network
        self.last_disk = current_disk
        self.last_snapshot_time = current_time
        
        # Process info
        try:
            open_files = len(self.process.open_files())
        except (psutil.AccessDenied, AttributeError):
            open_files = -1
        
        thread_count = self.process.num_threads()
        
        return ResourceSnapshot(
            timestamp=datetime.now(),
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            memory_mb=memory_info.rss / (1024 * 1024),
            disk_io_read_mb=disk_read_mb,
            disk_io_write_mb=disk_write_mb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            open_files=open_files,
            thread_count=thread_count
        )
    
    def _check_resource_changes(self, snapshot: ResourceSnapshot):
        """Check for significant resource changes"""
        if len(self.snapshots) < 5:  # Need some history
            return
        
        # Get recent snapshots for comparison
        recent = list(self.snapshots)[-5:]
        avg_cpu = statistics.mean([s.cpu_percent for s in recent])
        avg_memory = statistics.mean([s.memory_mb for s in recent])
        
        # Check for spikes
        if snapshot.cpu_percent > avg_cpu * 2 and snapshot.cpu_percent > 50:
            logger.warn(LogCategory.PERFORMANCE, f"CPU usage spike detected: {snapshot.cpu_percent:.1f}%",
                       context={"current": snapshot.cpu_percent, "average": avg_cpu})
        
        if snapshot.memory_mb > avg_memory * 1.5 and snapshot.memory_mb > 500:
            logger.warn(LogCategory.PERFORMANCE, f"Memory usage spike detected: {snapshot.memory_mb:.1f}MB",
                       context={"current": snapshot.memory_mb, "average": avg_memory})
    
    def get_current_snapshot(self) -> Optional[ResourceSnapshot]:
        """Get the most recent resource snapshot"""
        if self.snapshots:
            return self.snapshots[-1]
        return None
    
    def get_resource_history(self, minutes: int = 10) -> List[ResourceSnapshot]:
        """Get resource history for the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [s for s in self.snapshots if s.timestamp >= cutoff_time]


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system
    """
    
    def __init__(self):
        self.metric_collector = MetricCollector()
        self.system_monitor = SystemMonitor()
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self.alerts: List[Alert] = []
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Timing contexts
        self.active_timers: Dict[str, float] = {}
        self.timer_lock = threading.RLock()
        
        # Performance baselines
        self.baselines: Dict[str, Dict[str, float]] = {}
        
        # Initialize default thresholds
        self._setup_default_thresholds()
    
    def _setup_default_thresholds(self):
        """Setup default performance thresholds"""
        self.thresholds.update({
            "cpu_percent": PerformanceThreshold(70.0, 90.0, MetricType.GAUGE, "gt"),
            "memory_mb": PerformanceThreshold(1024.0, 2048.0, MetricType.GAUGE, "gt"),
            "response_time_ms": PerformanceThreshold(5000.0, 10000.0, MetricType.TIMER, "gt"),
            "error_rate": PerformanceThreshold(0.05, 0.1, MetricType.GAUGE, "gt"),
            "llm_call_duration_ms": PerformanceThreshold(30000.0, 60000.0, MetricType.TIMER, "gt")
        })
    
    def start_monitoring(self):
        """Start performance monitoring"""
        self.system_monitor.start()
        
        # Start periodic system metric collection
        threading.Thread(target=self._collect_system_metrics_loop, daemon=True).start()
        
        logger.info(LogCategory.PERFORMANCE, "Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.system_monitor.stop()
        logger.info(LogCategory.PERFORMANCE, "Performance monitoring stopped")
    
    def add_threshold(self, metric_name: str, threshold: PerformanceThreshold):
        """Add or update a performance threshold"""
        self.thresholds[metric_name] = threshold
        logger.debug(LogCategory.PERFORMANCE, f"Added threshold for {metric_name}",
                    context={
                        "warning": threshold.warning_threshold,
                        "critical": threshold.critical_threshold
                    })
    
    def subscribe_to_alerts(self, callback: Callable[[Alert], None]):
        """Subscribe to performance alerts"""
        self.alert_callbacks.append(callback)
    
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     metric_type: MetricType = MetricType.GAUGE,
                     tags: Optional[Dict[str, str]] = None):
        """Record a performance metric"""
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            metric_type=metric_type
        )
        
        self.metric_collector.add_metric(metric)
        
        # Check thresholds
        self._check_threshold(metric)
        
        # Log significant metrics
        if metric_type in [MetricType.TIMER, MetricType.COUNTER]:
            logger.debug(LogCategory.PERFORMANCE, f"Metric recorded: {name}",
                        context={"value": value, "type": metric_type.value, "tags": tags})
    
    def start_timer(self, timer_name: str) -> str:
        """Start a performance timer"""
        timer_id = f"{timer_name}_{int(time.time() * 1000)}"
        with self.timer_lock:
            self.active_timers[timer_id] = time.time()
        
        logger.debug(LogCategory.PERFORMANCE, f"Started timer: {timer_name}",
                    context={"timer_id": timer_id})
        return timer_id
    
    def end_timer(self, timer_id: str, metric_name: Optional[str] = None) -> float:
        """End a performance timer and record the duration"""
        with self.timer_lock:
            start_time = self.active_timers.pop(timer_id, None)
        
        if start_time is None:
            logger.warn(LogCategory.PERFORMANCE, f"Timer not found: {timer_id}")
            return 0.0
        
        duration_ms = (time.time() - start_time) * 1000
        
        if metric_name:
            self.record_metric(metric_name, duration_ms, MetricType.TIMER)
        
        logger.debug(LogCategory.PERFORMANCE, f"Timer completed: {timer_id}",
                    context={"duration_ms": duration_ms, "metric_name": metric_name})
        
        return duration_ms
    
    def record_operation_time(self, operation_name: str, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record operation timing"""
        self.record_metric(f"{operation_name}_duration_ms", duration_ms, MetricType.TIMER, tags)
        
        # Update baseline
        if operation_name not in self.baselines:
            self.baselines[operation_name] = {"total_time": 0.0, "count": 0}
        
        baseline = self.baselines[operation_name]
        baseline["total_time"] += duration_ms
        baseline["count"] += 1
        baseline["avg_duration_ms"] = baseline["total_time"] / baseline["count"]
    
    def _collect_system_metrics_loop(self):
        """Periodic system metrics collection"""
        while True:
            try:
                snapshot = self.system_monitor.get_current_snapshot()
                if snapshot:
                    # Record system metrics
                    self.record_metric("cpu_percent", snapshot.cpu_percent)
                    self.record_metric("memory_mb", snapshot.memory_mb)
                    self.record_metric("memory_percent", snapshot.memory_percent)
                    self.record_metric("disk_read_mb_per_sec", snapshot.disk_io_read_mb)
                    self.record_metric("disk_write_mb_per_sec", snapshot.disk_io_write_mb)
                    self.record_metric("network_sent_mb_per_sec", snapshot.network_sent_mb)
                    self.record_metric("network_recv_mb_per_sec", snapshot.network_recv_mb)
                    self.record_metric("open_files", snapshot.open_files)
                    self.record_metric("thread_count", snapshot.thread_count)
                
                # Garbage collection metrics
                gc_stats = gc.get_stats()
                if gc_stats:
                    self.record_metric("gc_collections", sum(stat["collections"] for stat in gc_stats))
                
                # Python-specific metrics
                self.record_metric("python_objects", len(gc.get_objects()))
                
                time.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logger.error(LogCategory.PERFORMANCE, f"Error collecting system metrics: {e}")
                time.sleep(30)
    
    def _check_threshold(self, metric: Metric):
        """Check if metric crosses any thresholds"""
        threshold = self.thresholds.get(metric.name)
        if not threshold:
            return
        
        alert_level = threshold.check_threshold(metric.value)
        if alert_level:
            self._create_alert(metric, threshold, alert_level)
    
    def _create_alert(self, metric: Metric, threshold: PerformanceThreshold, level: AlertLevel):
        """Create a performance alert"""
        import uuid
        
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            level=level,
            metric_name=metric.name,
            threshold=threshold.critical_threshold if level == AlertLevel.CRITICAL else threshold.warning_threshold,
            current_value=metric.value,
            message=f"{metric.name} is {metric.value:.2f}, exceeding {level.value} threshold of {threshold.critical_threshold if level == AlertLevel.CRITICAL else threshold.warning_threshold}",
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-500:]
        
        # Log the alert
        log_level = LogLevel.CRITICAL if level == AlertLevel.CRITICAL else LogLevel.WARN
        logger.log(log_level, LogCategory.PERFORMANCE, f"Performance alert: {alert.message}",
                  context={
                      "alert_id": alert.alert_id,
                      "metric_name": metric.name,
                      "current_value": metric.value,
                      "threshold": alert.threshold,
                      "level": level.value
                  },
                  tags=["alert", "performance"])
        
        # Notify subscribers
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(LogCategory.PERFORMANCE, f"Error in alert callback: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        current_snapshot = self.system_monitor.get_current_snapshot()
        
        # Recent metrics stats
        metric_stats = {}
        for metric_name in ["cpu_percent", "memory_mb", "response_time_ms", "llm_call_duration_ms"]:
            stats = self.metric_collector.get_metric_stats(metric_name, window_minutes=5)
            if stats:
                metric_stats[metric_name] = stats
        
        # Active alerts
        active_alerts = [alert for alert in self.alerts[-50:] if not alert.resolved]
        
        # Performance baselines
        baselines_summary = {
            name: {"avg_duration_ms": data["avg_duration_ms"], "count": data["count"]}
            for name, data in self.baselines.items()
        }
        
        return {
            "current_resources": current_snapshot._asdict() if current_snapshot else None,
            "metric_stats": metric_stats,
            "active_alerts": len(active_alerts),
            "total_alerts": len(self.alerts),
            "baselines": baselines_summary,
            "active_timers": len(self.active_timers),
            "thresholds_configured": len(self.thresholds)
        }
    
    def get_alerts(self, limit: int = 50, resolved: Optional[bool] = None) -> List[Alert]:
        """Get recent alerts"""
        alerts = self.alerts[-limit:] if limit else self.alerts
        
        if resolved is not None:
            alerts = [alert for alert in alerts if alert.resolved == resolved]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


# Context manager for timing operations
class TimingContext:
    """Context manager for timing operations with automatic metric recording"""
    
    def __init__(self, operation_name: str, tags: Optional[Dict[str, str]] = None):
        self.operation_name = operation_name
        self.tags = tags
        self.start_time = None
        self.timer_id = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.timer_id = performance_monitor.start_timer(self.operation_name)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = performance_monitor.end_timer(self.timer_id)
        
        # Record with success/failure tag
        tags = self.tags.copy() if self.tags else {}
        tags["success"] = str(exc_type is None)
        
        performance_monitor.record_operation_time(self.operation_name, duration_ms, tags)
        
        # Log slow operations
        if duration_ms > 5000:  # 5 seconds
            logger.warn(LogCategory.PERFORMANCE, f"Slow operation detected: {self.operation_name}",
                       context={
                           "duration_ms": duration_ms,
                           "operation": self.operation_name,
                           "tags": tags
                       })


# Decorator for automatic timing
def timed_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for automatic operation timing"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with TimingContext(operation_name, tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator