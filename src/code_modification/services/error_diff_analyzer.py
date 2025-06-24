"""
Error Diff Analyzer
Tracks how errors change between recovery attempts to measure progress
"""

import time
import json
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

# Import existing analysis types
from .dart_analysis import AnalysisIssue, AnalysisType, AnalysisResult

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class ErrorChangeType(Enum):
    """Types of error changes between attempts"""
    FIXED = "fixed"           # Error was resolved
    NEW = "new"               # New error appeared
    PERSISTENT = "persistent" # Error still exists
    MODIFIED = "modified"     # Error changed but not fixed


@dataclass
class ErrorChange:
    """Represents a change in error state"""
    change_type: ErrorChangeType
    issue: AnalysisIssue
    previous_issue: Optional[AnalysisIssue] = None
    context: Optional[str] = None


@dataclass
class ErrorSnapshot:
    """Snapshot of errors at a specific time"""
    timestamp: float
    attempt_number: int
    total_errors: int
    total_warnings: int
    issues: List[AnalysisIssue]
    error_categories: Dict[str, int] = field(default_factory=dict)
    context: Optional[str] = None


@dataclass
class ErrorDiff:
    """Difference between two error snapshots"""
    from_snapshot: ErrorSnapshot
    to_snapshot: ErrorSnapshot
    changes: List[ErrorChange]
    summary: Dict[str, int] = field(default_factory=dict)
    progress_score: float = 0.0
    regression_score: float = 0.0


