"""
Flutter Management Configuration

Configuration settings specific to Flutter process management
"""

import os
from typing import List, Dict, Any


class FlutterConfig:
    """Configuration for Flutter management operations"""
    
    # Default Flutter development server settings
    DEFAULT_WEB_PORT = 8080
    DEFAULT_WEB_HOSTNAME = "0.0.0.0"
    
    # Development mode configurations
    DEV_MODES = {
        'fast': {
            'dart_defines': [
                "FLUTTER_WEB_USE_SKIA=false",
                "FLUTTER_WEB_USE_EXPERIMENTAL_CANVAS_TEXT=false"
            ],
            'web_browser_flags': [
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--disable-backgrounding-occluded-windows"
            ]
        },
        'profile': {
            'args': ["--profile"],
            'web_renderer': "canvaskit"
        },
        'debug': {
            # Default Flutter debug settings
        }
    }
    
    # Output buffer settings
    MAX_OUTPUT_BUFFER_SIZE = 1000
    TRUNCATE_OUTPUT_TO = 500
    
    # Process monitoring settings
    STARTUP_WAIT_TIME = 2  # seconds
    OUTPUT_READ_TIMEOUT = 0.1  # seconds
    
    # Ready detection phrases
    READY_PHRASES = [
        "is being served at",
        "running application at", 
        "web development server is available at",
        "http://",
        "application started"
    ]
    
    @classmethod
    def get_flutter_command(cls, dev_mode: str = 'fast') -> List[str]:
        """Get Flutter command with appropriate flags for the given dev mode"""
        base_cmd = [
            "flutter", "run",
            "-d", "web-server",
            f"--web-port={cls.DEFAULT_WEB_PORT}",
            f"--web-hostname={cls.DEFAULT_WEB_HOSTNAME}"
        ]
        
        mode_config = cls.DEV_MODES.get(dev_mode, {})
        
        # Add dart defines
        for define in mode_config.get('dart_defines', []):
            base_cmd.extend([f"--dart-define={define}"])
        
        # Add web browser flags
        for flag in mode_config.get('web_browser_flags', []):
            base_cmd.extend([f"--web-browser-flag={flag}"])
        
        # Add additional args
        base_cmd.extend(mode_config.get('args', []))
        
        # Add web renderer
        if 'web_renderer' in mode_config:
            base_cmd.extend([f"--web-renderer={mode_config['web_renderer']}"])
        
        return base_cmd
    
    @classmethod
    def get_project_path(cls) -> str:
        """Get the Flutter project path"""
        return os.path.join(os.getcwd(), "project")
    
    @classmethod
    def get_repo_url(cls) -> str:
        """Get repository URL from environment"""
        return os.environ.get('REPO_URL', '')
    
    @classmethod
    def get_github_token(cls) -> str:
        """Get GitHub token from environment"""
        return os.environ.get('GITHUB_TOKEN', '')
    
    @classmethod
    def get_dev_mode(cls) -> str:
        """Get development mode from environment"""
        return os.environ.get('FLUTTER_DEV_MODE', 'fast').lower()