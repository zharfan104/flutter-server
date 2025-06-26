"""
JSON Utilities for Code Modification System
Handles extraction of JSON from LLM responses that may be wrapped in markdown
"""

import json
import re
from typing import Any, Dict, List, Optional, Tuple

# Import advanced logging
try:
    from src.utils.advanced_logger import logger, LogCategory
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


def extract_json_from_response(response: str, context: str = "LLM response") -> str:
    """
    Extract JSON content from LLM response that may be wrapped in markdown code blocks
    
    Args:
        response: Raw LLM response text
        context: Context description for logging
        
    Returns:
        Clean JSON string ready for parsing
        
    Raises:
        ValueError: If no valid JSON content is found
    """
    if not response or not response.strip():
        raise ValueError(f"Empty response in {context}")
    
    original_response = response
    response = response.strip()
    
    # Method 1: Try to extract from markdown code blocks
    # Look for ```json ... ``` or ``` ... ``` patterns
    json_patterns = [
        r'```json\s*\n(.*?)\n```',  # ```json ... ```
        r'```\s*\n(.*?)\n```',     # ``` ... ```
        r'```json(.*?)```',        # ```json...``` (no newlines)
        r'```(.*?)```',            # ```...``` (no newlines)
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        if matches:
            json_content = matches[0].strip()
            if json_content:
                if MONITORING_AVAILABLE:
                    logger.debug(LogCategory.CODE_MOD, f"Extracted JSON from markdown blocks in {context}")
                return json_content
    
    # Method 2: Look for JSON object patterns in the response
    # Find content between { and } that looks like JSON
    json_object_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_object_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            # Test if it's valid JSON
            json.loads(match)
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.CODE_MOD, f"Extracted JSON object pattern in {context}")
            return match
        except json.JSONDecodeError:
            continue
    
    # Method 3: Try to find JSON array patterns
    json_array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    matches = re.findall(json_array_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            # Test if it's valid JSON
            json.loads(match)
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.CODE_MOD, f"Extracted JSON array pattern in {context}")
            return match
        except json.JSONDecodeError:
            continue
    
    # Method 4: Check if the entire response is already valid JSON
    try:
        json.loads(response)
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.CODE_MOD, f"Response is already valid JSON in {context}")
        return response
    except json.JSONDecodeError:
        pass
    
    # If all methods fail, raise an error with detailed information
    if MONITORING_AVAILABLE:
        logger.warn(LogCategory.CODE_MOD, f"Failed to extract JSON from {context}. Response: {original_response[:200]}...")
    
    raise ValueError(f"Could not extract valid JSON from {context}. Response may not contain properly formatted JSON.")


def safe_json_loads(response: str, context: str = "response", default: Optional[Any] = None) -> Any:
    """
    Safely parse JSON from LLM response with automatic extraction and error handling
    
    Args:
        response: Raw LLM response text
        context: Context description for logging
        default: Default value to return if parsing fails
        
    Returns:
        Parsed JSON object or default value
    """
    try:
        json_content = extract_json_from_response(response, context)
        parsed_data = json.loads(json_content)
        
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.CODE_MOD, f"Successfully parsed JSON from {context}")
        
        return parsed_data
        
    except (ValueError, json.JSONDecodeError) as e:
        if MONITORING_AVAILABLE:
            logger.warn(LogCategory.CODE_MOD, f"JSON parsing failed for {context}: {str(e)}")
        
        if default is not None:
            return default
        else:
            raise


