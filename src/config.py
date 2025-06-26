"""
Global Configuration

Global application configuration and settings
"""

import os
from typing import Dict, Any


class GlobalConfig:
    """Global application configuration"""
    
    # Flask settings
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 5000
    
    # Flutter settings
    FLUTTER_WEB_PORT = 8080
    FLUTTER_WEB_HOSTNAME = "0.0.0.0"
    
    # Project settings
    PROJECT_DIR = "project"
    LOGS_DIR = "logs"
    
    # Monitoring settings
    ENABLE_MONITORING = True
    ENABLE_PERFORMANCE_MONITORING = True
    ENABLE_REQUEST_TRACING = True
    
    # Chat settings
    DEFAULT_CONVERSATION_TITLE = "New Conversation"
    
    @classmethod
    def from_environment(cls) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}
        
        # Flask settings
        config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
        config['HOST'] = os.environ.get('FLASK_HOST', cls.HOST)
        config['PORT'] = int(os.environ.get('FLASK_PORT', cls.PORT))
        
        # Flutter settings
        config['FLUTTER_WEB_PORT'] = int(os.environ.get('FLUTTER_WEB_PORT', cls.FLUTTER_WEB_PORT))
        config['FLUTTER_WEB_HOSTNAME'] = os.environ.get('FLUTTER_WEB_HOSTNAME', cls.FLUTTER_WEB_HOSTNAME)
        config['FLUTTER_DEV_MODE'] = os.environ.get('FLUTTER_DEV_MODE', 'fast')
        
        # Repository settings
        config['REPO_URL'] = os.environ.get('REPO_URL', '')
        config['GITHUB_TOKEN'] = os.environ.get('GITHUB_TOKEN', '')
        
        # Monitoring settings
        config['ENABLE_MONITORING'] = os.environ.get('ENABLE_MONITORING', 'True').lower() == 'true'
        config['ENABLE_PERFORMANCE_MONITORING'] = os.environ.get('ENABLE_PERFORMANCE_MONITORING', 'True').lower() == 'true'
        config['ENABLE_REQUEST_TRACING'] = os.environ.get('ENABLE_REQUEST_TRACING', 'True').lower() == 'true'
        
        return config