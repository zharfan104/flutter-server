"""
Code Modification Service
Orchestrates multi-file code modifications using LLM analysis
"""

import os
import json
import asyncio
import time
import re
from typing import Dict, List, Set, Optional, Tuple, Union, Any
from dataclasses import dataclass
from pathlib import Path
import subprocess

from .llm_executor import SimpleLLMExecutor, LLMResponse, StreamProgress
from .project_analyzer import FlutterProjectAnalyzer, ProjectStructure
from .prompt_loader import prompt_loader

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel, OperationTracker
    from utils.request_tracer import tracer, EventContext, TraceEventType
    from utils.performance_monitor import performance_monitor, TimingContext
    from utils.error_analyzer import error_analyzer, analyze_error
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
class ModificationRequest:
    """Represents a code modification request"""
    description: str
    target_files: Optional[List[str]] = None
    files_to_create: Optional[List[str]] = None
    files_to_delete: Optional[List[str]] = None
    context: Optional[Dict] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    max_retries: int = 20
    images: Optional[List[Dict[str, str]]] = None
    existing_changes: Optional[Set[str]] = None


@dataclass
class ModificationResult:
    """Represents the result of a code modification"""
    success: bool
    modified_files: List[str]
    created_files: List[str]
    deleted_files: List[str]
    errors: List[str]
    warnings: List[str]
    changes_summary: str
    request_id: Optional[str] = None


@dataclass
class FileModification:
    """Represents a modification to a single file"""
    file_path: str
    original_content: str
    modified_content: str
    change_description: str
    operation: str = "modify"  # "create", "modify", "delete"
    is_new_file: bool = False
    validation_passed: bool = True


