"""
Flutter Management Utilities

Utility functions for Flutter management operations
"""

import os
import socket
import subprocess
import time
from typing import Tuple, Optional, List, Dict, Any

from .constants import DEFAULT_PORTS, READY_DETECTION_PHRASES
from .exceptions import ProcessStartError, ConfigurationError


def check_port_available(port: int, host: str = 'localhost') -> bool:
    """Check if a port is available for use"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result != 0  # Port is available if connection failed
    except Exception:
        return False


def kill_process_on_port(port: int) -> bool:
    """Kill any process running on the specified port"""
    try:
        # Try to find and kill process on port
        result = subprocess.run(
            ["pkill", "-9", "-f", f":{port}"], 
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        time.sleep(1)  # Give time for process to die
        return True
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        return False


def ensure_port_free(port: int, force: bool = False) -> bool:
    """Ensure a port is free, optionally killing existing processes"""
    if check_port_available(port):
        return True
    
    if force:
        return kill_process_on_port(port)
    
    return False


def validate_project_structure(project_path: str) -> Tuple[bool, List[str]]:
    """Validate Flutter project structure and return issues if any"""
    issues = []
    
    if not os.path.exists(project_path):
        issues.append(f"Project directory does not exist: {project_path}")
        return False, issues
    
    # Check for essential Flutter files
    essential_files = [
        'pubspec.yaml',
        'lib/main.dart'
    ]
    
    for file_path in essential_files:
        full_path = os.path.join(project_path, file_path)
        if not os.path.exists(full_path):
            issues.append(f"Missing essential file: {file_path}")
    
    # Check for Flutter project indicators
    pubspec_path = os.path.join(project_path, 'pubspec.yaml')
    if os.path.exists(pubspec_path):
        try:
            with open(pubspec_path, 'r') as f:
                content = f.read()
                if 'flutter:' not in content.lower():
                    issues.append("pubspec.yaml does not appear to be a Flutter project")
        except Exception as e:
            issues.append(f"Could not read pubspec.yaml: {str(e)}")
    
    return len(issues) == 0, issues


def parse_flutter_output(output_line: str) -> Dict[str, Any]:
    """Parse Flutter output line and extract useful information"""
    result = {
        'type': 'info',
        'message': output_line.strip(),
        'is_ready_indicator': False,
        'is_error': False,
        'timestamp': time.time()
    }
    
    line_lower = output_line.lower()
    
    # Check for ready indicators
    if any(phrase in line_lower for phrase in READY_DETECTION_PHRASES):
        result['is_ready_indicator'] = True
        result['type'] = 'ready'
    
    # Check for errors
    error_indicators = ['error:', 'exception:', 'failed:', 'could not']
    if any(indicator in line_lower for indicator in error_indicators):
        result['is_error'] = True
        result['type'] = 'error'
    
    # Check for warnings
    warning_indicators = ['warning:', 'warn:']
    if any(indicator in line_lower for indicator in warning_indicators):
        result['type'] = 'warning'
    
    return result


def extract_url_from_output(output: str) -> Optional[str]:
    """Extract URL from Flutter output if present"""
    lines = output.split('\n')
    for line in lines:
        if 'http://' in line or 'https://' in line:
            # Simple URL extraction
            words = line.split()
            for word in words:
                if word.startswith(('http://', 'https://')):
                    return word.strip('.,;')
    return None


def format_command_for_logging(command: List[str]) -> str:
    """Format command list for logging purposes"""
    return ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)


def get_git_auth_url(repo_url: str, token: str) -> str:
    """Insert GitHub token into repository URL for authentication"""
    if not token or not repo_url:
        return repo_url
    
    if repo_url.startswith('https://'):
        return repo_url.replace('https://', f'https://{token}@')
    
    return repo_url


def sanitize_environment_config() -> Dict[str, str]:
    """Get and sanitize environment configuration for Flutter"""
    config = {}
    
    # Get environment variables with defaults
    config['repo_url'] = os.environ.get('REPO_URL', '')
    config['github_token'] = os.environ.get('GITHUB_TOKEN', '')
    config['dev_mode'] = os.environ.get('FLUTTER_DEV_MODE', 'fast').lower()
    
    # Validate dev_mode
    valid_modes = ['fast', 'debug', 'profile']
    if config['dev_mode'] not in valid_modes:
        raise ConfigurationError(
            f"Invalid dev mode: {config['dev_mode']}. Must be one of: {valid_modes}",
            config_key='FLUTTER_DEV_MODE',
            config_value=config['dev_mode']
        )
    
    return config


def is_flutter_project(path: str) -> bool:
    """Check if a directory contains a Flutter project"""
    pubspec_path = os.path.join(path, 'pubspec.yaml')
    
    if not os.path.exists(pubspec_path):
        return False
    
    try:
        with open(pubspec_path, 'r') as f:
            content = f.read().lower()
            return 'flutter:' in content
    except Exception:
        return False


def get_flutter_version() -> Optional[str]:
    """Get Flutter version if available"""
    try:
        result = subprocess.run(
            ['flutter', '--version'], 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            return first_line.strip()
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    return None