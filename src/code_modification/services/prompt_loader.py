"""
Prompt Loader for Code Modification System
Loads and manages prompts from YAML files
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path


class PromptLoader:
    """
    Loads and manages prompts from YAML files
    """
    
    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Default to prompts directory relative to this file
            current_dir = Path(__file__).parent
            self.prompts_dir = current_dir / "prompts"
        else:
            self.prompts_dir = Path(prompts_dir)
        
        self._prompts_cache = {}
        self._load_all_prompts()
    
    def _load_all_prompts(self):
        """Load all YAML prompt files from the prompts directory"""
        if not self.prompts_dir.exists():
            print(f"Warning: Prompts directory {self.prompts_dir} does not exist")
            return
        
        for yaml_file in self.prompts_dir.rglob("*.yaml"):
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    prompt_data = yaml.safe_load(f)
                
                prompt_name = prompt_data.get('name', yaml_file.stem)
                self._prompts_cache[prompt_name] = prompt_data
                print(f"Loaded prompt: {prompt_name}")
                
            except Exception as e:
                print(f"Error loading prompt file {yaml_file}: {e}")
    
    def get_prompt_template(self, prompt_name: str) -> str:
        """
        Get the template string for a specific prompt
        
        Args:
            prompt_name: Name of the prompt to retrieve
            
        Returns:
            The prompt template string
            
        Raises:
            KeyError: If prompt is not found
        """
        if prompt_name not in self._prompts_cache:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts_cache.keys())}")
        
        prompt_data = self._prompts_cache[prompt_name]
        # Support legacy 'template' field and newer 'prompt' field for backward compatibility
        return prompt_data.get('template', prompt_data.get('user_template', prompt_data.get('prompt', '')))
    
    def get_prompt_info(self, prompt_name: str) -> Dict[str, Any]:
        """
        Get full information about a prompt including metadata
        
        Args:
            prompt_name: Name of the prompt to retrieve
            
        Returns:
            Dictionary containing prompt data
        """
        if prompt_name not in self._prompts_cache:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts_cache.keys())}")
        
        return self._prompts_cache[prompt_name]
    
    def list_available_prompts(self) -> list:
        """
        Get list of all available prompt names
        
        Returns:
            List of prompt names
        """
        return list(self._prompts_cache.keys())
    
    def reload_prompts(self):
        """Reload all prompts from files"""
        self._prompts_cache.clear()
        self._load_all_prompts()
    
    def get_system_prompt(self, prompt_name: str) -> str:
        """
        Get the system prompt for a specific prompt (v2.0+ prompts)
        
        Args:
            prompt_name: Name of the prompt to retrieve
            
        Returns:
            The system prompt string
            
        Raises:
            KeyError: If prompt is not found or doesn't have system_prompt
        """
        if prompt_name not in self._prompts_cache:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts_cache.keys())}")
        
        prompt_data = self._prompts_cache[prompt_name]
        if 'system_prompt' not in prompt_data:
            # Fall back to empty system prompt for legacy prompts
            return ""
        
        return prompt_data['system_prompt']
    
    def get_user_template(self, prompt_name: str) -> str:
        """
        Get the user template for a specific prompt (v2.0+ prompts)
        
        Args:
            prompt_name: Name of the prompt to retrieve
            
        Returns:
            The user template string
            
        Raises:
            KeyError: If prompt is not found
        """
        if prompt_name not in self._prompts_cache:
            raise KeyError(f"Prompt '{prompt_name}' not found. Available prompts: {list(self._prompts_cache.keys())}")
        
        prompt_data = self._prompts_cache[prompt_name]
        # Support both new format and legacy format
        return prompt_data.get('user_template', prompt_data.get('template', prompt_data.get('prompt', '')))
    
    def format_user_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Format a user prompt template with provided variables
        
        Args:
            prompt_name: Name of the prompt to format
            **kwargs: Variables to substitute in the template
            
        Returns:
            Formatted user prompt string
        """
        template = self.get_user_template(prompt_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required variable for prompt '{prompt_name}': {e}")
    
    def get_system_user_prompts(self, prompt_name: str, **kwargs) -> tuple[str, str]:
        """
        Get both system and formatted user prompts for modern (v2.0+) prompts
        
        Args:
            prompt_name: Name of the prompt to retrieve
            **kwargs: Variables to substitute in the user template
            
        Returns:
            Tuple of (system_prompt, formatted_user_prompt)
        """
        system_prompt = self.get_system_prompt(prompt_name)
        user_prompt = self.format_user_prompt(prompt_name, **kwargs)
        return system_prompt, user_prompt
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Format a prompt template with provided variables (legacy method)
        
        Args:
            prompt_name: Name of the prompt to format
            **kwargs: Variables to substitute in the template
            
        Returns:
            Formatted prompt string
        """
        template = self.get_prompt_template(prompt_name)
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required variable for prompt '{prompt_name}': {e}")


# Global instance for easy access
prompt_loader = PromptLoader()