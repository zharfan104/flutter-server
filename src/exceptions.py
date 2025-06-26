"""
Global Exceptions

Global exception classes and error handlers
"""


class FlutterServerError(Exception):
    """Base exception for Flutter server"""
    pass


class ServiceNotAvailableError(FlutterServerError):
    """Raised when a required service is not available"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Service not available: {service_name}")


class ConfigurationError(FlutterServerError):
    """Raised when configuration is invalid"""
    pass


class DependencyInjectionError(FlutterServerError):
    """Raised when dependency injection fails"""
    pass


class ModuleImportError(FlutterServerError):
    """Raised when a required module cannot be imported"""
    
    def __init__(self, module_name: str, original_error: Exception = None):
        self.module_name = module_name
        self.original_error = original_error
        super().__init__(f"Failed to import module: {module_name}")


def create_error_handlers(app):
    """Create error handlers for the Flask app"""
    
    @app.errorhandler(ServiceNotAvailableError)
    def handle_service_not_available(error):
        return {
            "error": str(error),
            "service_name": error.service_name,
            "type": "service_not_available"
        }, 503
    
    @app.errorhandler(ConfigurationError)
    def handle_configuration_error(error):
        return {
            "error": str(error),
            "type": "configuration_error"
        }, 500
    
    @app.errorhandler(DependencyInjectionError)
    def handle_dependency_injection_error(error):
        return {
            "error": str(error),
            "type": "dependency_injection_error"
        }, 500
    
    @app.errorhandler(ModuleImportError)
    def handle_module_import_error(error):
        return {
            "error": str(error),
            "module_name": error.module_name,
            "type": "module_import_error"
        }, 500