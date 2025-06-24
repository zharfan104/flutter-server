"""
Flutter Management Constants

Constants used throughout the Flutter management module
"""

from enum import Enum
from typing import List


class ProcessState(Enum):
    """Flutter process states"""
    STOPPED = "stopped"
    STARTING = "starting" 
    RUNNING = "running"
    READY = "ready"
    ERROR = "error"


class DevMode(Enum):
    """Flutter development modes"""
    FAST = "fast"
    DEBUG = "debug"
    PROFILE = "profile"


# Flutter command constants
FLUTTER_COMMANDS = {
    'CREATE': ['flutter', 'create'],
    'RUN': ['flutter', 'run'],
    'HOT_RELOAD': 'r\n',
    'HOT_RESTART': 'R\n',
    'QUIT': 'q\n'
}

# Git command constants
GIT_COMMANDS = {
    'CLONE': ['git', 'clone'],
    'PULL': ['git', 'pull'],
    'STATUS': ['git', 'status']
}

# Process monitoring constants
PROCESS_TIMEOUTS = {
    'STARTUP': 2,  # seconds
    'OUTPUT_READ': 0.1,  # seconds
    'RECOVERY': 300,  # 5 minutes
}

# Output buffer limits
OUTPUT_LIMITS = {
    'MAX_BUFFER_SIZE': 1000,
    'TRUNCATE_TO': 500,
    'RECENT_LINES': 10
}

# Ready detection patterns
READY_DETECTION_PHRASES: List[str] = [
    "is being served at",
    "running application at", 
    "web development server is available at",
    "http://",
    "application started"
]

# Error patterns for hot reload
HOT_RELOAD_ERROR_PATTERNS: List[str] = [
    "Error:",
    "error:",
    "Try again after fixing",
    "failed to compile", 
    "compilation failed",
    "Member not found:",
    "The method",
    "The getter",
    "The setter"
]

# Success patterns for hot reload
HOT_RELOAD_SUCCESS_PATTERNS: List[str] = [
    "Restarted application in",
    "Hot reload completed",
    "Recompile complete", 
    "Application finished",
    "Restarted application",
    "Hot reload performed",
    "Performing hot restart",
    "Hot reload.",
    "successfully"
]

# Default ports
DEFAULT_PORTS = {
    'FLUTTER_WEB': 8080,
    'FLASK_API': 5000
}

# Project structure constants
PROJECT_STRUCTURE = {
    'PROJECT_DIR': 'project',
    'LIB_DIR': 'lib',
    'PUBSPEC_FILE': 'pubspec.yaml',
    'MAIN_DART': 'lib/main.dart'
}