def validate_file_operation_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate that a parsed JSON response contains expected file operation fields
    
    Args:
        data: Parsed JSON data
        
    Returns:
        Validated data with defaults for missing fields
    """
    # Ensure all required fields exist with default values
    validated_data = {
        "directly_modified_files": data.get("directly_modified_files", []),
        "files_to_create": data.get("files_to_create", []),
        "files_to_delete": data.get("files_to_delete", []),
        "all_relevant_files": data.get("all_relevant_files", [])
    }
    
    # Ensure all fields are lists
    for field in validated_data:
        if not isinstance(validated_data[field], list):
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.CODE_MOD, f"Field '{field}' is not a list, converting to list")
            validated_data[field] = [validated_data[field]] if validated_data[field] else []
    
    # If all_relevant_files is empty, populate it from other fields
    if not validated_data["all_relevant_files"]:
        all_files = set()
        all_files.update(validated_data["directly_modified_files"])
        all_files.update(validated_data["files_to_create"])
        validated_data["all_relevant_files"] = list(all_files)
    
    return validated_data


def extract_partial_file_operations(response: str, context: str = "partial extraction") -> List[Dict[str, Any]]:
    """
    Extract individual file operations from potentially truncated JSON response using brace-balanced parsing
    
    Args:
        response: Raw LLM response text (may be truncated)
        context: Context description for logging
        
    Returns:
        List of complete file operation dictionaries found in response
    """
    file_operations = []
    
    if MONITORING_AVAILABLE:
        logger.debug(LogCategory.CODE_MOD, f"Starting brace-balanced file operations extraction from {context}")
    
    # Method 1: Try to find complete file_operations array using brace balancing
    file_ops_start = response.find('"file_operations"')
    if file_ops_start != -1:
        # Look for the opening bracket of the array
        array_start = response.find('[', file_ops_start)
        if array_start != -1:
            extracted_from_array = _extract_from_file_operations_array(response[array_start:])
            file_operations.extend(extracted_from_array)
            if MONITORING_AVAILABLE and extracted_from_array:
                logger.debug(LogCategory.CODE_MOD, f"Extracted {len(extracted_from_array)} operations from file_operations array")
    
    # Method 2: Extract individual JSON objects with brace balancing
    individual_objects = _extract_individual_json_objects(response)
    for obj_str in individual_objects:
        try:
            file_op = json.loads(obj_str)
            # Check if this looks like a file operation
            if (isinstance(file_op, dict) and 
                all(key in file_op for key in ['operation', 'path', 'content'])):
                
                # Clean up the file operation
                cleaned_file_op = _clean_file_operation(file_op)
                if (cleaned_file_op and 
                    not any(op.get('path') == cleaned_file_op.get('path') for op in file_operations)):
                    
                    file_operations.append(cleaned_file_op)
                    if MONITORING_AVAILABLE:
                        logger.debug(LogCategory.CODE_MOD, f"Extracted individual file operation: {cleaned_file_op['path']}")
        except json.JSONDecodeError:
            continue
    
    if MONITORING_AVAILABLE:
        logger.info(LogCategory.CODE_MOD, f"Total extracted file operations: {len(file_operations)}")
    
    return file_operations


def _extract_from_file_operations_array(text: str) -> List[Dict[str, Any]]:
    """
    Extract file operations from a file_operations array using brace balancing
    
    Args:
        text: Text starting with '[' for the file_operations array
        
    Returns:
        List of parsed file operation dictionaries
    """
    file_operations = []
    if not text.startswith('['):
        return file_operations
    
    i = 1  # Skip opening bracket
    brace_count = 0
    current_object = ""
    in_string = False
    escape_next = False
    
    while i < len(text):
        char = text[i]
        
        if escape_next:
            current_object += char
            escape_next = False
        elif char == '\\' and in_string:
            current_object += char
            escape_next = True
        elif char == '"' and not escape_next:
            current_object += char
            in_string = not in_string
        elif not in_string:
            if char == '{':
                if brace_count == 0:
                    current_object = char  # Start new object
                else:
                    current_object += char
                brace_count += 1
            elif char == '}':
                current_object += char
                brace_count -= 1
                
                if brace_count == 0:
                    # Complete object found
                    try:
                        file_op = json.loads(current_object)
                        if (isinstance(file_op, dict) and 
                            all(key in file_op for key in ['operation', 'path', 'content'])):
                            
                            # Clean up the file operation
                            cleaned_file_op = _clean_file_operation(file_op)
                            if cleaned_file_op:
                                file_operations.append(cleaned_file_op)
                    except json.JSONDecodeError:
                        pass  # Skip malformed objects
                    current_object = ""
            elif char == ']' and brace_count == 0:
                # End of array
                break
            elif brace_count > 0:
                current_object += char
        else:
            current_object += char
            
        i += 1
    
    return file_operations


def _clean_file_operation(file_op: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Clean and validate a file operation object
    
    Args:
        file_op: Raw file operation dictionary
        
    Returns:
        Cleaned file operation or None if invalid
    """
    if not isinstance(file_op, dict):
        return None
    
    path = file_op.get('path', '').strip()
    content = file_op.get('content', '').strip()
    operation = file_op.get('operation', 'modify').strip()
    
    # Skip if missing required fields
    if not path or not content or not operation:
        return None
    
    # Fix duplicate path issues (e.g., "lib/models/todo.dartlib/models/todo.dart")
    if path.count('.dart') > 1:
        # Find the first .dart occurrence and use everything up to that point
        first_dart_pos = path.find('.dart')
        if first_dart_pos != -1:
            path = path[:first_dart_pos + 5]  # Include ".dart"
    
    # Fix paths with duplicate directory names
    path_parts = path.split('/')
    if len(path_parts) > 2:
        # Check for duplicate directory names like "lib/models/todo_model.dartlib/models"
        clean_parts = []
        seen_dirs = set()
        
        for i, part in enumerate(path_parts):
            if i == len(path_parts) - 1:  # Last part (filename)
                clean_parts.append(part)
            elif part not in seen_dirs or part in ['lib', 'src', 'test']:  # Allow common dirs
                clean_parts.append(part)
                seen_dirs.add(part)
        
        path = '/'.join(clean_parts)
    
    # Remove truncation markers
    content = content.replace('▋', '').strip()
    
    # Skip if content looks incomplete (ends with incomplete syntax)
    if (content.endswith(',\\') or 
        content.endswith('child: const Icon(Icons.add),\\') or
        content.count('{') != content.count('}') and len(content) > 100):
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.CODE_MOD, f"Skipping incomplete file operation: {path}")
        return None
    
    return {
        'operation': operation,
        'path': path,
        'content': content,
        'reason': file_op.get('reason', ''),
        'validation': file_op.get('validation', '')
    }


