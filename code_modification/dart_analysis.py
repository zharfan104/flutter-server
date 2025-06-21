"""
Dart Analysis Service
Runs dart analyze and parses output for error detection and fixing
"""

import subprocess
import os
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class AnalysisType(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    HINT = "hint"


@dataclass
class AnalysisIssue:
    """Represents a single analysis issue from dart analyze"""
    type: AnalysisType
    file_path: str
    line: int
    column: int
    message: str
    rule_name: Optional[str] = None
    severity: str = "medium"


@dataclass
class AnalysisResult:
    """Result of dart analyze run"""
    success: bool
    issues: List[AnalysisIssue]
    errors: List[AnalysisIssue]
    warnings: List[AnalysisIssue]
    output: str
    execution_time: float


class DartAnalysisService:
    """
    Service for running Dart analysis and parsing results
    Based on steve-backend's simple_dart_command.py but enhanced
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.lib_path = self.project_path / "lib"
        
    def run_analysis(self, target_path: Optional[str] = None) -> AnalysisResult:
        """
        Run dart analyze on the project
        
        Args:
            target_path: Specific path to analyze, defaults to lib directory
            
        Returns:
            AnalysisResult with parsed issues
        """
        import time
        start_time = time.time()
        
        # Default to lib directory if no target specified
        if target_path is None:
            target_path = str(self.lib_path)
        else:
            target_path = str(self.project_path / target_path)
            
        if not os.path.exists(target_path):
            return AnalysisResult(
                success=False,
                issues=[],
                errors=[AnalysisIssue(
                    type=AnalysisType.ERROR,
                    file_path=target_path,
                    line=0,
                    column=0,
                    message=f"Target path does not exist: {target_path}"
                )],
                warnings=[],
                output=f"Error: Target path does not exist: {target_path}",
                execution_time=time.time() - start_time
            )
        
        try:
            # Run dart analyze command
            command = ["dart", "analyze", target_path]
            print(f"Running: {' '.join(command)}")
            
            result = subprocess.run(
                command,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=60  # 60 second timeout
            )
            
            execution_time = time.time() - start_time
            full_output = result.stdout + result.stderr
            
            # Parse the output
            issues = self._parse_analyze_output(full_output)
            errors = [issue for issue in issues if issue.type == AnalysisType.ERROR]
            warnings = [issue for issue in issues if issue.type == AnalysisType.WARNING]
            
            # Success if no errors (warnings are OK)
            success = len(errors) == 0 and result.returncode == 0
            
            return AnalysisResult(
                success=success,
                issues=issues,
                errors=errors,
                warnings=warnings,
                output=full_output,
                execution_time=execution_time
            )
            
        except subprocess.TimeoutExpired:
            return AnalysisResult(
                success=False,
                issues=[],
                errors=[AnalysisIssue(
                    type=AnalysisType.ERROR,
                    file_path=target_path,
                    line=0,
                    column=0,
                    message="Dart analyze timed out after 60 seconds"
                )],
                warnings=[],
                output="Timeout: dart analyze took too long",
                execution_time=60.0
            )
            
        except Exception as e:
            return AnalysisResult(
                success=False,
                issues=[],
                errors=[AnalysisIssue(
                    type=AnalysisType.ERROR,
                    file_path=target_path,
                    line=0,
                    column=0,
                    message=f"Failed to run dart analyze: {str(e)}"
                )],
                warnings=[],
                output=f"Error: {str(e)}",
                execution_time=time.time() - start_time
            )
    
    def _parse_analyze_output(self, output: str) -> List[AnalysisIssue]:
        """
        Parse dart analyze output into structured issues
        
        Expected format examples:
        error • The method 'foo' isn't defined for the type 'Bar' • lib/main.dart:25:5 • undefined_method
        warning • Unused import • lib/main.dart:3:8 • unused_import
        """
        issues = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Match the dart analyze output format
            # Pattern: type • message • file:line:column • rule_name
            match = re.match(r'(error|warning|info|hint)\s*•\s*(.+?)\s*•\s*(.+?):(\d+):(\d+)\s*•\s*(.+)', line)
            
            if match:
                issue_type_str, message, file_path, line_num, column, rule_name = match.groups()
                
                # Convert type string to enum
                try:
                    issue_type = AnalysisType(issue_type_str.lower())
                except ValueError:
                    issue_type = AnalysisType.INFO
                
                # Determine severity
                severity = self._determine_severity(issue_type, rule_name, message)
                
                issues.append(AnalysisIssue(
                    type=issue_type,
                    file_path=file_path,
                    line=int(line_num),
                    column=int(column),
                    message=message.strip(),
                    rule_name=rule_name.strip(),
                    severity=severity
                ))
            
            # Also check for simpler formats without rule names
            elif re.match(r'(error|warning|info|hint)', line, re.IGNORECASE):
                # Fallback parsing for different output formats
                parts = line.split(' - ', 1)
                if len(parts) >= 2:
                    issue_type_str = parts[0].split()[0].lower()
                    try:
                        issue_type = AnalysisType(issue_type_str)
                    except ValueError:
                        issue_type = AnalysisType.INFO
                    
                    issues.append(AnalysisIssue(
                        type=issue_type,
                        file_path="unknown",
                        line=0,
                        column=0,
                        message=parts[1].strip(),
                        rule_name="unknown",
                        severity="medium"
                    ))
        
        return issues
    
    def _determine_severity(self, issue_type: AnalysisType, rule_name: str, message: str) -> str:
        """Determine severity level for prioritizing fixes"""
        
        if issue_type == AnalysisType.ERROR:
            # Critical errors that prevent compilation
            critical_patterns = [
                "isn't defined",
                "doesn't define a class",
                "can't be assigned",
                "undefined",
                "not found",
                "missing required",
                "expected"
            ]
            
            for pattern in critical_patterns:
                if pattern.lower() in message.lower():
                    return "high"
            
            return "high"  # All errors are high priority by default
        
        elif issue_type == AnalysisType.WARNING:
            # Important warnings
            important_warnings = [
                "unused_import",
                "dead_code",
                "unreachable_code",
                "invalid_assignment"
            ]
            
            if rule_name in important_warnings:
                return "medium"
            
            return "low"
        
        else:
            return "low"  # Info and hints are low priority
    
    def categorize_errors(self, issues: List[AnalysisIssue]) -> Dict[str, List[AnalysisIssue]]:
        """Categorize issues by type and severity for better handling"""
        categories = {
            "critical_errors": [],
            "compilation_errors": [],
            "import_errors": [],
            "type_errors": [],
            "syntax_errors": [],
            "warnings": [],
            "other": []
        }
        
        for issue in issues:
            if issue.type != AnalysisType.ERROR:
                categories["warnings"].append(issue)
                continue
            
            message_lower = issue.message.lower()
            
            if any(pattern in message_lower for pattern in ["isn't defined", "undefined"]):
                categories["critical_errors"].append(issue)
            elif any(pattern in message_lower for pattern in ["import", "library"]):
                categories["import_errors"].append(issue)
            elif any(pattern in message_lower for pattern in ["type", "assigned", "expected"]):
                categories["type_errors"].append(issue)
            elif any(pattern in message_lower for pattern in ["syntax", "expected ';'", "expected ')'"]):
                categories["syntax_errors"].append(issue)
            elif "can't" in message_lower or "cannot" in message_lower:
                categories["compilation_errors"].append(issue)
            else:
                categories["other"].append(issue)
        
        return categories
    
    def format_error_summary(self, issues: List[AnalysisIssue]) -> str:
        """Create a human-readable summary of errors"""
        if not issues:
            return "No issues found ✅"
        
        categories = self.categorize_errors(issues)
        
        summary_parts = []
        
        for category, items in categories.items():
            if items:
                count = len(items)
                category_name = category.replace("_", " ").title()
                summary_parts.append(f"• {category_name}: {count}")
        
        total_errors = len([i for i in issues if i.type == AnalysisType.ERROR])
        total_warnings = len([i for i in issues if i.type == AnalysisType.WARNING])
        
        header = f"Analysis Summary: {total_errors} errors, {total_warnings} warnings"
        
        if summary_parts:
            return f"{header}\n" + "\n".join(summary_parts)
        else:
            return header
    
    def run_flutter_pub_get(self) -> Tuple[bool, str]:
        """Run flutter pub get to ensure dependencies are up to date"""
        try:
            print("Running flutter pub get...")
            result = subprocess.run(
                ["flutter", "pub", "get"],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout for pub get
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "flutter pub get timed out after 2 minutes"
        except Exception as e:
            return False, f"Failed to run flutter pub get: {str(e)}"
    
    def run_dart_fix(self, file_path: Optional[str] = None) -> Tuple[bool, str]:
        """Run dart fix --apply to automatically fix some issues"""
        try:
            command = ["dart", "fix", "--apply"]
            if file_path:
                command.append(str(self.project_path / file_path))
            else:
                command.append(str(self.lib_path))
            
            print(f"Running: {' '.join(command)}")
            result = subprocess.run(
                command,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            success = result.returncode == 0
            output = result.stdout + result.stderr
            
            return success, output
            
        except subprocess.TimeoutExpired:
            return False, "dart fix timed out after 60 seconds"
        except Exception as e:
            return False, f"Failed to run dart fix: {str(e)}"