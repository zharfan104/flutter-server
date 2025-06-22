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
        
        for yaml_file in self.prompts_dir.glob("*.yaml"):
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
        
        return self._prompts_cache[prompt_name]['template']
    
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
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Format a prompt template with provided variables
        
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