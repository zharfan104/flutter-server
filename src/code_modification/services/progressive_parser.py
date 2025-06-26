"""
Progressive Parser for Code Modification System

Reusable class that handles batch file processing with progressive parsing.
Extracts and applies file modifications as they're found in AI responses.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path

from .json_utils import extract_partial_file_operations, extract_shell_commands_from_response


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


@dataclass
class ParseResult:
    """Result of progressive parsing and application"""
    success: bool
    modifications: List[FileModification]
    shell_commands: List[str]
    files_applied: int
    errors: List[str]
    duration: float


class ProgressiveParser:
    """
    Reusable progressive parser that can extract and apply file modifications
    from AI responses, handling truncated JSON and applying files immediately.
    """
    
    def __init__(self, project_path: str):
        """
        Initialize the progressive parser
        
        Args:
            project_path: Path to the project root directory
        """
        self.project_path = Path(project_path)
        
        # Validate project path
        if not self.project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
    
    async def parse_and_apply_batch(
        self, 
        response_text: str,
        current_contents: Dict[str, str],
        context_description: str = "batch processing"
    ) -> ParseResult:
        """
        Main entry point: Parse AI response and apply file modifications progressively
        
        Args:
            response_text: AI response containing file modifications
            current_contents: Current content of files (path -> content mapping)
            context_description: Description for logging/debugging
            
        Returns:
            ParseResult with applied modifications and any errors
        """
        start_time = time.time()
        modifications = []
        shell_commands = []
        errors = []
        
        print(f"[ProgressiveParser] Starting progressive parsing for {context_description}")
        print(f"[ProgressiveParser] Response length: {len(response_text)} characters")
        
        try:
            # Extract file operations using enhanced JSON parsing
            file_operations = extract_partial_file_operations(response_text, context_description)
            
            # Extract shell commands
            extracted_commands = extract_shell_commands_from_response(response_text, context_description)
            shell_commands.extend(extracted_commands)
            
            print(f"[ProgressiveParser] Found {len(file_operations)} file operations and {len(extracted_commands)} shell commands")
            
            if not file_operations:
                print(f"[ProgressiveParser] No file operations found in response")
                return ParseResult(
                    success=True,
                    modifications=modifications,
                    shell_commands=shell_commands,
                    files_applied=0,
                    errors=["No file operations found in AI response"],
                    duration=time.time() - start_time
                )
            
            # Process each file operation immediately
            for i, file_op in enumerate(file_operations):
                try:
                    print(f"[ProgressiveParser] Processing file operation {i+1}/{len(file_operations)}")
                    
                    modification = await self._process_file_operation(
                        file_op, current_contents, context_description
                    )
                    
                    if modification:
                        # Apply the modification immediately
                        success = await self._apply_file_modification(modification)
                        
                        if success:
                            modifications.append(modification)
                            # Update current_contents to reflect the change
                            current_contents[modification.file_path] = modification.modified_content
                            
                            if modification.is_new_file:
                                print(f"[ProgressiveParser] ✅ Created new file: {modification.file_path}")
                            else:
                                print(f"[ProgressiveParser] ✅ Modified file: {modification.file_path}")
                        else:
                            error_msg = f"Failed to apply modification to {modification.file_path}"
                            errors.append(error_msg)
                            print(f"[ProgressiveParser] ❌ {error_msg}")
                    else:
                        print(f"[ProgressiveParser] Skipped file operation {i+1}: invalid or incomplete")
                        
                except Exception as e:
                    error_msg = f"Error processing file operation {i+1}: {str(e)}"
                    errors.append(error_msg)
                    print(f"[ProgressiveParser] ❌ {error_msg}")
                    continue
            
            duration = time.time() - start_time
            success = len(modifications) > 0 or len(shell_commands) > 0
            
            print(f"[ProgressiveParser] Progressive parsing completed in {duration:.1f}s:")
            print(f"  - Files applied: {len(modifications)}")
            print(f"  - Shell commands: {len(shell_commands)}")
            print(f"  - Errors: {len(errors)}")
            
            return ParseResult(
                success=success,
                modifications=modifications,
                shell_commands=shell_commands,
                files_applied=len(modifications),
                errors=errors,
                duration=duration
            )
            
        except Exception as e:
            error_msg = f"Progressive parsing failed: {str(e)}"
            errors.append(error_msg)
            print(f"[ProgressiveParser] ❌ {error_msg}")
            
            return ParseResult(
                success=False,
                modifications=modifications,
                shell_commands=shell_commands,
                files_applied=len(modifications),
                errors=errors,
                duration=time.time() - start_time
            )
    
    async def _process_file_operation(
        self, 
        file_op: Dict[str, Any], 
        current_contents: Dict[str, str],
        context: str
    ) -> Optional[FileModification]:
        """
        Process a single file operation and create a FileModification
        
        Args:
            file_op: File operation dictionary from AI response
            current_contents: Current file contents mapping
            context: Context description for logging
            
        Returns:
            FileModification object or None if invalid
        """
        try:
            operation = file_op.get('operation', 'modify')
            file_path = file_op.get('path', '')
            content = file_op.get('content', '')
            
            if not file_path or not content:
                print(f"[ProgressiveParser] Skipping incomplete file operation: missing path or content")
                return None
            
            # Skip delete operations for now (handle separately if needed)
            if operation == 'delete':
                print(f"[ProgressiveParser] Skipping delete operation: {file_path}")
                return None
            
            # Clean up the content
            cleaned_content = self._clean_file_content(content)
            
            # Handle NO_CHANGES_NEEDED for individual files
            if cleaned_content.strip() == "NO_CHANGES_NEEDED":
                print(f"[ProgressiveParser] Skipping {file_path}: NO_CHANGES_NEEDED")
                return None
            
            original_content = current_contents.get(file_path, "")
            is_new_file = not (self.project_path / file_path).exists() or original_content == ""
            
            # Validate content completeness for Dart files
            validation_passed = self._validate_file_content(file_path, cleaned_content)
            
            if not validation_passed:
                print(f"[ProgressiveParser] Validation failed for {file_path}")
                return None
            
            # Only process if content is different or it's a new file
            if cleaned_content != original_content or is_new_file:
                return FileModification(
                    file_path=file_path,
                    original_content=original_content,
                    modified_content=cleaned_content,
                    change_description=f"{operation.capitalize()}d via progressive parsing: {context}",
                    operation=operation,
                    is_new_file=is_new_file,
                    validation_passed=validation_passed
                )
            else:
                print(f"[ProgressiveParser] Skipping {file_path}: content unchanged")
                return None
                
        except Exception as e:
            print(f"[ProgressiveParser] Error processing file operation: {e}")
            return None
    
    async def _apply_file_modification(self, modification: FileModification) -> bool:
        """
        Apply a file modification to the filesystem
        
        Args:
            modification: The file modification to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.project_path / modification.file_path
            
            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(modification.modified_content)
            
            print(f"[ProgressiveParser] Applied {modification.operation} to {modification.file_path} ({len(modification.modified_content)} chars)")
            return True
            
        except Exception as e:
            print(f"[ProgressiveParser] Failed to apply modification to {modification.file_path}: {e}")
            return False
    
    def _clean_file_content(self, content: str) -> str:
        """
        Clean up file content from AI response
        
        Args:
            content: Raw content from AI
            
        Returns:
            Cleaned content ready for writing to file
        """
        # Remove common markdown artifacts
        cleaned = content.strip()
        
        # Remove markdown code block markers
        if cleaned.startswith('```dart'):
            cleaned = cleaned[7:].strip()
        elif cleaned.startswith('```'):
            cleaned = cleaned[3:].strip()
        
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3].strip()
        
        # Remove any leading/trailing whitespace but preserve internal formatting
        return cleaned
    
    def _validate_file_content(self, file_path: str, content: str) -> bool:
        """
        Validate file content for completeness and syntax
        
        Args:
            file_path: Path to the file being validated
            content: File content to validate
            
        Returns:
            True if content appears valid, False otherwise
        """
        if not content or not content.strip():
            return False
        
        # For Dart files, do basic validation
        if file_path.endswith('.dart'):
            # Check for balanced braces (basic syntax check)
            brace_count = content.count('{') - content.count('}')
            if brace_count != 0:
                print(f"[ProgressiveParser] Validation failed for {file_path}: unbalanced braces ({brace_count})")
                return False
            
            # Check for basic Dart structure (should have some meaningful content)
            has_meaningful_content = any(keyword in content for keyword in [
                'class ', 'void ', 'String ', 'int ', 'double ', 'bool ', 'var ', 'final ', 'const ',
                'import ', 'library ', 'part ', 'export ', 'enum ', 'mixin ', 'extension '
            ])
            
            if not has_meaningful_content:
                print(f"[ProgressiveParser] Validation failed for {file_path}: no meaningful Dart content detected")
                return False
        
        return True