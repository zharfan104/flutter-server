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

from .llm_executor import SimpleLLMExecutor, LLMResponse
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
    
    async def modify_code(self, request: ModificationRequest) -> ModificationResult:
        """
        Execute a code modification request
        
        Args:
            request: The modification request
            
        Returns:
            ModificationResult with success status and details
        """
        start_time = time.time()
        
        # Enhanced logging
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.CODE_MOD, f"Starting code modification: {request.description[:100]}...", 
                       context={
                           "request_id": request.request_id,
                           "user_id": request.user_id,
                           "description": request.description,
                           "target_files": request.target_files,
                           "files_to_create": request.files_to_create,
                           "files_to_delete": request.files_to_delete
                       })
        
        print(f"Processing modification request: {request.description}")
        
        try:
            # Load project structure
            structure = self._load_project_structure()
            
            # Determine which files need modification
            if request.target_files:
                directly_modified_files = set(request.target_files)
                all_relevant_files = set(request.target_files)
                files_to_create = request.files_to_create or []
                files_to_delete = request.files_to_delete or []
            else:
                directly_modified_files, all_relevant_files, files_to_create, files_to_delete = await self._determine_relevant_files(request, structure)
                
            if not directly_modified_files and not files_to_create and not files_to_delete:
                error_msg = "No files identified for modification"
                
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.CODE_MOD, error_msg)
                
                return ModificationResult(
                    success=False,
                    modified_files=[],
                    created_files=[],
                    deleted_files=[],
                    errors=[error_msg],
                    warnings=[],
                    changes_summary="No changes made",
                    request_id=request.request_id
                )
            
            print(f"Target files for modification: {directly_modified_files}")
            print(f"Files to create: {files_to_create}")
            print(f"Files to delete: {files_to_delete}")
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CODE_MOD, f"Identified {len(directly_modified_files)} files for modification", 
                           context={
                               "directly_modified_files": list(directly_modified_files), 
                               "files_to_create": files_to_create,
                               "files_to_delete": files_to_delete,
                               "request_id": request.request_id
                           })
            
            # Get current file contents for all relevant files
            all_files_list = list(all_relevant_files) + files_to_create
            current_contents = self._get_file_contents(all_files_list)
            
            # Generate modified content
            modifications, deletions, shell_commands = await self._generate_modifications(
                request, structure, directly_modified_files, files_to_create, files_to_delete, current_contents
            )
            
            # Apply modifications
            result = await self._apply_modifications(modifications, deletions, shell_commands, request.request_id)
            
            # Enhanced success logging
            duration = time.time() - start_time
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CODE_MOD, f"Code modification completed: {result.changes_summary}", 
                           context={
                               "request_id": request.request_id,
                               "duration_seconds": round(duration, 2),
                               "modified_files": result.modified_files,
                               "created_files": result.created_files,
                               "deleted_files": result.deleted_files,
                               "changes_summary": result.changes_summary
                           })
            
            print(f"✅ Code modification completed: {result.changes_summary}")
            return result
                
        except Exception as e:
            error_message = str(e)
            
            print(f"Error during code modification: {error_message}")
            
            duration = time.time() - start_time
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CODE_MOD, f"Code modification failed: {error_message}",
                           context={
                               "request_id": request.request_id,
                               "duration_seconds": round(duration, 2),
                               "error_message": error_message,
                               "description": request.description[:100]
                           })
            
            return ModificationResult(
                success=False,
                modified_files=[],
                created_files=[],
                deleted_files=[],
                errors=[f"Modification failed: {error_message}"],
                warnings=[],
                changes_summary="No changes made due to error",
                request_id=request.request_id
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
            
            prompt = self.prompt_loader.format_prompt(
                'generate_code',
                project_summary=json.dumps(project_summary, indent=2),
                change_request=request.description,
                current_contents=contents_text,
                target_files=json.dumps(list(remaining_files)),
                files_to_create=json.dumps([f for f in files_to_create if f in remaining_files]),
                files_to_delete=json.dumps(files_to_delete)
            )
            
            # Add images to content if provided
            content = [{"type": "text", "text": prompt}]
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
            
            try:
                response = self.llm_executor.execute(messages=messages)
                
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
    
    def get_modification_history(self) -> List[Dict]:
        """
        Get history of modifications (placeholder for future implementation)
        
        Returns:
            List of modification records
        """
        # This would typically read from a database or log file
        return []
    
    def preview_modifications(self, request: ModificationRequest) -> Dict:
        """
        Preview what modifications would be made without applying them
        
        Args:
            request: The modification request
            
        Returns:
            Dictionary with preview information
        """
        # This would run the modification process but not apply changes
        # Useful for showing users what would change before confirming
        return {
            "target_files": [],
            "estimated_changes": "Preview not yet implemented",
            "warnings": []
        }