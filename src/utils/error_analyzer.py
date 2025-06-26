"""
Advanced Error Analysis and Classification System
Provides intelligent error categorization, pattern detection, and resolution suggestions
"""

import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, Counter
import json

from .advanced_logger import logger, LogCategory, LogLevel


class ErrorCategory(Enum):
    DART_SYNTAX = "dart_syntax"
    DART_TYPE = "dart_type"
    DART_IMPORT = "dart_import"
    DART_UNDEFINED = "dart_undefined"
    FLUTTER_WIDGET = "flutter_widget"
    FLUTTER_STATE = "flutter_state"
    LLM_RESPONSE = "llm_response"
    LLM_PARSING = "llm_parsing"
    FILE_OPERATION = "file_operation"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    PIPELINE = "pipeline"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorResolution(Enum):
    AUTO_FIXABLE = "auto_fixable"
    SUGGESTION_AVAILABLE = "suggestion_available"
    MANUAL_REQUIRED = "manual_required"
    INVESTIGATION_NEEDED = "investigation_needed"


@dataclass
class ErrorPattern:
    """Represents a pattern in error messages"""
    pattern_id: str
    regex_pattern: str
    category: ErrorCategory
    severity: ErrorSeverity
    resolution_type: ErrorResolution
    description: str
    auto_fix_template: Optional[str] = None
    suggestion: Optional[str] = None
    documentation_link: Optional[str] = None


