"""
Simple Dart Analysis Fixer

A straightforward class that loops dart analyze until all errors are fixed.
Uses a 2-step AI process with queue-based file processing.
"""

import time
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path

from .progressive_parser import ProgressiveParser


@dataclass
class FileQueueItem:
    """Represents a file that needs to be processed"""
    path: str
    operation: str  # 'create', 'modify', 'delete'
    reason: str
    priority: int = 1
    completed: bool = False


class FileQueue:
    """Manages the queue of files to be processed"""
    
    def __init__(self):
        self.items: List[FileQueueItem] = []
    
    def add_file(self, path: str, operation: str, reason: str, priority: int = 1):
        """Add a file to the processing queue"""
        item = FileQueueItem(
            path=path,
            operation=operation,
            reason=reason,
            priority=priority,
            completed=False
        )
        self.items.append(item)
    
    def get_next(self) -> Optional[FileQueueItem]:
        """Get the next uncompleted file from the queue"""
        for item in self.items:
            if not item.completed:
                return item
        return None
    
    def mark_completed(self, item: FileQueueItem):
        """Mark a file as processed"""
        item.completed = True
    
    def is_empty(self) -> bool:
        """Check if all files in the queue are processed"""
        return all(item.completed for item in self.items)
    
    def get_pending_count(self) -> int:
        """Get the number of pending files"""
        return sum(1 for item in self.items if not item.completed)
    
    def clear(self):
        """Clear all items from the queue"""
        self.items.clear()


@dataclass
class AnalysisError:
    """Represents a single error from dart analyze"""
    file_path: str
    line: int
    column: int
    message: str
    error_type: str = "error"  # error, warning, info, hint


@dataclass
class AnalysisResult:
    """Result of running dart analyze"""
    success: bool
    errors: List[AnalysisError]
    warnings: List[AnalysisError]
    output: str
    execution_time: float


@dataclass
class FixResult:
    """Result of the fixing process"""
    success: bool
    initial_error_count: int
    final_error_count: int
    attempts_made: int
    files_processed: List[str]
    total_duration: float
    error_message: Optional[str] = None