class CodeModificationService:
    """
    Main service for handling intelligent code modifications
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.llm_executor = SimpleLLMExecutor()
        self.project_analyzer = FlutterProjectAnalyzer(str(self.project_path))
        self.project_structure = None
        
        # Initialize prompt loader
        self.prompt_loader = prompt_loader
        
        # Verify prompts are loaded
        available_prompts = self.prompt_loader.list_available_prompts()
        print(f"Available prompts: {available_prompts}")
        
        if 'determine_files' not in available_prompts:
            raise Exception("Required prompt 'determine_files' not found")
        if 'generate_code' not in available_prompts:
            raise Exception("Required prompt 'generate_code' not found")
    
    def _load_project_structure(self):
        """Load and cache project structure"""
        if self.project_structure is None:
            self.project_structure = self.project_analyzer.analyze()
        return self.project_structure
    
    
    async def modify_code_stream(self, request: ModificationRequest):
        """
        Execute a code modification request with streaming progress updates
        
        Args:
            request: The modification request
            
        Yields:
            StreamProgress objects and status updates during the modification process
        """
        from .llm_executor import StreamProgress
        
        start_time = time.time()
        
        try:
            # Initial progress
            yield StreamProgress(
                stage="analyzing",
                message="Starting code modification...",
                progress_percent=0.0,
                metadata={"request_id": request.request_id}
            )
            
            # Load project structure
            yield StreamProgress(
                stage="analyzing", 
                message="Analyzing project structure...",
                progress_percent=10.0
            )
            
            structure = self._load_project_structure()
            
            # Determine which files need modification
            yield StreamProgress(
                stage="analyzing",
                message="Determining files to modify...",
                progress_percent=20.0
            )
            
            if request.target_files:
                directly_modified_files = set(request.target_files)
                all_relevant_files = set(request.target_files)
                files_to_create = request.files_to_create or []
                files_to_delete = request.files_to_delete or []
            else:
                # Stream the file determination process
                async for progress in self._determine_relevant_files_stream(request, structure):
                    yield progress
                
                directly_modified_files, all_relevant_files, files_to_create, files_to_delete = await self._determine_relevant_files(request, structure)
            
            yield StreamProgress(
                stage="generating",
                message=f"Generating code for {len(directly_modified_files)} files...",
                progress_percent=40.0,
                metadata={
                    "files_to_modify": len(directly_modified_files),
                    "files_to_create": len(files_to_create),
                    "files_to_delete": len(files_to_delete)
                }
            )
            
            if not directly_modified_files and not files_to_create and not files_to_delete:
                yield StreamProgress(
                    stage="error",
                    message="No files identified for modification",
                    progress_percent=0.0
                )
                return
            
            # Load current file contents
            yield StreamProgress(
                stage="analyzing",
                message="Loading current file contents...",
                progress_percent=30.0
            )
            
            current_contents = {}
            for file_path in all_relevant_files:
                full_path = self.project_path / file_path
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            current_contents[file_path] = f.read()
                    except Exception as e:
                        yield StreamProgress(
                            stage="warning",
                            message=f"Failed to read {file_path}: {str(e)}",
                            progress_percent=30.0
                        )
            
            # Generate code modifications using the existing method
            yield StreamProgress(
                stage="generating",
                message="AI is generating code modifications...",
                progress_percent=40.0,
                metadata={
                    "files_to_modify": list(directly_modified_files),
                    "files_to_create": files_to_create,
                    "files_to_delete": files_to_delete
                }
            )
            
            # Stream the LLM generation process
            streaming_content = {}
            accumulated_response = ""
            current_file = None
            current_content = ""
            
            # Get prompts for LLM
            project_summary = self.project_analyzer.generate_project_summary()
            all_target_files = list(directly_modified_files) + files_to_create
            
            contents_text = "\n\n".join([
                f"=== {file_path} ===\n{content}"
                for file_path, content in current_contents.items()
                if file_path in all_target_files or file_path in current_contents
            ])
            
            try:
                system_prompt, user_prompt = self.prompt_loader.get_system_user_prompts(
                    'generate_code',
                    project_summary=json.dumps(project_summary, indent=2),
                    change_request=request.description,
                    current_contents=contents_text,
                    target_files=json.dumps(all_target_files),
                    files_to_create=json.dumps(files_to_create),
                    files_to_delete=json.dumps(files_to_delete)
                )
            except KeyError:
                user_prompt = self.prompt_loader.format_prompt(
                    'generate_code',
                    project_summary=json.dumps(project_summary, indent=2),
                    change_request=request.description,
                    current_contents=contents_text,
                    target_files=json.dumps(all_target_files),
                    files_to_create=json.dumps(files_to_create),
                    files_to_delete=json.dumps(files_to_delete)
                )
                system_prompt = None
            
            # Prepare messages
            content = [{"type": "text", "text": user_prompt}]
            if request.images:
                for image in request.images:
                    content.extend([
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image["media_type"],
                                "data": image["data"]
                            }
                        },
                        {"type": "text", "text": "Use this image as a reference."}
                    ])
            
            messages = [{"role": "user", "content": content}]
            
            # Stream the response
            async for chunk in self.llm_executor.execute_stream_with_progress(
                messages=messages,
                system_prompt=system_prompt
            ):
                if isinstance(chunk, str):
                    # Text chunk from LLM
                    accumulated_response += chunk
                    
                    # Detect file boundaries
                    if "=== " in chunk and " ===" in chunk:
                        # New file started
                        if current_file:
                            streaming_content[current_file] = current_content
                            yield StreamProgress(
                                stage="generating",
                                message=f"Completed {current_file}",
                                progress_percent=48.0,
                                partial_content=current_content,
                                metadata={"current_file": current_file, "file_complete": True}
                            )
                        
                        # Extract new file name
                        file_match = re.search(r'=== (.*?) ===', accumulated_response)
                        if file_match:
                            current_file = file_match.group(1).strip()
                            current_content = ""
                            yield StreamProgress(
                                stage="generating",
                                message=f"Generating {current_file}...",
                                progress_percent=45.0,
                                metadata={"current_file": current_file, "file_start": True}
                            )
                    else:
                        # Add to current file content
                        current_content += chunk
                        
                        # Yield streaming update
                        yield StreamProgress(
                            stage="generating",
                            message=f"Writing code for {current_file or 'analysis'}...",
                            progress_percent=46.0,
                            partial_content=current_content,
                            metadata={
                                "current_file": current_file,
                                "chunk": chunk,
                                "streaming": True
                            }
                        )
                
                elif hasattr(chunk, 'stage'):
                    # StreamProgress from LLM executor
                    yield chunk
            
            # Complete last file if any
            if current_file and current_content:
                streaming_content[current_file] = current_content
                yield StreamProgress(
                    stage="generating", 
                    message=f"Completed {current_file}",
                    progress_percent=50.0,
                    partial_content=current_content,
                    metadata={"current_file": current_file, "file_complete": True}
                )
            
            # Parse the complete response
            modifications, deletions, shell_commands = self._parse_modification_response(
                accumulated_response, current_contents, request, set(all_target_files)
            )
            
            yield StreamProgress(
                stage="generating",
                message=f"Generated modifications for {len(modifications)} files",
                progress_percent=60.0
            )
            
            # Validation phase
            yield StreamProgress(
                stage="validating",
                message="Validating generated code...",
                progress_percent=70.0
            )
            
            # Apply modifications with progress updates
            yield StreamProgress(
                stage="applying",
                message="Applying code changes...",
                progress_percent=80.0
            )
            
            modified_files = []
            created_files = []
            errors = []
            
            for modification in modifications:
                try:
                    yield StreamProgress(
                        stage="applying",
                        message=f"Writing {modification.file_path}...",
                        progress_percent=80.0 + (len(modified_files + created_files) / len(modifications)) * 15.0,
                        metadata={"current_file": modification.file_path}
                    )
                    
                    await self._apply_modification(modification)
                    
                    if modification.is_new_file:
                        created_files.append(modification.file_path)
                    else:
                        modified_files.append(modification.file_path)
                        
                except Exception as e:
                    errors.append(f"Failed to apply {modification.file_path}: {str(e)}")
            
            # Handle file deletions
            deleted_files = []
            for file_path in deletions:
                try:
                    yield StreamProgress(
                        stage="applying",
                        message=f"Deleting {file_path}...",
                        progress_percent=95.0,
                        metadata={"current_file": file_path}
                    )
                    
                    full_path = self.project_path / file_path
                    if full_path.exists():
                        full_path.unlink()
                        deleted_files.append(file_path)
                        
                except Exception as e:
                    errors.append(f"Failed to delete {file_path}: {str(e)}")
            
            # Execute shell commands
            if shell_commands:
                yield StreamProgress(
                    stage="applying",
                    message="Executing shell commands...",
                    progress_percent=96.0
                )
                
                for cmd in shell_commands:
                    try:
                        yield StreamProgress(
                            stage="applying",
                            message=f"Running: {cmd}",
                            progress_percent=97.0,
                            metadata={"command": cmd}
                        )
                        
                        # Execute command
                        import subprocess
                        result = subprocess.run(
                            cmd,
                            shell=True,
                            cwd=str(self.project_path),
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode != 0:
                            errors.append(f"Command failed: {cmd} - {result.stderr}")
                            
                    except Exception as e:
                        errors.append(f"Failed to execute command {cmd}: {str(e)}")
            
            # Final completion
            success = len(errors) == 0
            yield StreamProgress(
                stage="complete" if success else "error",
                message="Code modification completed!" if success else f"Completed with {len(errors)} errors",
                progress_percent=100.0,
                metadata={
                    "success": success,
                    "modified_files": modified_files,
                    "created_files": created_files,
                    "deleted_files": deleted_files,
                    "commands_executed": shell_commands,
                    "errors": errors,
                    "duration": time.time() - start_time
                }
            )
            
            # Send final result as structured event
            yield {
                "event_type": "result",
                "success": success,
                "modified_files": modified_files,
                "created_files": created_files,
                "deleted_files": deleted_files,
                "commands_executed": shell_commands,
                "errors": errors,
                "request_id": request.request_id
            }
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"Code modification failed: {str(e)}",
                progress_percent=0.0,
                metadata={"error": str(e)}
            )
    
    async def _determine_relevant_files_stream(self, request: ModificationRequest, structure: ProjectStructure):
        """Stream progress updates for file determination"""
        from .llm_executor import StreamProgress
        
        yield StreamProgress(
            stage="analyzing",
            message="Asking AI to determine relevant files...",
            progress_percent=25.0
        )
        
        # This could be enhanced to show LLM streaming during file determination
        yield StreamProgress(
            stage="analyzing", 
            message="AI is analyzing project structure...",
            progress_percent=30.0
        )
    
    
    async def _determine_relevant_files(
        self, 
        request: ModificationRequest, 
        structure: ProjectStructure
    ) -> Tuple[Set[str], Set[str], List[str], List[str]]:
        """
        Use LLM to determine which files need modification, creation, or deletion
        
        Args:
            request: The modification request
            structure: Project structure
            
        Returns:
            Tuple of (directly_modified_files, all_relevant_files, files_to_create, files_to_delete)
        """
        if not self.llm_executor.is_available():
            # Fallback to simple analysis
            suggested_files = self.project_analyzer.suggest_files_for_modification(request.description)
            return set(suggested_files), set(suggested_files), [], []
        
        try:
            project_summary = self.project_analyzer.generate_project_summary()
            
            prompt = self.prompt_loader.format_prompt(
                'determine_files',
                project_summary=json.dumps(project_summary, indent=2),
                change_request=request.description
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            response = self.llm_executor.execute(messages=messages)
            
            # Parse the JSON response using robust extraction
            from .json_utils import extract_file_operations_from_response
            result = extract_file_operations_from_response(response.text, "file operations analysis")
            
            # The extraction function returns validated data, so we can trust the format
            directly_modified = set(result.get("directly_modified_files", []))
            all_relevant = set(result.get("all_relevant_files", []))
            to_create = result.get("files_to_create", [])
            to_delete = result.get("files_to_delete", [])
            
            # Always add lib/app.dart if it exists
            app_dart_path = "lib/app.dart"
            if (self.project_path / app_dart_path).exists():
                directly_modified.add(app_dart_path)
                all_relevant.add(app_dart_path)
            
            # Always include pubspec.yaml
            pubspec_path = "pubspec.yaml"
            if (self.project_path / pubspec_path).exists():
                all_relevant.add(pubspec_path)
            
            # Filter out files that are in existing_changes if provided
            if request.existing_changes:
                directly_modified = {f for f in directly_modified 
                                   if not any(f in ec or ec in f for ec in request.existing_changes)}
                all_relevant = {f for f in all_relevant 
                              if not any(f in ec or ec in f for ec in request.existing_changes)}
                to_create = [f for f in to_create 
                           if not any(f in ec or ec in f for ec in request.existing_changes)]
            
            return directly_modified, all_relevant, to_create, to_delete
                
        except Exception as e:
            print(f"Error determining relevant files: {e}")
            # Fallback to simple analysis
            suggested_files = self.project_analyzer.suggest_files_for_modification(request.description)
            return set(suggested_files), set(suggested_files), [], []
    
    def _get_file_contents(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Get current contents of specified files
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary mapping file paths to their contents
        """
        contents = {}
        
        for file_path in file_paths:
            full_path = self.project_path / file_path
            try:
                if full_path.exists():
                    with open(full_path, 'r', encoding='utf-8') as f:
                        contents[file_path] = f.read()
                else:
                    contents[file_path] = ""  # New file
            except Exception as e:
                print(f"Error reading file {file_path}: {e}")
                contents[file_path] = ""
        
        return contents
    
    async def _generate_modifications(
        self,
        request: ModificationRequest,
        structure: ProjectStructure,
        directly_modified_files: Set[str],
        files_to_create: List[str],
        files_to_delete: List[str],
        current_contents: Dict[str, str]
    ) -> Tuple[List[FileModification], List[str], List[str]]:
        """
        Generate modified content for target files with retry logic
        
        Args:
            request: The modification request
            structure: Project structure
            directly_modified_files: Set of files to modify
            files_to_create: List of files to create
            files_to_delete: List of files to delete
            current_contents: Current file contents
            
        Returns:
            Tuple of (modifications, deletions, shell_commands)
        """
        if not self.llm_executor.is_available():
            raise Exception("LLM executor not available for code generation")
        
        project_summary = self.project_analyzer.generate_project_summary()
        
        modifications = []
        deletions = files_to_delete.copy()
        shell_commands = []
        
        # Combine files to work with
        all_target_files = list(directly_modified_files) + files_to_create
        remaining_files = set(all_target_files)
        
        max_retries = request.max_retries
        attempt = 0
        
        while remaining_files and attempt < max_retries:
            attempt += 1
            print(f"\nGeneration attempt {attempt}/{max_retries}")
            print(f"Remaining files: {len(remaining_files)}")
            
            # Format current contents for the prompt
            contents_text = "\n\n".join([
                f"=== {file_path} ===\n{content}"
                for file_path, content in current_contents.items()
                if file_path in remaining_files or file_path in current_contents
            ])
            
            # Get system and user prompts separately (v2.0 structure)
            try:
                system_prompt, user_prompt = self.prompt_loader.get_system_user_prompts(
                    'generate_code',
                    project_summary=json.dumps(project_summary, indent=2),
                    change_request=request.description,
                    current_contents=contents_text,
                    target_files=json.dumps(list(remaining_files)),
                    files_to_create=json.dumps([f for f in files_to_create if f in remaining_files]),
                    files_to_delete=json.dumps(files_to_delete)
                )
                use_system_prompt = True
            except KeyError:
                # Fallback to legacy format if system/user prompts not available
                user_prompt = self.prompt_loader.format_prompt(
                    'generate_code',
                    project_summary=json.dumps(project_summary, indent=2),
                    change_request=request.description,
                    current_contents=contents_text,
                    target_files=json.dumps(list(remaining_files)),
                    files_to_create=json.dumps([f for f in files_to_create if f in remaining_files]),
                    files_to_delete=json.dumps(files_to_delete)
                )
                system_prompt = ""
                use_system_prompt = False
            
            # Add images to content if provided
            content = [{"type": "text", "text": user_prompt}]
            if request.images:
                for image in request.images:
                    content.extend([
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image["media_type"],
                                "data": image["data"]
                            }
                        },
                        {"type": "text", "text": "Use this image as a reference."}
                    ])
            
            # Construct messages with proper system/user structure
            if use_system_prompt and system_prompt:
                messages = [{"role": "user", "content": content}]
                system_prompt_for_llm = system_prompt
            else:
                messages = [{"role": "user", "content": content}]
                system_prompt_for_llm = None
            
            try:
                response = self.llm_executor.execute(
                    messages=messages,
                    system_prompt=system_prompt_for_llm,
                    user_id=request.user_id,
                    session_id=request.request_id
                )
                
                # Parse the response to extract file modifications
                batch_modifications, batch_deletions, batch_commands = self._parse_modification_response(
                    response.text, current_contents, request, remaining_files
                )
                
                # Add successful modifications
                modifications.extend(batch_modifications)
                deletions.extend(batch_deletions)
                shell_commands.extend(batch_commands)
                
                # Remove successfully processed files
                processed_files = {mod.file_path for mod in batch_modifications}
                remaining_files -= processed_files
                
                print(f"Successfully processed {len(processed_files)} files")
                
                if not remaining_files:
                    break
                    
            except Exception as e:
                print(f"Error in attempt {attempt}: {str(e)}")
                if attempt >= max_retries:
                    print("Max retries reached, proceeding with partial results")
                    break
                    
        return modifications, deletions, shell_commands
    
    def _parse_modification_response(
        self, 
        response_text: str, 
        current_contents: Dict[str, str],
        request: ModificationRequest,
        target_files: Set[str] = None
    ) -> Tuple[List[FileModification], List[str], List[str]]:
        """
        Parse LLM response to extract file modifications, deletions, and shell commands
        Supports both new JSON format (v2.0) and legacy XML-style format
        
        Args:
            response_text: The LLM response
            current_contents: Current file contents
            request: The modification request
            target_files: Set of files we're expecting to process
            
        Returns:
            Tuple of (modifications, deletions, shell_commands)
        """
        modifications = []
        deletions = []
        shell_commands = []
        
        # Handle NO_CHANGES_NEEDED response
        if response_text.strip() == "NO_CHANGES_NEEDED":
            return modifications, deletions, shell_commands
        
        # Try to parse as JSON first (v2.0 format)
        try:
            json_response = self._parse_json_response(response_text)
            if json_response:
                return self._parse_json_format(json_response, current_contents, request, target_files)
        except Exception as e:
            print(f"JSON parsing failed, falling back to legacy format: {e}")
        
        # Fall back to legacy XML-style parsing
        return self._parse_legacy_format(response_text, current_contents, request, target_files)
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Extract JSON from response text, handling markdown code blocks"""
        import json
        
        # Try to find JSON in markdown code blocks first
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON directly in response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def _parse_json_format(
        self, 
        json_response: Dict, 
        current_contents: Dict[str, str],
        request: ModificationRequest,
        target_files: Set[str] = None
    ) -> Tuple[List[FileModification], List[str], List[str]]:
        """Parse the new JSON format response"""
        modifications = []
        deletions = []
        shell_commands = []
        
        # Extract shell commands
        if 'shell_commands' in json_response:
            shell_commands.extend(json_response['shell_commands'])
        
        # Extract file operations
        if 'file_operations' in json_response:
            for file_op in json_response['file_operations']:
                operation = file_op.get('operation', 'modify')
                file_path = file_op.get('path', '')
                content = file_op.get('content', '')
                
                if operation == 'delete':
                    deletions.append(file_path)
                    continue
                
                if not file_path or not content:
                    continue
                
                # Clean up the content
                cleaned_content = self._clean_file_content(content)
                
                # Handle NO_CHANGES_NEEDED for individual files
                if cleaned_content.strip() == "NO_CHANGES_NEEDED":
                    continue
                
                original_content = current_contents.get(file_path, "")
                is_new_file = not (self.project_path / file_path).exists() or original_content == ""
                
                # Validate content completeness for Dart files
                validation_passed = self._validate_file_content(file_path, cleaned_content)
                
                if cleaned_content != original_content or is_new_file:
                    modifications.append(FileModification(
                        file_path=file_path,
                        original_content=original_content,
                        modified_content=cleaned_content,
                        change_description=f"{operation.capitalize()}d based on request: {request.description[:50]}...",
                        operation=operation,
                        is_new_file=is_new_file,
                        validation_passed=validation_passed
                    ))
        
        return modifications, deletions, shell_commands
    
    def _parse_legacy_format(
        self, 
        response_text: str, 
        current_contents: Dict[str, str],
        request: ModificationRequest,
        target_files: Set[str] = None
    ) -> Tuple[List[FileModification], List[str], List[str]]:
        """Parse the legacy XML-style format"""
        modifications = []
        deletions = []
        shell_commands = []
        
        # Parse response looking for <files path="..."> blocks
        file_blocks = re.findall(
            r'<files path="([^"]+)">(.*?)</files>',
            response_text,
            re.DOTALL
        )
        
        # Parse response looking for <delete path="..."> blocks
        delete_blocks = re.findall(
            r'<delete path="([^"]+)">DELETE</delete>',
            response_text
        )
        
        # Parse response looking for <shell> blocks
        shell_blocks = re.findall(
            r'<shell>(.*?)</shell>',
            response_text,
            re.DOTALL
        )
        
        deletions.extend(delete_blocks)
        
        # Process shell commands
        for shell_block in shell_blocks:
            commands = [cmd.strip() for cmd in shell_block.strip().split('\n') if cmd.strip()]
            shell_commands.extend(commands)
        
        for file_path, content in file_blocks:
            # Clean up the content
            cleaned_content = self._clean_file_content(content)
            
            # Handle NO_CHANGES_NEEDED for individual files
            if cleaned_content.strip() == "NO_CHANGES_NEEDED":
                continue
            
            original_content = current_contents.get(file_path, "")
            is_new_file = not (self.project_path / file_path).exists() or original_content == ""
            
            # Determine operation type
            operation = "create" if is_new_file else "modify"
            
            # Validate content completeness for Dart files
            validation_passed = self._validate_file_content(file_path, cleaned_content)
            
            if cleaned_content != original_content or is_new_file:
                modifications.append(FileModification(
                    file_path=file_path,
                    original_content=original_content,
                    modified_content=cleaned_content,
                    change_description=f"{operation.capitalize()}d based on request: {request.description[:50]}...",
                    operation=operation,
                    is_new_file=is_new_file,
                    validation_passed=validation_passed
                ))
        
        # Add any explicitly requested deletions that weren't in LLM response
        if request.files_to_delete:
            for file_to_delete in request.files_to_delete:
                if file_to_delete not in deletions:
                    deletions.append(file_to_delete)
        
        return modifications, deletions, shell_commands
    
    
    
    def _parse_file_blocks(self, response_text: str) -> List[Tuple[str, str]]:
        """
        Parse file blocks from the LLM response
        Supports multiple formats:
        1. <file path="...">content</file>
        2. === path/to/file.dart ===\ncontent
        3. JSON format with file_operations
        """
        file_blocks = []
        
        # First try JSON format
        try:
            # Look for JSON in the response
            json_match = re.search(r'\{[\s\S]*"file_operations"[\s\S]*\}', response_text)
            if json_match:
                json_data = json.loads(json_match.group(0))
                if "file_operations" in json_data:
                    for file_op in json_data["file_operations"]:
                        if file_op.get("operation") in ["create", "modify"]:
                            file_blocks.append((file_op["path"], file_op.get("content", "")))
                    return file_blocks
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Try <file> tag format
        file_tag_pattern = r'<file(?:\s+path="([^"]+)")?\s*>(.*?)</file>'
        file_tag_matches = re.findall(file_tag_pattern, response_text, re.DOTALL)
        if file_tag_matches:
            for path, content in file_tag_matches:
                if path:
                    file_blocks.append((path, content))
            return file_blocks
        
        # Try === delimiter format
        delimiter_pattern = r'===\s*([^\s=]+)\s*===\n(.*?)(?=\n===|$)'
        delimiter_matches = re.findall(delimiter_pattern, response_text, re.DOTALL)
        if delimiter_matches:
            for path, content in delimiter_matches:
                file_blocks.append((path.strip(), content))
            return file_blocks
        
        # Try to find file path patterns with content blocks
        # Look for patterns like "lib/main.dart:" or "File: lib/main.dart"
        file_pattern = r'(?:File:\s*|^)([a-zA-Z0-9_/.-]+\.dart)(?:\s*:)?\s*\n((?:(?!File:|^[a-zA-Z0-9_/.-]+\.dart).)*)'
        file_matches = re.findall(file_pattern, response_text, re.MULTILINE | re.DOTALL)
        if file_matches:
            for path, content in file_matches:
                # Clean up the content
                content = content.strip()
                if content and not content.startswith("```"):
                    # If content doesn't start with code block, look for one
                    code_block_match = re.search(r'```(?:dart)?\n(.*?)```', content, re.DOTALL)
                    if code_block_match:
                        content = code_block_match.group(1)
                file_blocks.append((path, content))
        
        return file_blocks
    
    def _clean_file_content(self, content: str) -> str:
        """
        Clean the file content by removing markdown and continuation markers
        """
        content = content.strip()
        
        # Remove markdown code block markers
        if content.startswith('```'):
            lines = content.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        # Remove "continue with" lines from the last few lines
        lines = content.splitlines()
        if len(lines) >= 2:
            start_index = max(0, len(lines) - 5)
            for i in range(start_index, len(lines)):
                if "continue with" in lines[i].lower():
                    lines[i] = ""
        
        return '\n'.join(lines)
    
    def _validate_file_content(self, file_path: str, content: str) -> bool:
        """
        Validate file content for completeness and basic syntax
        """
        if not content.strip():
            return False
            
        # For Dart files, check if content ends properly
        if file_path.endswith('.dart'):
            content = content.strip()
            # Check if it ends with } or ;
            if not (content.endswith('}') or content.endswith(';')):
                return False
                
            # Check for balanced braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                return False
                
        return True
    
    async def _apply_modification(self, modification: FileModification) -> None:
        """Apply a single file modification"""
        file_path = self.project_path / modification.file_path
        
        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(modification.modified_content)
            
        if MONITORING_AVAILABLE:
            operation = "create" if modification.is_new_file else "modify"
            logger.info(LogCategory.FILE_OPS, f"{operation.capitalize()}d file: {modification.file_path}")
    
    async def _apply_modifications(
        self, 
        modifications: List[FileModification],
        deletions: List[str],
        shell_commands: List[str],
        request_id: Optional[str] = None
    ) -> ModificationResult:
        """
        Apply modifications to files
        
        Args:
            modifications: List of modifications to apply
            deletions: List of files to delete
            request_id: Optional request ID
            
        Returns:
            ModificationResult
        """
        modified_files = []
        created_files = []
        deleted_files = []
        errors = []
        warnings = []
        
        # Create backup of modified files
        backups = {}
        
        try:
            # Handle file deletions first
            for file_to_delete in deletions:
                file_path = self.project_path / file_to_delete
                
                if file_path.exists():
                    # Create backup before deletion
                    with open(file_path, 'r', encoding='utf-8') as f:
                        backups[file_to_delete] = f.read()
                    
                    # Delete the file
                    file_path.unlink()
                    deleted_files.append(file_to_delete)
                    print(f"Deleted file: {file_to_delete}")
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.FILE_OPS, f"Deleted file: {file_to_delete}",
                                   context={"operation": "delete", "file_path": file_to_delete, "request_id": request_id})
                else:
                    warnings.append(f"File to delete not found: {file_to_delete}")
            
            # Handle file modifications and creations
            for modification in modifications:
                file_path = self.project_path / modification.file_path
                
                # Determine if this is a new file or modification
                is_new_file = not file_path.exists() or modification.original_content == ""
                
                # Create backup if file exists
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        backups[modification.file_path] = f.read()
                
                # Create directory if it doesn't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modification.modified_content)
                
                if is_new_file:
                    created_files.append(modification.file_path)
                    print(f"Created file: {modification.file_path}")
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.FILE_OPS, f"Created file: {modification.file_path}",
                                   context={"operation": "create", "file_path": modification.file_path, "request_id": request_id})
                else:
                    modified_files.append(modification.file_path)
                    print(f"Modified file: {modification.file_path}")
                    
                    if MONITORING_AVAILABLE:
                        logger.info(LogCategory.FILE_OPS, f"Modified file: {modification.file_path}",
                                   context={"operation": "modify", "file_path": modification.file_path, "request_id": request_id})
            
            # Validate the modifications (basic syntax check)
            validation_errors = self._validate_modifications(modifications)
            if validation_errors:
                # Rollback changes
                await self._rollback_modifications(backups, deleted_files)
                return ModificationResult(
                    success=False,
                    modified_files=[],
                    created_files=[],
                    deleted_files=[],
                    errors=validation_errors,
                    warnings=warnings,
                    changes_summary="Modifications rolled back due to validation errors",
                    request_id=request_id
                )
            
            # Execute shell commands after file operations
            if shell_commands:
                print(f"Executing {len(shell_commands)} shell commands...")
                for cmd in shell_commands:
                    try:
                        result = subprocess.run(
                            cmd, 
                            shell=True, 
                            cwd=self.project_path, 
                            capture_output=True, 
                            text=True,
                            timeout=300  # 5 minute timeout
                        )
                        print(f"Command '{cmd}' executed successfully")
                        if MONITORING_AVAILABLE:
                            logger.info(LogCategory.FILE_OPS, f"Executed shell command: {cmd}",
                                       context={"command": cmd, "return_code": result.returncode, "request_id": request_id})
                    except subprocess.TimeoutExpired:
                        warnings.append(f"Shell command timed out: {cmd}")
                        print(f"Warning: Command '{cmd}' timed out")
                    except Exception as e:
                        warnings.append(f"Shell command failed: {cmd} - {str(e)}")
                        print(f"Warning: Command '{cmd}' failed: {str(e)}")
            
            # Create summary of changes
            summary_parts = []
            if modified_files:
                summary_parts.append(f"Modified {len(modified_files)} files")
            if created_files:
                summary_parts.append(f"Created {len(created_files)} files")
            if deleted_files:
                summary_parts.append(f"Deleted {len(deleted_files)} files")
            if shell_commands:
                summary_parts.append(f"Executed {len(shell_commands)} commands")
            
            changes_summary = "; ".join(summary_parts) if summary_parts else "No changes made"
            
            return ModificationResult(
                success=True,
                modified_files=modified_files,
                created_files=created_files,
                deleted_files=deleted_files,
                errors=errors,
                warnings=warnings,
                changes_summary=changes_summary,
                request_id=request_id
            )
            
        except Exception as e:
            # Rollback changes on error
            await self._rollback_modifications(backups, deleted_files)
            return ModificationResult(
                success=False,
                modified_files=[],
                created_files=[],
                deleted_files=[],
                errors=[f"Failed to apply modifications: {str(e)}"],
                warnings=warnings,
                changes_summary="Modifications rolled back due to error",
                request_id=request_id
            )
    
    def _validate_modifications(self, modifications: List[FileModification]) -> List[str]:
        """
        Validate modifications for basic syntax and structure
        
        Args:
            modifications: List of modifications to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        
        for modification in modifications:
            # Basic Dart syntax validation
            content = modification.modified_content
            
            # Check for balanced braces
            open_braces = content.count('{')
            close_braces = content.count('}')
            if open_braces != close_braces:
                errors.append(f"{modification.file_path}: Unbalanced braces ({open_braces} open, {close_braces} close)")
            
            # Check for balanced parentheses
            open_parens = content.count('(')
            close_parens = content.count(')')
            if open_parens != close_parens:
                errors.append(f"{modification.file_path}: Unbalanced parentheses ({open_parens} open, {close_parens} close)")
            
            # Check that Dart files have some basic structure
            if modification.file_path.endswith('.dart'):
                if not any(keyword in content for keyword in ['class ', 'void ', 'import ', 'main(']):
                    errors.append(f"{modification.file_path}: File doesn't appear to contain valid Dart code")
        
        return errors
    
    async def _rollback_modifications(self, backups: Dict[str, str], deleted_files: List[str]):
        """
        Rollback modifications using backups
        
        Args:
            backups: Dictionary of file paths to their backup content
            deleted_files: List of files that were deleted
        """
        for file_path, backup_content in backups.items():
            try:
                full_path = self.project_path / file_path
                
                # If this was a deleted file, restore it
                if file_path in deleted_files:
                    # Create directory if needed
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(backup_content)
                print(f"Rolled back: {file_path}")
            except Exception as e:
                print(f"Error rolling back {file_path}: {e}")
    