@dataclass
class ErrorInstance:
    """Individual error occurrence"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    resolution_type: ErrorResolution
    component: str
    operation: str
    message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    pattern_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    suggestion: Optional[str] = None
    auto_fix_applied: bool = False


@dataclass
class ErrorCluster:
    """Group of related errors"""
    cluster_id: str
    pattern_id: Optional[str]
    category: ErrorCategory
    count: int
    first_seen: datetime
    last_seen: datetime
    error_instances: List[str]  # Error IDs
    severity: ErrorSeverity
    resolution_suggestions: List[str]
    impact_score: float


class ErrorPatternMatcher:
    """Matches errors against known patterns"""
    
    def __init__(self):
        self.patterns: List[ErrorPattern] = []
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default error patterns for common issues"""
        
        # Dart syntax errors
        self.patterns.extend([
            ErrorPattern(
                pattern_id="dart_missing_semicolon",
                regex_pattern=r"Expected ';'",
                category=ErrorCategory.DART_SYNTAX,
                severity=ErrorSeverity.LOW,
                resolution_type=ErrorResolution.AUTO_FIXABLE,
                description="Missing semicolon in Dart code",
                auto_fix_template="Add semicolon at end of statement",
                suggestion="Check for missing semicolons at the end of statements"
            ),
            ErrorPattern(
                pattern_id="dart_unbalanced_braces",
                regex_pattern=r"Expected '\}'" + r"|Unbalanced.*brace",
                category=ErrorCategory.DART_SYNTAX,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Unbalanced braces in Dart code",
                suggestion="Check for missing or extra braces in your code blocks"
            ),
            ErrorPattern(
                pattern_id="dart_undefined_method",
                regex_pattern=r"The method '(\w+)' isn't defined for the type '(\w+)'",
                category=ErrorCategory.DART_UNDEFINED,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Method not defined for type",
                suggestion="Check method name spelling or import required packages"
            ),
            
            # Dart type errors
            ErrorPattern(
                pattern_id="dart_type_mismatch",
                regex_pattern=r"A value of type '(\w+)' can't be assigned to a variable of type '(\w+)'",
                category=ErrorCategory.DART_TYPE,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Type mismatch assignment",
                suggestion="Check variable types and ensure compatible assignment"
            ),
            ErrorPattern(
                pattern_id="dart_null_safety",
                regex_pattern=r"The property '(\w+)' can't be unconditionally accessed because the receiver can be 'null'",
                category=ErrorCategory.DART_TYPE,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Null safety violation",
                suggestion="Use null-aware operators (?.) or null checks"
            ),
            
            # Import errors
            ErrorPattern(
                pattern_id="dart_import_not_found",
                regex_pattern=r"Target of URI doesn't exist: '([^']+)'",
                category=ErrorCategory.DART_IMPORT,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Import file not found",
                suggestion="Check file path or add missing dependency to pubspec.yaml"
            ),
            ErrorPattern(
                pattern_id="dart_unused_import",
                regex_pattern=r"Unused import: '([^']+)'",
                category=ErrorCategory.DART_IMPORT,
                severity=ErrorSeverity.LOW,
                resolution_type=ErrorResolution.AUTO_FIXABLE,
                description="Unused import",
                auto_fix_template="Remove unused import statement",
                suggestion="Remove unused import to clean up code"
            ),
            
            # Flutter widget errors
            ErrorPattern(
                pattern_id="flutter_widget_context",
                regex_pattern=r"Navigator operation requested with a context that does not include a Navigator",
                category=ErrorCategory.FLUTTER_WIDGET,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Navigator context error",
                suggestion="Ensure Navigator.of(context) is called within a widget that has a Navigator ancestor"
            ),
            ErrorPattern(
                pattern_id="flutter_state_error",
                regex_pattern=r"setState\(\) called after dispose\(\)",
                category=ErrorCategory.FLUTTER_STATE,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="setState called after dispose",
                suggestion="Check if widget is mounted before calling setState()"
            ),
            
            # LLM and parsing errors
            ErrorPattern(
                pattern_id="llm_response_empty",
                regex_pattern=r"Empty response from LLM|No LLM response",
                category=ErrorCategory.LLM_RESPONSE,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.INVESTIGATION_NEEDED,
                description="Empty LLM response",
                suggestion="Check LLM API connectivity and rate limits"
            ),
            ErrorPattern(
                pattern_id="llm_parsing_failed",
                regex_pattern=r"Failed to parse LLM response|Invalid LLM format",
                category=ErrorCategory.LLM_PARSING,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="LLM response parsing failed",
                suggestion="Check LLM response format and parsing logic"
            ),
            
            # File operation errors
            ErrorPattern(
                pattern_id="file_not_found",
                regex_pattern=r"No such file or directory|File not found",
                category=ErrorCategory.FILE_OPERATION,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="File not found",
                suggestion="Check file path and ensure file exists"
            ),
            ErrorPattern(
                pattern_id="file_permission_denied",
                regex_pattern=r"Permission denied|Access denied",
                category=ErrorCategory.FILE_OPERATION,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.MANUAL_REQUIRED,
                description="File permission denied",
                suggestion="Check file permissions and access rights"
            ),
            
            # Network errors
            ErrorPattern(
                pattern_id="network_timeout",
                regex_pattern=r"timeout|timed out|Connection timeout",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                resolution_type=ErrorResolution.SUGGESTION_AVAILABLE,
                description="Network timeout",
                suggestion="Check network connectivity and increase timeout if needed"
            ),
            ErrorPattern(
                pattern_id="network_connection_refused",
                regex_pattern=r"Connection refused|Connection reset",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.HIGH,
                resolution_type=ErrorResolution.INVESTIGATION_NEEDED,
                description="Network connection refused",
                suggestion="Check if target service is running and accessible"
            )
        ])
    
    def match_pattern(self, error_message: str, stack_trace: Optional[str] = None) -> Optional[ErrorPattern]:
        """Match error message against known patterns"""
        for pattern in self.patterns:
            if re.search(pattern.regex_pattern, error_message, re.IGNORECASE):
                return pattern
        
        return None
    
    def add_pattern(self, pattern: ErrorPattern):
        """Add a new error pattern"""
        self.patterns.append(pattern)
        logger.debug(LogCategory.ERROR, f"Added error pattern: {pattern.pattern_id}",
                    context={"pattern": asdict(pattern)})
    
    def get_patterns_by_category(self, category: ErrorCategory) -> List[ErrorPattern]:
        """Get all patterns for a specific category"""
        return [p for p in self.patterns if p.category == category]