class SimpleDartAnalysisFixer:
    """
    Simple Dart analysis fixer that uses a 2-step AI process with queue-based file processing.
    
    Process:
    1. Run dart analyze to get errors
    2. AI Step 1: Plan which files to modify/create/delete (creates queue)
    3. Process ALL files in queue until empty
    4. Run dart analyze again
    5. Repeat until no errors
    """
    
    def __init__(self, project_path: str, max_attempts: int = 5):
        """
        Initialize the SimpleDartAnalysisFixer
        
        Args:
            project_path: Path to the Flutter/Dart project
            max_attempts: Maximum number of fixing attempts before giving up
        """
        self.project_path = Path(project_path)
        self.max_attempts = max_attempts
        self.current_attempt = 0
        self.file_queue = FileQueue()
        self.memory_entries: List[str] = []  # AI-generated memory of previous attempts
        self.session_id = f"dart_fix_{int(time.time())}"
        
        # Initialize progressive parser for batch file processing
        self.progressive_parser = ProgressiveParser(str(project_path))
        
        # Validate project path
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        
        # Check if it's a Dart/Flutter project
        pubspec_path = self.project_path / "pubspec.yaml"
        if not pubspec_path.exists():
            raise ValueError(f"Not a valid Dart/Flutter project (no pubspec.yaml): {project_path}")
    
    def __repr__(self) -> str:
        return f"SimpleDartAnalysisFixer(project_path={self.project_path}, max_attempts={self.max_attempts})"
    
    def _run_dart_analysis(self, target_path: Optional[str] = None) -> AnalysisResult:
        """
        Run dart analyze on the project and parse the results
        
        Args:
            target_path: Specific path to analyze, defaults to lib directory
            
        Returns:
            AnalysisResult with parsed errors and warnings
        """
        start_time = time.time()
        
        # Default to lib directory if no target specified
        if target_path is None:
            target_path = "lib"
        
        # Ensure target path exists
        full_target_path = self.project_path / target_path
        if not full_target_path.exists():
            return AnalysisResult(
                success=False,
                errors=[AnalysisError(
                    file_path=target_path,
                    line=0,
                    column=0,
                    message=f"Target path does not exist: {target_path}",
                    error_type="error"
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
            errors, warnings = self._parse_dart_analysis_output(full_output)
            
            # Success if no errors (warnings are OK)
            success = len(errors) == 0 and result.returncode == 0
            
            return AnalysisResult(
                success=success,
                errors=errors,
                warnings=warnings,
                output=full_output,
                execution_time=execution_time
            )
            
        except subprocess.TimeoutExpired:
            return AnalysisResult(
                success=False,
                errors=[AnalysisError(
                    file_path=target_path,
                    line=0,
                    column=0,
                    message="dart analyze timed out after 60 seconds",
                    error_type="error"
                )],
                warnings=[],
                output="Timeout: dart analyze took too long",
                execution_time=60.0
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AnalysisResult(
                success=False,
                errors=[AnalysisError(
                    file_path=target_path,
                    line=0,
                    column=0,
                    message=f"Failed to run dart analyze: {str(e)}",
                    error_type="error"
                )],
                warnings=[],
                output=f"Error: {str(e)}",
                execution_time=execution_time
            )
    
    def _parse_dart_analysis_output(self, output: str) -> tuple[List[AnalysisError], List[AnalysisError]]:
        """
        Parse dart analyze output into structured errors and warnings
        
        Expected format examples:
        error • The method 'foo' isn't defined for the type 'Bar' • lib/main.dart:25:5 • undefined_method
        warning • Unused import • lib/main.dart:3:8 • unused_import
        
        Args:
            output: Raw output from dart analyze
            
        Returns:
            Tuple of (errors, warnings)
        """
        import re
        
        errors = []
        warnings = []
        
        for line in output.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Match the dart analyze output format
            # Pattern: type • message • file:line:column • rule_name
            match = re.match(r'(error|warning|info|hint)\s*•\s*(.+?)\s*•\s*(.+?):(\d+):(\d+)\s*•\s*(.+)', line)
            
            if match:
                error_type, message, file_path, line_num, column, rule_name = match.groups()
                
                analysis_error = AnalysisError(
                    file_path=file_path,
                    line=int(line_num),
                    column=int(column),
                    message=message.strip(),
                    error_type=error_type.lower()
                )
                
                if error_type.lower() == "error":
                    errors.append(analysis_error)
                elif error_type.lower() in ["warning", "info", "hint"]:
                    warnings.append(analysis_error)
            
            # Also check for simpler formats without rule names
            elif re.match(r'(error|warning|info|hint)', line, re.IGNORECASE):
                # Fallback parsing for different output formats
                parts = line.split(' - ', 1)
                if len(parts) >= 2:
                    error_type_str = parts[0].split()[0].lower()
                    
                    analysis_error = AnalysisError(
                        file_path="unknown",
                        line=0,
                        column=0,
                        message=parts[1].strip(),
                        error_type=error_type_str
                    )
                    
                    if error_type_str == "error":
                        errors.append(analysis_error)
                    elif error_type_str in ["warning", "info", "hint"]:
                        warnings.append(analysis_error)
        
        return errors, warnings
    
    def _collect_error_context(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        Collect code context for errors so AI can see the actual problematic code
        
        Args:
            analysis_result: Result from dart analyze with errors
            
        Returns:
            Dictionary containing file contents, error context, and project structure
        """
        context = {
            "files": {},
            "error_context": {},
            "project_structure": {
                "imports": set(),
                "classes": set(),
                "methods": set(),
                "dependencies": []
            }
        }
        
        # Collect all files mentioned in errors
        error_files = set()
        for error in analysis_result.errors + analysis_result.warnings:
            if error.file_path != "unknown" and not error.file_path.startswith("/"):
                error_files.add(error.file_path)
        
        # Read content of error files
        for file_path in error_files:
            full_path = self.project_path / file_path
            if full_path.exists() and full_path.suffix == ".dart":
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        context["files"][file_path] = content
                        
                        # Extract basic structure information
                        self._extract_dart_structure(content, context["project_structure"])
                        
                except Exception as e:
                    print(f"Warning: Could not read {file_path}: {e}")
        
        # Collect error-specific context (lines around errors)
        for error in analysis_result.errors:
            if error.file_path in context["files"] and error.line > 0:
                file_content = context["files"][error.file_path]
                error_context = self._get_error_line_context(file_content, error.line, error.column)
                
                error_key = f"{error.file_path}:{error.line}:{error.column}"
                context["error_context"][error_key] = {
                    "error": error,
                    "line_content": error_context["target_line"],
                    "surrounding_lines": error_context["surrounding_lines"],
                    "function_context": error_context["function_context"]
                }
        
        # Read pubspec.yaml for dependencies
        pubspec_path = self.project_path / "pubspec.yaml"
        if pubspec_path.exists():
            try:
                with open(pubspec_path, 'r', encoding='utf-8') as f:
                    pubspec_content = f.read()
                    context["project_structure"]["dependencies"] = self._extract_dependencies(pubspec_content)
            except Exception as e:
                print(f"Warning: Could not read pubspec.yaml: {e}")
        
        # Convert sets to lists for JSON serialization
        context["project_structure"]["imports"] = list(context["project_structure"]["imports"])
        context["project_structure"]["classes"] = list(context["project_structure"]["classes"])
        context["project_structure"]["methods"] = list(context["project_structure"]["methods"])
        
        return context
    
    def _extract_dart_structure(self, content: str, structure: Dict[str, set]):
        """
        Extract basic Dart structure information from file content
        
        Args:
            content: Dart file content
            structure: Dictionary to update with found imports, classes, methods
        """
        import re
        
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract imports
            if line.startswith('import '):
                match = re.match(r"import\s+['\"]([^'\"]+)['\"]", line)
                if match:
                    structure["imports"].add(match.group(1))
            
            # Extract class definitions
            class_match = re.match(r'class\s+(\w+)', line)
            if class_match:
                structure["classes"].add(class_match.group(1))
            
            # Extract method/function definitions
            method_match = re.match(r'\s*(\w+\s+)?(\w+)\s*\([^)]*\)\s*{?', line)
            if method_match and not line.startswith('//'):
                method_name = method_match.group(2)
                # Filter out common non-method patterns
                if method_name not in ['if', 'for', 'while', 'switch', 'return', 'class', 'import']:
                    structure["methods"].add(method_name)
    
    def _get_error_line_context(self, content: str, line_num: int, column: int) -> Dict[str, Any]:
        """
        Get context around a specific error line
        
        Args:
            content: File content
            line_num: Line number (1-based)
            column: Column number (1-based)
            
        Returns:
            Dictionary with target line, surrounding lines, and function context
        """
        lines = content.split('\n')
        
        # Convert to 0-based index
        target_index = line_num - 1
        
        context = {
            "target_line": "",
            "surrounding_lines": [],
            "function_context": ""
        }
        
        if 0 <= target_index < len(lines):
            context["target_line"] = lines[target_index]
            
            # Get surrounding lines (5 lines before and after)
            start = max(0, target_index - 5)
            end = min(len(lines), target_index + 6)
            
            for i in range(start, end):
                line_marker = ">>> " if i == target_index else "    "
                context["surrounding_lines"].append(f"{line_marker}{i + 1:3d}: {lines[i]}")
            
            # Try to find the containing function/method
            function_name = self._find_containing_function(lines, target_index)
            if function_name:
                context["function_context"] = f"Inside function/method: {function_name}"
        
        return context
    
    def _find_containing_function(self, lines: List[str], target_index: int) -> Optional[str]:
        """
        Find the function/method that contains the target line
        
        Args:
            lines: List of file lines
            target_index: Target line index (0-based)
            
        Returns:
            Function name if found, None otherwise
        """
        import re
        
        # Search backwards from target line to find function definition
        for i in range(target_index, -1, -1):
            line = lines[i].strip()
            
            # Look for function/method definition patterns
            patterns = [
                r'(\w+\s+)?(\w+)\s*\([^)]*\)\s*{',  # method(params) {
                r'(\w+\s+)?(\w+)\s*\([^)]*\)\s*=>',  # method(params) =>
                r'(\w+\s+)?(\w+)\s*\([^)]*\)\s*async\s*{',  # async method
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    return match.group(2)
        
        return None
    
    def _extract_dependencies(self, pubspec_content: str) -> List[str]:
        """
        Extract dependencies from pubspec.yaml content
        
        Args:
            pubspec_content: Content of pubspec.yaml
            
        Returns:
            List of dependency names
        """
        import re
        
        dependencies = []
        lines = pubspec_content.split('\n')
        in_dependencies = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if line == "dependencies:":
                in_dependencies = True
                continue
            elif line == "dev_dependencies:" or (line == "flutter:" and not original_line.startswith('  ')):
                # Only end dependencies for top-level sections, not indented flutter dependency
                in_dependencies = False
                continue
            
            if in_dependencies and line and not line.startswith('#'):
                # Check if this line has proper indentation (should be under dependencies)
                if original_line.startswith('  ') or original_line.startswith('\t'):
                    # Extract dependency name (before colon)
                    match = re.match(r'(\w+):', line)
                    if match:
                        dep_name = match.group(1)
                        # Skip nested properties like "sdk"
                        if not original_line.startswith('    ') and not original_line.startswith('\t\t'):
                            dependencies.append(dep_name)
                else:
                    # No indentation means we're out of dependencies section
                    in_dependencies = False
        
        return dependencies
    
    async def fix_until_clean(self) -> FixResult:
        """
        Main entry point: Fix dart errors until clean using 2-step AI process with queue
        
        Returns:
            FixResult with complete fixing session details
        """
        start_time = time.time()
        files_processed = []
        
        print(f"[SimpleDartAnalysisFixer] Starting error fixing session: {self.session_id}")
        
        for attempt in range(1, self.max_attempts + 1):
            self.current_attempt = attempt
            print(f"\n[SimpleDartAnalysisFixer] === Attempt {attempt}/{self.max_attempts} ===")
            
            # Step 1: Run dart analysis
            print(f"[SimpleDartAnalysisFixer] Running dart analyze...")
            analysis_result = self._run_dart_analysis()
            
            if not analysis_result.success and not analysis_result.errors:
                # Analysis failed completely
                return FixResult(
                    success=False,
                    initial_error_count=0,
                    final_error_count=0,
                    attempts_made=attempt,
                    files_processed=files_processed,
                    total_duration=time.time() - start_time,
                    error_message="Dart analysis failed"
                )
            
            initial_error_count = len(analysis_result.errors) if attempt == 1 else None
            current_error_count = len(analysis_result.errors)
            
            print(f"[SimpleDartAnalysisFixer] Found {current_error_count} errors")
            
            if current_error_count == 0:
                # Success! No more errors
                final_duration = time.time() - start_time
                print(f"[SimpleDartAnalysisFixer] ✅ All errors fixed! Session completed in {final_duration:.1f}s")
                
                return FixResult(
                    success=True,
                    initial_error_count=initial_error_count or 0,
                    final_error_count=0,
                    attempts_made=attempt,
                    files_processed=files_processed,
                    total_duration=final_duration
                )
            
            # Step 2: Collect error context
            print(f"[SimpleDartAnalysisFixer] Collecting error context...")
            error_context = self._collect_error_context(analysis_result)
            
            # Step 3: AI Step 1 - Plan which files to modify
            print(f"[SimpleDartAnalysisFixer] AI planning file modifications...")
            self.file_queue.clear()  # Clear previous queue
            
            success = await self._plan_files_with_ai(analysis_result, error_context)
            if not success:
                print(f"[SimpleDartAnalysisFixer] ❌ AI file planning failed")
                continue
            
            print(f"[SimpleDartAnalysisFixer] Planned {self.file_queue.get_pending_count()} files for modification")
            
            # Step 4: Process ALL files in queue with batch generation
            print(f"[SimpleDartAnalysisFixer] Processing file queue with batch generation...")
            queue_files = await self._process_file_queue_batch()
            files_processed.extend(queue_files)
            
            print(f"[SimpleDartAnalysisFixer] Processed {len(queue_files)} files")
            
            # Continue to next iteration to check if errors are fixed
        
        # Max attempts reached
        final_analysis = self._run_dart_analysis()
        final_error_count = len(final_analysis.errors) if final_analysis.success else current_error_count
        
        return FixResult(
            success=False,
            initial_error_count=initial_error_count or 0,
            final_error_count=final_error_count,
            attempts_made=self.max_attempts,
            files_processed=files_processed,
            total_duration=time.time() - start_time,
            error_message=f"Max attempts ({self.max_attempts}) reached"
        )
    
    async def _plan_files_with_ai(self, analysis_result: AnalysisResult, error_context: Dict[str, Any]) -> bool:
        """
        AI Step 1: Plan which files to modify/create/delete (creates queue)
        
        Args:
            analysis_result: Current dart analysis result
            error_context: Rich context about errors and code
            
        Returns:
            True if planning succeeded, False otherwise
        """
        try:
            # Import LLM executor
            from .llm_executor import SimpleLLMExecutor
            
            llm_executor = SimpleLLMExecutor()
            if not llm_executor.is_available():
                print(f"[SimpleDartAnalysisFixer] ❌ LLM not available for file planning")
                return False
            
            # Prepare prompt context
            context = {
                "project_path": str(self.project_path),
                "current_attempt": self.current_attempt,
                "max_attempts": self.max_attempts,
                "error_count": len(analysis_result.errors),
                "errors": [
                    {
                        "file": error.file_path,
                        "line": error.line,
                        "message": error.message,
                        "type": error.error_type
                    }
                    for error in analysis_result.errors[:10]  # Limit to top 10 errors
                ],
                "project_structure": error_context["project_structure"],
                "previous_attempts": self._get_memory_summary()
            }
            
            # Create file planning prompt
            prompt = f"""You are a Dart/Flutter expert. Analyze these compilation errors and determine which files need to be modified, created, or deleted to fix them.

Project: {context['project_path']}
Attempt: {context['current_attempt']}/{context['max_attempts']}
Errors: {context['error_count']}

ERRORS TO FIX:
{self._format_errors_for_prompt(analysis_result.errors)}

PROJECT STRUCTURE:
- Dependencies: {', '.join(context['project_structure']['dependencies'])}
- Classes: {', '.join(context['project_structure']['classes'][:10])}
- Imports: {', '.join(list(context['project_structure']['imports'])[:10])}

PREVIOUS ATTEMPTS:
{context['previous_attempts']}

TASK: Create a JSON plan for fixing these errors. Focus on the root causes.

OUTPUT FORMAT:
{{
    "analysis": "Brief analysis of what's causing the errors",
    "files_to_modify": [
        {{
            "path": "lib/main.dart",
            "reason": "Fix undefined method error",
            "operation": "modify"
        }}
    ],
    "files_to_create": [
        {{
            "path": "lib/services/new_service.dart", 
            "reason": "Create missing service class",
            "operation": "create"
        }}
    ],
    "files_to_delete": [],
    "shell_commands": ["flutter pub get", "dart format ."]
}}

Respond with ONLY the JSON, no other text."""
            
            messages = [{"role": "user", "content": prompt}]
            response = llm_executor.execute(messages)
            
            if not response or not response.text:
                print(f"[SimpleDartAnalysisFixer] ❌ Empty response from LLM")
                return False
            
            # Parse the response
            plan_data = self._parse_json_response(response.text)
            if not plan_data:
                print(f"[SimpleDartAnalysisFixer] ❌ Failed to parse LLM response as JSON")
                return False
            
            # Add files to queue
            files_to_modify = plan_data.get("files_to_modify", [])
            files_to_create = plan_data.get("files_to_create", [])
            
            for file_info in files_to_modify:
                self.file_queue.add_file(
                    path=file_info["path"],
                    operation="modify",
                    reason=file_info["reason"]
                )
            
            for file_info in files_to_create:
                self.file_queue.add_file(
                    path=file_info["path"],
                    operation="create", 
                    reason=file_info["reason"]
                )
            
            print(f"[SimpleDartAnalysisFixer] ✅ AI planned {len(files_to_modify)} modifications + {len(files_to_create)} creations")
            return True
            
        except Exception as e:
            print(f"[SimpleDartAnalysisFixer] ❌ File planning failed: {e}")
            return False
    
    async def _process_file_queue_batch(self) -> List[str]:
        """
        Process ALL files in queue using batch AI generation with progressive parsing
        
        Returns:
            List of files that were processed
        """
        if self.file_queue.is_empty():
            return []
        
        # Collect all pending files for batch processing
        pending_files = []
        while not self.file_queue.is_empty():
            file_item = self.file_queue.get_next()
            if file_item:
                pending_files.append(file_item)
                self.file_queue.mark_completed(file_item)  # Mark as processed
        
        if not pending_files:
            return []
        
        print(f"[SimpleDartAnalysisFixer] Generating {len(pending_files)} files in batch")
        
        # Generate all files in a single AI call
        success = await self._generate_and_apply_batch(pending_files)
        
        if success:
            processed_files = [item.path for item in pending_files]
            print(f"[SimpleDartAnalysisFixer] ✅ Batch generation completed for {len(processed_files)} files")
            return processed_files
        else:
            print(f"[SimpleDartAnalysisFixer] ❌ Batch generation failed")
            return []
    
    async def _generate_and_apply_batch(self, pending_files: List[FileQueueItem]) -> bool:
        """
        AI Step 2: Generate multiple files in a single AI call using progressive parsing
        
        Args:
            pending_files: List of files to process in batch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import LLM executor
            from .llm_executor import SimpleLLMExecutor
            
            llm_executor = SimpleLLMExecutor()
            if not llm_executor.is_available():
                print(f"[SimpleDartAnalysisFixer] ❌ LLM not available for batch file generation")
                return False
            
            # Collect current file contents
            current_contents = {}
            for file_item in pending_files:
                file_path = self.project_path / file_item.path
                if file_path.exists():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            current_contents[file_item.path] = f.read()
                    except Exception as e:
                        print(f"[SimpleDartAnalysisFixer] Warning: Could not read {file_item.path}: {e}")
                        current_contents[file_item.path] = ""
                else:
                    current_contents[file_item.path] = ""
            
            # Create batch generation prompt
            prompt = self._create_batch_prompt(pending_files, current_contents)
            
            messages = [{"role": "user", "content": prompt}]
            response = llm_executor.execute(messages)
            
            if not response or not response.text:
                print(f"[SimpleDartAnalysisFixer] ❌ Empty response from LLM for batch generation")
                return False
            
            # Use progressive parser to extract and apply files
            parse_result = await self.progressive_parser.parse_and_apply_batch(
                response.text,
                current_contents,
                f"dart_fixer_batch_attempt_{self.current_attempt}"
            )
            
            if parse_result.success and parse_result.files_applied > 0:
                print(f"[SimpleDartAnalysisFixer] ✅ Batch generation: {parse_result.files_applied} files applied")
                
                # Add memory entry for next attempt
                self.add_memory_entry(
                    f"Attempt {self.current_attempt}: Successfully generated {parse_result.files_applied} files "
                    f"({', '.join([mod.file_path for mod in parse_result.modifications])})"
                )
                
                return True
            else:
                print(f"[SimpleDartAnalysisFixer] ❌ Batch generation failed: {parse_result.errors}")
                
                # Add memory entry about failure
                self.add_memory_entry(
                    f"Attempt {self.current_attempt}: Batch generation failed - {', '.join(parse_result.errors[:3])}"
                )
                
                return False
            
        except Exception as e:
            print(f"[SimpleDartAnalysisFixer] ❌ Batch file generation failed: {e}")
            return False
    
    def _create_batch_prompt(self, pending_files: List[FileQueueItem], current_contents: Dict[str, str]) -> str:
        """
        Create a prompt for batch file generation using the progressive parsing format
        
        Args:
            pending_files: List of files to generate
            current_contents: Current content of existing files
            
        Returns:
            Formatted prompt for the AI
        """
        files_info = []
        
        for file_item in pending_files:
            current_content = current_contents.get(file_item.path, "")
            
            if file_item.operation == "create":
                files_info.append(f"""
- FILE: {file_item.path} (CREATE)
  REASON: {file_item.reason}
  CURRENT: [New file - no existing content]""")
            else:  # modify
                content_preview = current_content[:200] + "..." if len(current_content) > 200 else current_content
                files_info.append(f"""
- FILE: {file_item.path} (MODIFY)
  REASON: {file_item.reason}
  CURRENT: {content_preview}""")
        
        files_list = "\n".join(files_info)
        
        return f"""You are a Dart/Flutter expert. Generate complete file contents for multiple files to fix compilation errors.

PROJECT: {self.project_path}
ATTEMPT: {self.current_attempt}/{self.max_attempts}
FILES TO PROCESS: {len(pending_files)}

FILES DETAILS:
{files_list}

PREVIOUS ATTEMPTS MEMORY:
{self._get_memory_summary()}

TASK: Generate complete, corrected file contents for ALL the files listed above.

OUTPUT FORMAT (IMPORTANT):
Provide a JSON response with file_operations array. Each file operation must have:
- "operation": "create" or "modify"
- "path": the file path
- "content": the complete file content

Example format:
{{
    "file_operations": [
        {{
            "operation": "modify",
            "path": "lib/main.dart",
            "content": "import 'package:flutter/material.dart';\\n\\nvoid main() {{\\n  runApp(MyApp());\\n}}\\n\\nclass MyApp extends StatelessWidget {{\\n  @override\\n  Widget build(BuildContext context) {{\\n    return MaterialApp(home: Scaffold());\\n  }}\\n}}"
        }},
        {{
            "operation": "create", 
            "path": "lib/services/new_service.dart",
            "content": "class NewService {{\\n  // Service implementation\\n}}"
        }}
    ],
    "shell_commands": ["flutter pub get", "dart format ."]
}}

REQUIREMENTS:
- Generate complete, syntactically correct Dart code
- Fix all compilation errors mentioned in the reasons
- Proper null safety and Flutter conventions
- Ensure all imports are correct
- Follow existing code patterns where possible
- Include shell commands if packages need to be added

Respond with ONLY the JSON, no other text."""
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from LLM response with fallback strategies"""
        import json
        import re
        
        # Strategy 1: Direct JSON parsing
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
        
        # Strategy 3: Find largest JSON-like object
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
        
        print(f"[SimpleDartAnalysisFixer] ❌ Could not parse JSON from response: {response_text[:200]}...")
        return None
    
    def _get_memory_summary(self) -> str:
        """Get a summary of previous attempts for AI context"""
        if not self.memory_entries:
            return "No previous attempts in this session."
        
        # Return last few memory entries
        recent_entries = self.memory_entries[-3:]
        return "\n".join(f"- {entry}" for entry in recent_entries)
    
    def _format_errors_for_prompt(self, errors: List[AnalysisError], limit: int = 10) -> str:
        """Format errors for AI prompt"""
        if not errors:
            return "No errors found."
        
        formatted_errors = []
        for i, error in enumerate(errors[:limit]):
            formatted_errors.append(f"{i+1}. {error.file_path}:{error.line} - {error.message}")
        
        if len(errors) > limit:
            formatted_errors.append(f"... and {len(errors) - limit} more errors")
        
        return "\n".join(formatted_errors)
    
    def add_memory_entry(self, entry: str):
        """Add a memory entry for AI context"""
        self.memory_entries.append(entry)
        # Keep only last 10 entries to avoid token limit
        if len(self.memory_entries) > 10:
            self.memory_entries = self.memory_entries[-10:]