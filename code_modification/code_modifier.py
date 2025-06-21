"""
Code Modification Service
Orchestrates multi-file code modifications using LLM analysis
"""

import os
import json
import asyncio
import time
from typing import Dict, List, Set, Optional, Tuple, Union
from dataclasses import dataclass
from pathlib import Path

from .llm_executor import SimpleLLMExecutor, LLMResponse
from .project_analyzer import FlutterProjectAnalyzer, ProjectStructure

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


class CodeModificationService:
    """
    Main service for handling intelligent code modifications
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.llm_executor = SimpleLLMExecutor()
        self.project_analyzer = FlutterProjectAnalyzer(str(self.project_path))
        self.project_structure = None
        
        # Prompt templates
        self.determine_files_prompt = """
You are a Flutter development expert. Given a change request, determine which files need to be modified.

Project Structure:
{project_summary}

Change Request: {change_request}

Analyze the request and return a JSON array of file paths that need to be modified. Consider:
1. Direct files mentioned or implied by the request
2. Files that depend on the modified files
3. Related files that might need updates for consistency

Return only a JSON array of file paths, no additional text:
["lib/file1.dart", "lib/file2.dart"]
        """
        
        self.generate_code_prompt = """
You are a Flutter development expert. Generate modified code for the specified files.

Project Structure:
{project_summary}

Change Request: {change_request}

Current File Contents:
{current_contents}

Files to Modify: {target_files}
Files to Create: {files_to_create}
Files to Delete: {files_to_delete}

For each file that needs modification or creation, generate the complete new content. Format your response as:

<files path="lib/example.dart">
// Complete new file content here
</files>

<files path="lib/another_file.dart">
// Complete new file content here  
</files>

For files to delete, respond with:
<delete path="lib/old_file.dart">DELETE</delete>

Important guidelines:
1. Maintain existing code style and patterns
2. Keep imports and dependencies consistent
3. Ensure code compiles and follows Flutter best practices
4. Only modify what's necessary for the requested change
5. Preserve existing functionality unless explicitly asked to change it
6. When creating new files, follow Flutter/Dart naming conventions
7. Ensure proper directory structure for new files
        """
    
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
                target_files = request.target_files
            else:
                target_files = await self._determine_relevant_files(request, structure)
                
            if not target_files and not request.files_to_create and not request.files_to_delete:
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
            
            print(f"Target files for modification: {target_files}")
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CODE_MOD, f"Identified {len(target_files)} files for modification", 
                           context={"target_files": target_files, "request_id": request.request_id})
            
            # Get current file contents
            all_files = target_files + (request.files_to_create or [])
            current_contents = self._get_file_contents(all_files)
            
            # Generate modified content
            modifications, deletions = await self._generate_modifications(
                request, structure, target_files, current_contents
            )
            
            # Apply modifications
            result = await self._apply_modifications(modifications, deletions, request.request_id)
            
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
    ) -> List[str]:
        """
        Use LLM to determine which files need modification
        
        Args:
            request: The modification request
            structure: Project structure
            
        Returns:
            List of file paths to modify
        """
        if not self.llm_executor.is_available():
            # Fallback to simple analysis
            return self.project_analyzer.suggest_files_for_modification(request.description)
        
        try:
            project_summary = self.project_analyzer.generate_project_summary()
            
            prompt = self.determine_files_prompt.format(
                project_summary=json.dumps(project_summary, indent=2),
                change_request=request.description
            )
            
            messages = [{"role": "user", "content": prompt}]
            
            response = self.llm_executor.execute(messages=messages)
            
            # Parse the JSON response
            try:
                files = json.loads(response.text.strip())
                if isinstance(files, list):
                    # Filter to only existing files
                    existing_files = []
                    for file_path in files:
                        full_path = self.project_path / file_path
                        if full_path.exists():
                            existing_files.append(file_path)
                        else:
                            print(f"Warning: File {file_path} does not exist")
                    
                    return existing_files
                else:
                    print(f"Invalid response format: {response.text}")
                    return []
            except json.JSONDecodeError as e:
                print(f"Failed to parse LLM response as JSON: {e}")
                print(f"Response was: {response.text}")
                return []
                
        except Exception as e:
            print(f"Error determining relevant files: {e}")
            # Fallback to simple analysis
            return self.project_analyzer.suggest_files_for_modification(request.description)
    
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
        target_files: List[str],
        current_contents: Dict[str, str]
    ) -> Tuple[List[FileModification], List[str]]:
        """
        Generate modified content for target files
        
        Args:
            request: The modification request
            structure: Project structure
            target_files: List of files to modify
            current_contents: Current file contents
            
        Returns:
            List of FileModification objects
        """
        if not self.llm_executor.is_available():
            raise Exception("LLM executor not available for code generation")
        
        project_summary = self.project_analyzer.generate_project_summary()
        
        # Format current contents for the prompt
        contents_text = "\n\n".join([
            f"=== {file_path} ===\n{content}"
            for file_path, content in current_contents.items()
        ])
        
        prompt = self.generate_code_prompt.format(
            project_summary=json.dumps(project_summary, indent=2),
            change_request=request.description,
            current_contents=contents_text,
            target_files=json.dumps(target_files),
            files_to_create=json.dumps(request.files_to_create or []),
            files_to_delete=json.dumps(request.files_to_delete or [])
        )
        
        messages = [{"role": "user", "content": prompt}]
        
        response = self.llm_executor.execute(messages=messages)
        
        # Parse the response to extract file modifications
        modifications, deletions = self._parse_modification_response(response.text, current_contents, request)
        
        return modifications, deletions
    
    def _parse_modification_response(
        self, 
        response_text: str, 
        current_contents: Dict[str, str],
        request: ModificationRequest
    ) -> Tuple[List[FileModification], List[str]]:
        """
        Parse LLM response to extract file modifications and deletions
        
        Args:
            response_text: The LLM response
            current_contents: Current file contents
            request: The modification request
            
        Returns:
            Tuple of (modifications, deletions)
        """
        modifications = []
        deletions = []
        
        # Parse response looking for <files path="..."> blocks
        import re
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
        
        deletions.extend(delete_blocks)
        
        for file_path, content in file_blocks:
            # Clean up the content
            cleaned_content = content.strip()
            
            # Remove any markdown code block markers
            if cleaned_content.startswith('```'):
                lines = cleaned_content.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                cleaned_content = '\n'.join(lines)
            
            original_content = current_contents.get(file_path, "")
            
            if cleaned_content != original_content:
                modifications.append(FileModification(
                    file_path=file_path,
                    original_content=original_content,
                    modified_content=cleaned_content,
                    change_description=f"Modified based on request"
                ))
        
        # Add any explicitly requested deletions that weren't in LLM response
        if request.files_to_delete:
            for file_to_delete in request.files_to_delete:
                if file_to_delete not in deletions:
                    deletions.append(file_to_delete)
        
        return modifications, deletions
    
    async def _apply_modifications(
        self, 
        modifications: List[FileModification],
        deletions: List[str],
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
            
            # Create summary of changes
            summary_parts = []
            if modified_files:
                summary_parts.append(f"Modified {len(modified_files)} files")
            if created_files:
                summary_parts.append(f"Created {len(created_files)} files")
            if deleted_files:
                summary_parts.append(f"Deleted {len(deleted_files)} files")
            
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