class ErrorAnalyzer:
    """
    Advanced error analysis and classification system
    """
    
    def __init__(self, max_errors: int = 10000):
        self.max_errors = max_errors
        self.pattern_matcher = ErrorPatternMatcher()
        
        # Storage
        self.error_instances: Dict[str, ErrorInstance] = {}
        self.error_clusters: Dict[str, ErrorCluster] = {}
        
        # Pattern tracking
        self.pattern_frequencies: Counter = Counter()
        self.category_frequencies: Counter = Counter()
        
        # Resolution tracking
        self.auto_fix_success_rate: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "total": 0})
        
        # Trending analysis
        self.hourly_error_counts: Dict[str, Counter] = defaultdict(Counter)  # hour -> category -> count
        
        # Error relationships
        self.error_correlations: Dict[str, Set[str]] = defaultdict(set)  # error_id -> related_error_ids
    
    def analyze_error(self, 
                     component: str,
                     operation: str,
                     message: str,
                     stack_trace: Optional[str] = None,
                     context: Optional[Dict[str, Any]] = None,
                     file_path: Optional[str] = None,
                     line_number: Optional[int] = None,
                     column_number: Optional[int] = None) -> ErrorInstance:
        """Analyze and classify an error"""
        
        error_id = self._generate_error_id(component, operation, message)
        
        # Match against patterns
        pattern = self.pattern_matcher.match_pattern(message, stack_trace)
        
        # Determine category, severity, and resolution if no pattern matched
        if pattern:
            category = pattern.category
            severity = pattern.severity
            resolution_type = pattern.resolution_type
            pattern_id = pattern.pattern_id
            suggestion = pattern.suggestion
        else:
            category = self._classify_error_category(message, component)
            severity = self._determine_severity(message, component)
            resolution_type = self._determine_resolution_type(category, severity)
            pattern_id = None
            suggestion = self._generate_generic_suggestion(category, message)
        
        # Create error instance
        error_instance = ErrorInstance(
            error_id=error_id,
            timestamp=datetime.now(),
            category=category,
            severity=severity,
            resolution_type=resolution_type,
            component=component,
            operation=operation,
            message=message,
            stack_trace=stack_trace,
            context=context or {},
            pattern_id=pattern_id,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            suggestion=suggestion
        )
        
        # Store error instance
        self.error_instances[error_id] = error_instance
        
        # Update tracking
        self._update_tracking(error_instance)
        
        # Cluster similar errors
        self._update_clusters(error_instance)
        
        # Check for correlations
        self._analyze_correlations(error_instance)
        
        # Cleanup old errors
        self._cleanup_old_errors()
        
        # Log the analysis
        logger.error(LogCategory.ERROR, f"Error analyzed: {component}.{operation}",
                    context={
                        "error_id": error_id,
                        "category": category.value,
                        "severity": severity.value,
                        "resolution_type": resolution_type.value,
                        "pattern_id": pattern_id,
                        "message": message[:200],  # Truncate for logging
                        "file_path": file_path,
                        "line_number": line_number
                    },
                    tags=["error_analysis", category.value])
        
        return error_instance
    
    def _generate_error_id(self, component: str, operation: str, message: str) -> str:
        """Generate unique error ID"""
        content = f"{component}:{operation}:{message}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _classify_error_category(self, message: str, component: str) -> ErrorCategory:
        """Classify error category based on message and component"""
        message_lower = message.lower()
        
        # Component-based classification
        if "dart" in component.lower() or "analysis" in component.lower():
            if "import" in message_lower or "library" in message_lower:
                return ErrorCategory.DART_IMPORT
            elif "type" in message_lower or "assign" in message_lower:
                return ErrorCategory.DART_TYPE
            elif "undefined" in message_lower or "not defined" in message_lower:
                return ErrorCategory.DART_UNDEFINED
            else:
                return ErrorCategory.DART_SYNTAX
        
        elif "flutter" in component.lower() or "widget" in message_lower:
            if "state" in message_lower or "setstate" in message_lower:
                return ErrorCategory.FLUTTER_STATE
            else:
                return ErrorCategory.FLUTTER_WIDGET
        
        elif "llm" in component.lower():
            if "parse" in message_lower or "format" in message_lower:
                return ErrorCategory.LLM_PARSING
            else:
                return ErrorCategory.LLM_RESPONSE
        
        elif "file" in component.lower() or "file" in message_lower:
            return ErrorCategory.FILE_OPERATION
        
        elif "network" in message_lower or "connection" in message_lower:
            return ErrorCategory.NETWORK
        
        elif "pipeline" in component.lower():
            return ErrorCategory.PIPELINE
        
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, message: str, component: str) -> ErrorSeverity:
        """Determine error severity"""
        message_lower = message.lower()
        
        # Critical keywords
        critical_keywords = ["critical", "fatal", "crash", "abort", "panic"]
        if any(keyword in message_lower for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL
        
        # High severity keywords
        high_keywords = ["error", "failed", "exception", "undefined", "not found"]
        if any(keyword in message_lower for keyword in high_keywords):
            return ErrorSeverity.HIGH
        
        # Medium severity keywords
        medium_keywords = ["warning", "warn", "deprecated", "invalid"]
        if any(keyword in message_lower for keyword in medium_keywords):
            return ErrorSeverity.MEDIUM
        
        # Default to low
        return ErrorSeverity.LOW
    
    def _determine_resolution_type(self, category: ErrorCategory, severity: ErrorSeverity) -> ErrorResolution:
        """Determine resolution type based on category and severity"""
        
        # Auto-fixable categories
        auto_fixable_categories = [ErrorCategory.DART_IMPORT]
        if category in auto_fixable_categories and severity in [ErrorSeverity.LOW, ErrorSeverity.MEDIUM]:
            return ErrorResolution.AUTO_FIXABLE
        
        # Manual required for critical errors
        if severity == ErrorSeverity.CRITICAL:
            return ErrorResolution.MANUAL_REQUIRED
        
        # Investigation needed for unknown or complex issues
        if category in [ErrorCategory.UNKNOWN, ErrorCategory.SYSTEM, ErrorCategory.NETWORK]:
            return ErrorResolution.INVESTIGATION_NEEDED
        
        # Default to suggestion available
        return ErrorResolution.SUGGESTION_AVAILABLE
    
    def _generate_generic_suggestion(self, category: ErrorCategory, message: str) -> str:
        """Generate generic suggestion based on category"""
        suggestions = {
            ErrorCategory.DART_SYNTAX: "Check Dart syntax and ensure proper formatting",
            ErrorCategory.DART_TYPE: "Verify variable types and type casting",
            ErrorCategory.DART_IMPORT: "Check import statements and dependencies",
            ErrorCategory.DART_UNDEFINED: "Verify method/variable names and imports",
            ErrorCategory.FLUTTER_WIDGET: "Check widget hierarchy and context usage",
            ErrorCategory.FLUTTER_STATE: "Verify state management and lifecycle methods",
            ErrorCategory.LLM_RESPONSE: "Check LLM API connectivity and configuration",
            ErrorCategory.LLM_PARSING: "Verify LLM response format and parsing logic",
            ErrorCategory.FILE_OPERATION: "Check file paths and permissions",
            ErrorCategory.NETWORK: "Verify network connectivity and endpoints",
            ErrorCategory.CONFIGURATION: "Check configuration settings",
            ErrorCategory.SYSTEM: "Check system resources and environment",
            ErrorCategory.PIPELINE: "Review pipeline configuration and dependencies",
            ErrorCategory.UNKNOWN: "Review error details and context for debugging"
        }
        
        return suggestions.get(category, "Review error message and context for resolution steps")
    
    def _update_tracking(self, error_instance: ErrorInstance):
        """Update error tracking statistics"""
        self.pattern_frequencies[error_instance.pattern_id or "no_pattern"] += 1
        self.category_frequencies[error_instance.category.value] += 1
        
        # Update hourly tracking
        hour_key = error_instance.timestamp.strftime("%Y-%m-%d-%H")
        self.hourly_error_counts[hour_key][error_instance.category.value] += 1
    
    def _update_clusters(self, error_instance: ErrorInstance):
        """Update error clustering"""
        # Find or create cluster
        cluster_key = f"{error_instance.category.value}:{error_instance.pattern_id or 'no_pattern'}"
        
        if cluster_key not in self.error_clusters:
            self.error_clusters[cluster_key] = ErrorCluster(
                cluster_id=cluster_key,
                pattern_id=error_instance.pattern_id,
                category=error_instance.category,
                count=0,
                first_seen=error_instance.timestamp,
                last_seen=error_instance.timestamp,
                error_instances=[],
                severity=error_instance.severity,
                resolution_suggestions=[],
                impact_score=0.0
            )
        
        # Update cluster
        cluster = self.error_clusters[cluster_key]
        cluster.count += 1
        cluster.last_seen = error_instance.timestamp
        cluster.error_instances.append(error_instance.error_id)
        
        # Update severity to highest seen
        severity_order = {ErrorSeverity.LOW: 1, ErrorSeverity.MEDIUM: 2, ErrorSeverity.HIGH: 3, ErrorSeverity.CRITICAL: 4}
        if severity_order[error_instance.severity] > severity_order[cluster.severity]:
            cluster.severity = error_instance.severity
        
        # Update impact score (frequency * severity weight)
        severity_weights = {ErrorSeverity.LOW: 1, ErrorSeverity.MEDIUM: 2, ErrorSeverity.HIGH: 4, ErrorSeverity.CRITICAL: 8}
        cluster.impact_score = cluster.count * severity_weights[cluster.severity]
        
        # Keep only recent error instances in cluster
        if len(cluster.error_instances) > 100:
            cluster.error_instances = cluster.error_instances[-50:]
    
    def _analyze_correlations(self, error_instance: ErrorInstance):
        """Analyze correlations between errors"""
        # Look for errors that occurred around the same time
        time_window = timedelta(minutes=5)
        start_time = error_instance.timestamp - time_window
        end_time = error_instance.timestamp + time_window
        
        related_errors = [
            error_id for error_id, instance in self.error_instances.items()
            if start_time <= instance.timestamp <= end_time and error_id != error_instance.error_id
        ]
        
        # Store correlations
        if related_errors:
            self.error_correlations[error_instance.error_id].update(related_errors)
            
            # Update reverse correlations
            for related_id in related_errors:
                self.error_correlations[related_id].add(error_instance.error_id)
    
    def _cleanup_old_errors(self):
        """Clean up old error instances to prevent memory leaks"""
        if len(self.error_instances) <= self.max_errors:
            return
        
        # Sort by timestamp and keep only recent errors
        sorted_errors = sorted(self.error_instances.items(), key=lambda x: x[1].timestamp, reverse=True)
        to_keep = dict(sorted_errors[:self.max_errors])
        to_remove = dict(sorted_errors[self.max_errors:])
        
        self.error_instances = to_keep
        
        # Clean up correlations for removed errors
        for error_id in to_remove.keys():
            self.error_correlations.pop(error_id, None)
        
        logger.debug(LogCategory.ERROR, f"Cleaned up {len(to_remove)} old error instances")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get comprehensive error summary"""
        now = datetime.now()
        
        # Recent errors (last hour)
        recent_errors = [
            error for error in self.error_instances.values()
            if now - error.timestamp <= timedelta(hours=1)
        ]
        
        # Top error patterns
        top_patterns = self.pattern_frequencies.most_common(10)
        
        # Category breakdown
        category_breakdown = dict(self.category_frequencies)
        
        # Severity distribution
        severity_counts = Counter()
        for error in self.error_instances.values():
            severity_counts[error.severity.value] += 1
        
        # Resolution type distribution
        resolution_counts = Counter()
        for error in self.error_instances.values():
            resolution_counts[error.resolution_type.value] += 1
        
        # Top clusters by impact
        top_clusters = sorted(
            self.error_clusters.values(),
            key=lambda c: c.impact_score,
            reverse=True
        )[:10]
        
        return {
            "total_errors": len(self.error_instances),
            "recent_errors_1h": len(recent_errors),
            "category_breakdown": category_breakdown,
            "severity_distribution": dict(severity_counts),
            "resolution_distribution": dict(resolution_counts),
            "top_patterns": [{"pattern": p, "count": c} for p, c in top_patterns],
            "top_clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "category": c.category.value,
                    "count": c.count,
                    "impact_score": c.impact_score,
                    "severity": c.severity.value
                } for c in top_clusters
            ],
            "auto_fix_success_rates": dict(self.auto_fix_success_rate)
        }
    
    def get_trending_errors(self, hours: int = 24) -> Dict[str, Any]:
        """Get trending error analysis"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Count errors by hour for each category
        hourly_trends = {}
        for hour_key, category_counts in self.hourly_error_counts.items():
            try:
                hour_time = datetime.strptime(hour_key, "%Y-%m-%d-%H")
                if hour_time >= cutoff_time:
                    hourly_trends[hour_key] = dict(category_counts)
            except ValueError:
                continue
        
        # Calculate trend direction for each category
        category_trends = {}
        for category in ErrorCategory:
            recent_counts = []
            for hour_key in sorted(hourly_trends.keys())[-6:]:  # Last 6 hours
                count = hourly_trends[hour_key].get(category.value, 0)
                recent_counts.append(count)
            
            if len(recent_counts) >= 2:
                # Simple trend calculation: compare first half with second half
                mid = len(recent_counts) // 2
                first_half_avg = sum(recent_counts[:mid]) / mid if mid > 0 else 0
                second_half_avg = sum(recent_counts[mid:]) / (len(recent_counts) - mid)
                
                if second_half_avg > first_half_avg * 1.5:
                    trend = "increasing"
                elif second_half_avg < first_half_avg * 0.5:
                    trend = "decreasing"
                else:
                    trend = "stable"
                
                category_trends[category.value] = {
                    "trend": trend,
                    "recent_avg": second_half_avg,
                    "previous_avg": first_half_avg
                }
        
        return {
            "hourly_trends": hourly_trends,
            "category_trends": category_trends,
            "analysis_period_hours": hours
        }
    
    def get_error_correlations(self, error_id: str) -> List[Dict[str, Any]]:
        """Get errors correlated with a specific error"""
        related_ids = self.error_correlations.get(error_id, set())
        
        correlations = []
        for related_id in related_ids:
            if related_id in self.error_instances:
                related_error = self.error_instances[related_id]
                correlations.append({
                    "error_id": related_id,
                    "category": related_error.category.value,
                    "severity": related_error.severity.value,
                    "component": related_error.component,
                    "operation": related_error.operation,
                    "message": related_error.message[:100],  # Truncated
                    "timestamp": related_error.timestamp.isoformat()
                })
        
        return correlations
    
    def suggest_resolution(self, error_id: str) -> Dict[str, Any]:
        """Get resolution suggestions for a specific error"""
        if error_id not in self.error_instances:
            return {"error": "Error not found"}
        
        error = self.error_instances[error_id]
        
        # Get pattern-specific suggestions
        suggestions = []
        if error.suggestion:
            suggestions.append(error.suggestion)
        
        # Get cluster-based suggestions
        cluster_key = f"{error.category.value}:{error.pattern_id or 'no_pattern'}"
        if cluster_key in self.error_clusters:
            cluster = self.error_clusters[cluster_key]
            suggestions.extend(cluster.resolution_suggestions)
        
        # Get correlation-based suggestions
        correlations = self.get_error_correlations(error_id)
        if correlations:
            suggestions.append("This error occurred with other errors - check for systemic issues")
        
        # Auto-fix availability
        auto_fix_available = error.resolution_type == ErrorResolution.AUTO_FIXABLE
        
        return {
            "error_id": error_id,
            "category": error.category.value,
            "severity": error.severity.value,
            "resolution_type": error.resolution_type.value,
            "auto_fix_available": auto_fix_available,
            "suggestions": list(set(suggestions)),  # Remove duplicates
            "correlations_count": len(correlations),
            "cluster_frequency": self.error_clusters.get(cluster_key, {}).get("count", 0) if cluster_key in self.error_clusters else 0
        }


# Global error analyzer instance
error_analyzer = ErrorAnalyzer()


# Convenience function for quick error analysis
def analyze_error(component: str,
                 operation: str, 
                 error: Exception,
                 context: Optional[Dict[str, Any]] = None) -> ErrorInstance:
    """Quick error analysis from exception"""
    import traceback
    
    return error_analyzer.analyze_error(
        component=component,
        operation=operation,
        message=str(error),
        stack_trace=traceback.format_exc(),
        context=context
    )