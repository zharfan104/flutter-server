"""
JSON Utilities for Code Modification System
Handles extraction of JSON from LLM responses that may be wrapped in markdown
"""

import json
import re
from typing import Any, Dict, Optional

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