class ErrorDiffAnalyzer:
    """
    Analyzes how errors change between recovery attempts
    """
    
    def __init__(self):
        self.snapshots: List[ErrorSnapshot] = []
        self.diffs: List[ErrorDiff] = []
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, "ErrorDiffAnalyzer initialized")
    
    def take_snapshot(self, analysis_result: AnalysisResult, attempt_number: int, 
                     context: Optional[str] = None) -> ErrorSnapshot:
        """
        Take a snapshot of current error state
        
        Args:
            analysis_result: Result from dart analyze
            attempt_number: Current recovery attempt number
            context: Optional context description
            
        Returns:
            ErrorSnapshot with current state
        """
        timestamp = time.time()
        
        # Categorize errors
        error_categories = self._categorize_issues(analysis_result.issues)
        
        snapshot = ErrorSnapshot(
            timestamp=timestamp,
            attempt_number=attempt_number,
            total_errors=len(analysis_result.errors),
            total_warnings=len(analysis_result.warnings),
            issues=analysis_result.issues.copy(),
            error_categories=error_categories,
            context=context
        )
        
        self.snapshots.append(snapshot)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, 
                       f"Error snapshot taken for attempt {attempt_number}",
                       context={
                           "total_errors": snapshot.total_errors,
                           "total_warnings": snapshot.total_warnings,
                           "categories": error_categories,
                           "context": context
                       })
        
        return snapshot
    
    def analyze_diff(self, previous_snapshot: Optional[ErrorSnapshot] = None,
                    current_snapshot: Optional[ErrorSnapshot] = None) -> Optional[ErrorDiff]:
        """
        Analyze differences between two snapshots
        
        Args:
            previous_snapshot: Earlier snapshot (defaults to second-to-last)
            current_snapshot: Later snapshot (defaults to last)
            
        Returns:
            ErrorDiff with analysis or None if insufficient data
        """
        if len(self.snapshots) < 2:
            return None
        
        from_snapshot = previous_snapshot or self.snapshots[-2]
        to_snapshot = current_snapshot or self.snapshots[-1]
        
        # Find changes between snapshots
        changes = self._find_changes(from_snapshot, to_snapshot)
        
        # Calculate summary statistics
        summary = self._calculate_summary(changes)
        
        # Calculate progress and regression scores
        progress_score = self._calculate_progress_score(from_snapshot, to_snapshot, changes)
        regression_score = self._calculate_regression_score(changes)
        
        diff = ErrorDiff(
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
            changes=changes,
            summary=summary,
            progress_score=progress_score,
            regression_score=regression_score
        )
        
        self.diffs.append(diff)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.ERROR_FIXING, 
                       f"Error diff analyzed: attempt {from_snapshot.attempt_number} → {to_snapshot.attempt_number}",
                       context={
                           "changes_count": len(changes),
                           "progress_score": round(progress_score, 2),
                           "regression_score": round(regression_score, 2),
                           "summary": summary
                       })
        
        return diff
    
    def _categorize_issues(self, issues: List[AnalysisIssue]) -> Dict[str, int]:
        """Categorize issues by type and error patterns"""
        categories = defaultdict(int)
        
        for issue in issues:
            # Primary categorization by type
            categories[issue.type.value] += 1
            
            # Secondary categorization by error content
            message_lower = issue.message.lower()
            
            if issue.type == AnalysisType.ERROR:
                if any(pattern in message_lower for pattern in ["isn't defined", "undefined"]):
                    categories["undefined_symbols"] += 1
                elif any(pattern in message_lower for pattern in ["import", "library"]):
                    categories["import_errors"] += 1
                elif any(pattern in message_lower for pattern in ["type", "assigned", "expected"]):
                    categories["type_errors"] += 1
                elif any(pattern in message_lower for pattern in ["syntax", "expected ';'", "expected ')'"]):
                    categories["syntax_errors"] += 1
                else:
                    categories["other_errors"] += 1
        
        return dict(categories)
    
    def _find_changes(self, from_snapshot: ErrorSnapshot, to_snapshot: ErrorSnapshot) -> List[ErrorChange]:
        """Find changes between two snapshots"""
        changes = []
        
        # Create lookup dictionaries for efficient comparison
        from_issues = {self._issue_key(issue): issue for issue in from_snapshot.issues}
        to_issues = {self._issue_key(issue): issue for issue in to_snapshot.issues}
        
        # Find fixed issues (in previous but not in current)
        for key, issue in from_issues.items():
            if key not in to_issues:
                changes.append(ErrorChange(
                    change_type=ErrorChangeType.FIXED,
                    issue=issue,
                    context=f"Fixed: {issue.message[:50]}..."
                ))
        
        # Find new issues (in current but not in previous)
        for key, issue in to_issues.items():
            if key not in from_issues:
                changes.append(ErrorChange(
                    change_type=ErrorChangeType.NEW,
                    issue=issue,
                    context=f"New: {issue.message[:50]}..."
                ))
        
        # Find persistent or modified issues
        for key, current_issue in to_issues.items():
            if key in from_issues:
                previous_issue = from_issues[key]
                if self._issues_identical(previous_issue, current_issue):
                    changes.append(ErrorChange(
                        change_type=ErrorChangeType.PERSISTENT,
                        issue=current_issue,
                        previous_issue=previous_issue
                    ))
                else:
                    changes.append(ErrorChange(
                        change_type=ErrorChangeType.MODIFIED,
                        issue=current_issue,
                        previous_issue=previous_issue,
                        context=f"Modified: {previous_issue.message[:30]}... → {current_issue.message[:30]}..."
                    ))
        
        return changes
    
    def _issue_key(self, issue: AnalysisIssue) -> str:
        """Generate a key for issue comparison"""
        # Use file, line, and message type for matching
        return f"{issue.file_path}:{issue.line}:{issue.type.value}:{issue.rule_name or 'unknown'}"
    
    def _issues_identical(self, issue1: AnalysisIssue, issue2: AnalysisIssue) -> bool:
        """Check if two issues are identical"""
        return (
            issue1.file_path == issue2.file_path and
            issue1.line == issue2.line and
            issue1.column == issue2.column and
            issue1.message == issue2.message and
            issue1.type == issue2.type
        )
    
    def _calculate_summary(self, changes: List[ErrorChange]) -> Dict[str, int]:
        """Calculate summary statistics for changes"""
        summary = defaultdict(int)
        
        for change in changes:
            summary[change.change_type.value] += 1
            
            # Count by error type
            if change.issue.type == AnalysisType.ERROR:
                summary[f"errors_{change.change_type.value}"] += 1
            elif change.issue.type == AnalysisType.WARNING:
                summary[f"warnings_{change.change_type.value}"] += 1
        
        return dict(summary)
    
    def _calculate_progress_score(self, from_snapshot: ErrorSnapshot, 
                                to_snapshot: ErrorSnapshot, changes: List[ErrorChange]) -> float:
        """Calculate progress score (0-1, higher is better)"""
        if from_snapshot.total_errors == 0:
            return 1.0 if to_snapshot.total_errors == 0 else 0.0
        
        # Basic progress: reduction in total errors
        error_reduction = max(0, from_snapshot.total_errors - to_snapshot.total_errors)
        basic_progress = error_reduction / from_snapshot.total_errors
        
        # Bonus for actually fixing issues (not just moving them around)
        fixed_count = sum(1 for change in changes if change.change_type == ErrorChangeType.FIXED)
        new_count = sum(1 for change in changes if change.change_type == ErrorChangeType.NEW)
        
        if fixed_count > 0:
            fix_bonus = min(0.5, fixed_count / from_snapshot.total_errors)
        else:
            fix_bonus = 0.0
        
        # Penalty for introducing new errors
        if new_count > 0:
            new_penalty = min(0.3, new_count / max(1, from_snapshot.total_errors))
        else:
            new_penalty = 0.0
        
        total_score = basic_progress + fix_bonus - new_penalty
        return max(0.0, min(1.0, total_score))
    
    def _calculate_regression_score(self, changes: List[ErrorChange]) -> float:
        """Calculate regression score (0-1, lower is better)"""
        total_changes = len(changes)
        if total_changes == 0:
            return 0.0
        
        # Count negative changes
        new_count = sum(1 for change in changes if change.change_type == ErrorChangeType.NEW)
        
        return new_count / total_changes
    
    def get_overall_progress(self) -> Dict[str, any]:
        """Get overall progress summary across all attempts"""
        if len(self.snapshots) < 2:
            return {"status": "insufficient_data"}
        
        initial = self.snapshots[0]
        current = self.snapshots[-1]
        
        total_reduction = initial.total_errors - current.total_errors
        progress_percentage = (total_reduction / initial.total_errors * 100) if initial.total_errors > 0 else 0
        
        # Calculate average progress score
        avg_progress = sum(diff.progress_score for diff in self.diffs) / len(self.diffs) if self.diffs else 0.0
        avg_regression = sum(diff.regression_score for diff in self.diffs) / len(self.diffs) if self.diffs else 0.0
        
        return {
            "status": "analyzed",
            "attempts": len(self.snapshots),
            "initial_errors": initial.total_errors,
            "current_errors": current.total_errors,
            "total_reduction": total_reduction,
            "progress_percentage": round(progress_percentage, 1),
            "average_progress_score": round(avg_progress, 2),
            "average_regression_score": round(avg_regression, 2),
            "is_improving": total_reduction > 0,
            "latest_diff": self.diffs[-1] if self.diffs else None
        }
    
    def format_diff_summary(self, diff: ErrorDiff) -> str:
        """Format a diff summary for logging/display"""
        from_errors = diff.from_snapshot.total_errors
        to_errors = diff.to_snapshot.total_errors
        
        if from_errors == to_errors:
            change_str = f"stable at {to_errors}"
        elif to_errors < from_errors:
            reduction = from_errors - to_errors
            change_str = f"reduced {from_errors} → {to_errors} (-{reduction})"
        else:
            increase = to_errors - from_errors
            change_str = f"increased {from_errors} → {to_errors} (+{increase})"
        
        summary_parts = []
        if diff.summary.get("fixed", 0) > 0:
            summary_parts.append(f"✅ {diff.summary['fixed']} fixed")
        if diff.summary.get("new", 0) > 0:
            summary_parts.append(f"🆕 {diff.summary['new']} new")
        if diff.summary.get("persistent", 0) > 0:
            summary_parts.append(f"⏸️ {diff.summary['persistent']} persistent")
        
        details = " | ".join(summary_parts) if summary_parts else "no changes"
        
        return f"Errors {change_str} | {details} | Progress: {diff.progress_score:.2f}"
    
    def export_analysis(self) -> Dict[str, any]:
        """Export complete analysis data"""
        return {
            "snapshots": [
                {
                    "timestamp": snapshot.timestamp,
                    "attempt_number": snapshot.attempt_number,
                    "total_errors": snapshot.total_errors,
                    "total_warnings": snapshot.total_warnings,
                    "error_categories": snapshot.error_categories,
                    "context": snapshot.context
                }
                for snapshot in self.snapshots
            ],
            "diffs": [
                {
                    "from_attempt": diff.from_snapshot.attempt_number,
                    "to_attempt": diff.to_snapshot.attempt_number,
                    "summary": diff.summary,
                    "progress_score": diff.progress_score,
                    "regression_score": diff.regression_score,
                    "changes_count": len(diff.changes)
                }
                for diff in self.diffs
            ],
            "overall_progress": self.get_overall_progress()
        }


# Global instance for easy access
_error_diff_analyzer = None

def get_error_diff_analyzer() -> ErrorDiffAnalyzer:
    """Get or create the global error diff analyzer instance"""
    global _error_diff_analyzer
    if _error_diff_analyzer is None:
        _error_diff_analyzer = ErrorDiffAnalyzer()
    return _error_diff_analyzer

def reset_error_diff_analyzer():
    """Reset the global analyzer (for new recovery sessions)"""
    global _error_diff_analyzer
    _error_diff_analyzer = ErrorDiffAnalyzer()