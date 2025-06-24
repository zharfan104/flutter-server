"""
Flutter Management Exceptions

Custom exceptions for Flutter management operations
"""


class FlutterManagementError(Exception):
    """Base exception for Flutter management operations"""
    pass


class ProcessStartError(FlutterManagementError):
    """Raised when Flutter process fails to start"""
    
    def __init__(self, message: str, command: str = None, error_output: str = None):
        super().__init__(message)
        self.command = command
        self.error_output = error_output


class ProcessNotRunningError(FlutterManagementError):
    """Raised when attempting operations on a non-running Flutter process"""
    pass


class ProjectSetupError(FlutterManagementError):
    """Raised when Flutter project setup fails"""
    
    def __init__(self, message: str, project_path: str = None, repo_url: str = None):
        super().__init__(message)
        self.project_path = project_path
        self.repo_url = repo_url


class HotReloadError(FlutterManagementError):
    """Raised when hot reload operations fail"""
    
    def __init__(self, message: str, reload_output: str = None, compilation_errors: list = None):
        super().__init__(message)
        self.reload_output = reload_output
        self.compilation_errors = compilation_errors or []


class FileOperationError(FlutterManagementError):
    """Raised when file operations fail"""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        super().__init__(message)
        self.file_path = file_path
        self.operation = operation


class OutputBufferError(FlutterManagementError):
    """Raised when output buffer operations fail"""
    pass


class ProcessMonitoringError(FlutterManagementError):
    """Raised when process monitoring fails"""
    
    def __init__(self, message: str, process_id: int = None):
        super().__init__(message)
        self.process_id = process_id


class ConfigurationError(FlutterManagementError):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, config_key: str = None, config_value: str = None):
        super().__init__(message)
        self.config_key = config_key
        self.config_value = config_value