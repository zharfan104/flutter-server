"""
Flutter Typo Detection and Auto-Fix System
Detects and fixes common Flutter/Dart typos before running full AI recovery
"""

import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class FlutterTypoFixer:
    """Detects and fixes common Flutter typos automatically"""
    
    def __init__(self):
        # Common Flutter typos and their fixes
        self.typo_patterns = {
            # Most common: runApp typo
            r'\brunsApp\s*\(': 'runApp(',
            
            # Widget typos
            r'\bStatlessWidget\b': 'StatelessWidget',
            r'\bStatefullWidget\b': 'StatefulWidget',
            r'\bStatlessWidget\b': 'StatelessWidget',
            
            # Build method typos
            r'\bbuild\s*Wdiget\b': 'buildWidget',
            r'\bbuild\s*Context\b': 'BuildContext',
            
            # Material typos
            r'\bMaterilApp\b': 'MaterialApp',
            r'\bMaterailApp\b': 'MaterialApp',
            r'\bMaterApp\b': 'MaterialApp',
            
            # Common widget typos
            r'\bContainer\s*\(\s*child\s*:\s*Childern\b': 'Container(child: Children',
            r'\bColumn\s*\(\s*childern\s*:': 'Column(children:',
            r'\bRow\s*\(\s*childern\s*:': 'Row(children:',
            
            # Import typos
            r"import\s+'package:flutter/meterial\.dart'": "import 'package:flutter/material.dart'",
            r"import\s+'package:flutter/materail\.dart'": "import 'package:flutter/material.dart'",
        }
        
        # Flutter function name typos
        self.function_typos = {
            'runsApp': 'runApp',
            'runAp': 'runApp',
            'runApps': 'runApp',
            'ruApp': 'runApp',
            'StatlessWidget': 'StatelessWidget',
            'StatefullWidget': 'StatefulWidget',
            'StatlessWidget': 'StatelessWidget',
            'buildWdiget': 'build',
            'buildContect': 'build',
            'MaterilApp': 'MaterialApp',
            'MaterailApp': 'MaterialApp',
        }
    
    def detect_typos_in_error(self, error_message: str) -> List[Dict[str, str]]:
        """
        Detect typos in dart analyze error messages
        Returns list of detected typos with suggested fixes
        """
        typos_found = []
        
        # Look for "undefined function" errors
        undefined_func_pattern = r"The function '(\w+)' isn't defined"
        matches = re.findall(undefined_func_pattern, error_message)
        
        for func_name in matches:
            if func_name in self.function_typos:
                typos_found.append({
                    'original': func_name,
                    'corrected': self.function_typos[func_name],
                    'type': 'function_typo',
                    'confidence': 'high'
                })
            else:
                # Check for similar function names
                suggestion = self._find_similar_function(func_name)
                if suggestion:
                    typos_found.append({
                        'original': func_name,
                        'corrected': suggestion,
                        'type': 'function_suggestion',
                        'confidence': 'medium'
                    })
        
        return typos_found
    
    def _find_similar_function(self, func_name: str) -> Optional[str]:
        """Find similar function names using simple heuristics"""
        common_flutter_functions = [
            'runApp', 'StatelessWidget', 'StatefulWidget', 'MaterialApp',
            'build', 'setState', 'initState', 'dispose', 'didUpdateWidget'
        ]
        
        func_lower = func_name.lower()
        
        # Simple similarity check
        for correct_func in common_flutter_functions:
            correct_lower = correct_func.lower()
            
            # Check if it's a substring or very similar
            if (func_lower in correct_lower or correct_lower in func_lower or
                self._similar_strings(func_lower, correct_lower)):
                return correct_func
        
        return None
    
    def _similar_strings(self, s1: str, s2: str, threshold: float = 0.7) -> bool:
        """Simple string similarity check"""
        if len(s1) == 0 or len(s2) == 0:
            return False
        
        # Simple character overlap ratio
        s1_set = set(s1)
        s2_set = set(s2)
        overlap = len(s1_set & s2_set)
        total = len(s1_set | s2_set)
        
        return (overlap / total) > threshold
    
    def fix_typos_in_file(self, file_path: Path) -> Dict[str, any]:
        """
        Fix typos in a Dart file
        Returns information about fixes applied
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixes_applied = []
            
            # Apply regex-based fixes
            for pattern, replacement in self.typo_patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    fixes_applied.append({
                        'type': 'regex_fix',
                        'pattern': pattern,
                        'replacement': replacement,
                        'matches': len(matches)
                    })
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return {
                    'success': True,
                    'fixes_applied': len(fixes_applied),
                    'fixes_details': fixes_applied,
                    'file_modified': True
                }
            else:
                return {
                    'success': True,
                    'fixes_applied': 0,
                    'fixes_details': [],
                    'file_modified': False
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'fixes_applied': 0,
                'file_modified': False
            }
    
    def fix_specific_typo(self, file_path: Path, line_number: int, 
                         original: str, corrected: str) -> Dict[str, any]:
        """
        Fix a specific typo at a specific line
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number <= 0 or line_number > len(lines):
                return {'success': False, 'error': 'Invalid line number'}
            
            # Fix the specific line (1-indexed to 0-indexed)
            line_idx = line_number - 1
            original_line = lines[line_idx]
            
            if original in original_line:
                fixed_line = original_line.replace(original, corrected)
                lines[line_idx] = fixed_line
                
                # Write back the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                return {
                    'success': True,
                    'original_line': original_line.strip(),
                    'fixed_line': fixed_line.strip(),
                    'file_modified': True
                }
            else:
                return {
                    'success': False,
                    'error': f"'{original}' not found in line {line_number}",
                    'file_modified': False
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file_modified': False
            }
    
    def analyze_dart_errors(self, dart_analyze_output: str) -> Dict[str, any]:
        """
        Analyze dart analyze output for potential typos
        Returns suggested fixes
        """
        typos_detected = []
        
        # Parse dart analyze output
        lines = dart_analyze_output.split('\n')
        
        for line in lines:
            if 'error' in line and "isn't defined" in line:
                # Extract file, line number, and function name
                # Format: error - main.dart:11:3 - The function 'runsApp' isn't defined...
                match = re.search(r'error\s*-\s*(\S+):(\d+):(\d+)\s*-\s*(.+)', line)
                if match:
                    file_name, line_num, col_num, error_msg = match.groups()
                    
                    detected = self.detect_typos_in_error(error_msg)
                    for typo in detected:
                        typo.update({
                            'file': file_name,
                            'line': int(line_num),
                            'column': int(col_num),
                            'full_error': error_msg
                        })
                        typos_detected.append(typo)
        
        return {
            'typos_found': len(typos_detected),
            'typos_details': typos_detected,
            'auto_fixable': [t for t in typos_detected if t['confidence'] == 'high']
        }