def _extract_individual_json_objects(text: str) -> List[str]:
    """
    Extract individual JSON objects from text using brace balancing
    
    Args:
        text: Text that may contain JSON objects
        
    Returns:
        List of complete JSON object strings
    """
    objects = []
    i = 0
    
    while i < len(text):
        if text[i] == '{':
            # Found start of potential JSON object
            obj_str, end_pos = _extract_balanced_braces(text, i)
            if obj_str:
                objects.append(obj_str)
                i = end_pos
            else:
                i += 1
        else:
            i += 1
    
    return objects


def _extract_balanced_braces(text: str, start: int) -> Tuple[str, int]:
    """
    Extract a balanced JSON object starting from the given position
    
    Args:
        text: The text to extract from
        start: Starting position (should be at '{')
        
    Returns:
        Tuple of (extracted_object_string, end_position)
    """
    if start >= len(text) or text[start] != '{':
        return "", start
    
    brace_count = 0
    in_string = False
    escape_next = False
    i = start
    
    while i < len(text):
        char = text[i]
        
        if escape_next:
            escape_next = False
        elif char == '\\' and in_string:
            escape_next = True
        elif char == '"' and not escape_next:
            in_string = not in_string
        elif not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Complete object found
                    return text[start:i+1], i + 1
        
        i += 1
    
    # Incomplete object
    return "", i


def extract_shell_commands_from_response(response: str, context: str = "shell commands") -> List[str]:
    """
    Extract shell commands from potentially truncated JSON response
    
    Args:
        response: Raw LLM response text (may be truncated)
        context: Context description for logging
        
    Returns:
        List of shell commands found in response
    """
    shell_commands = []
    
    # Method 1: Try to find complete shell_commands array
    shell_pattern = r'"shell_commands"\s*:\s*\[(.*?)\]'
    match = re.search(shell_pattern, response, re.DOTALL)
    if match:
        try:
            # Extract individual command strings
            commands_text = match.group(1)
            command_matches = re.findall(r'"([^"]+)"', commands_text)
            shell_commands.extend(command_matches)
            if MONITORING_AVAILABLE:
                logger.debug(LogCategory.CODE_MOD, f"Extracted {len(command_matches)} shell commands")
        except Exception:
            pass
    
    # Method 2: Look for individual shell command patterns
    individual_pattern = r'"((?:flutter|dart|npm)\s+[^"]+)"'
    matches = re.findall(individual_pattern, response)
    for command in matches:
        if command not in shell_commands:
            shell_commands.append(command)
    
    return shell_commands


def extract_file_operations_from_response(response: str, context: str = "file operations") -> Dict[str, Any]:
    """
    Extract and validate file operations from LLM response
    
    Args:
        response: Raw LLM response text
        context: Context description for logging
        
    Returns:
        Validated file operations dictionary
    """
    try:
        data = safe_json_loads(response, context, default={})
        return validate_file_operation_response(data)
        
    except Exception as e:
        if MONITORING_AVAILABLE:
            logger.error(LogCategory.CODE_MOD, f"Failed to extract file operations from {context}: {str(e)}")
        
        # Return empty file operations as fallback
        return {
            "directly_modified_files": [],
            "files_to_create": [],
            "files_to_delete": [],
            "all_relevant_files": []
        }