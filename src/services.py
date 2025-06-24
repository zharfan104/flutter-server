"""
Service Registry and Initialization

Standardized service management for the Flutter server application.
"""

import os
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ServiceResult:
    """Result of service initialization"""
    success: bool
    service: Any
    error: Optional[str] = None


class ServiceRegistry:
    """Centralized service registry with dependency injection"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._initialized = False
    
    def register(self, name: str, service: Any) -> None:
        """Register a service in the registry"""
        self._services[name] = service
    
    def get(self, name: str) -> Any:
        """Get a service from the registry"""
        if name not in self._services:
            raise KeyError(f"Service '{name}' not found in registry")
        return self._services[name]
    
    def has(self, name: str) -> bool:
        """Check if a service exists in the registry"""
        return name in self._services
    
    def initialize_all(self) -> bool:
        """Initialize all services in the correct order"""
        if self._initialized:
            return True
        
        print("🔧 Initializing services...")
        
        # 1. Initialize monitoring first (optional)
        monitoring_result = self._initialize_monitoring_service()
        self.register('monitoring_available', monitoring_result.success)
        if monitoring_result.service:
            self.register('monitoring', monitoring_result.service)
        
        # 2. Initialize Flutter manager (required)
        flutter_result = self._initialize_flutter_service()
        if not flutter_result.success:
            print(f"❌ Critical service failed: {flutter_result.error}")
            return False
        self.register('flutter_manager', flutter_result.service)
        
        # 3. Initialize chat manager (optional)
        chat_result = self._initialize_chat_service()
        if chat_result.success:
            self.register('chat_manager', chat_result.service)
        
        self._initialized = True
        print("✅ All services initialized successfully")
        return True
    
    def inject_dependencies(self, router_modules: list) -> None:
        """Inject dependencies into router modules"""
        for module in router_modules:
            if hasattr(module, 'set_dependencies'):
                # Get required services for this module
                services = {}
                if self.has('flutter_manager'):
                    services['flutter_manager'] = self.get('flutter_manager')
                if self.has('chat_manager'):
                    services['chat_manager'] = self.get('chat_manager')
                if self.has('monitoring'):
                    services['monitoring'] = self.get('monitoring')
                
                module.set_dependencies(**services)
    
    def _initialize_monitoring_service(self) -> ServiceResult:
        """Initialize advanced logging and monitoring systems"""
        try:
            from src.utils.advanced_logger import logger, LogCategory, RequestTracker
            from src.utils.request_tracer import tracer
            from src.utils.performance_monitor import performance_monitor
            from src.utils.error_analyzer import error_analyzer
            
            # Configure advanced logging
            logger.configure(
                enable_console=True, 
                enable_file=True, 
                log_file_path="logs/flutter_server.log"
            )
            
            # Start performance monitoring
            performance_monitor.start_monitoring()
            
            # Set up performance alert callback
            def alert_callback(alert):
                logger.warn(LogCategory.PERFORMANCE, f"Performance Alert: {alert.message}",
                           context={
                               "alert_id": alert.alert_id,
                               "metric": alert.metric_name,
                               "value": alert.current_value,
                               "threshold": alert.threshold,
                               "level": alert.level.value
                           },
                           tags=["alert", "performance"])
            
            performance_monitor.subscribe_to_alerts(alert_callback)
            
            # Log successful initialization
            logger.info(LogCategory.SYSTEM, "Advanced monitoring systems initialized",
                       context={
                           "logging_enabled": True,
                           "performance_monitoring": True,
                           "request_tracing": True,
                           "error_analysis": True
                       },
                       tags=["startup", "monitoring"])
            
            print("  ✓ Advanced monitoring and logging systems")
            
            # Return monitoring context
            monitoring_context = {
                'logger': logger,
                'tracer': tracer,
                'performance_monitor': performance_monitor,
                'error_analyzer': error_analyzer
            }
            
            return ServiceResult(True, monitoring_context)
            
        except ImportError as e:
            print(f"  ⚠️ Monitoring systems not available: {e}")
            return ServiceResult(True, None)  # Not critical, continue without monitoring
        except Exception as e:
            print(f"  ❌ Failed to initialize monitoring systems: {e}")
            return ServiceResult(True, None)  # Not critical, continue without monitoring
    
    def _initialize_flutter_service(self) -> ServiceResult:
        """Initialize Flutter manager service"""
        try:
            from .flutter_management.service import FlutterManager
            
            flutter_manager = FlutterManager()
            print("  ✓ Flutter management service")
            
            return ServiceResult(True, flutter_manager)
            
        except Exception as e:
            return ServiceResult(False, None, f"Failed to initialize Flutter service: {str(e)}")
    
    def _initialize_chat_service(self) -> ServiceResult:
        """Initialize chat manager service"""
        try:
            # Try new location first
            from .chat.services.chat_manager import chat_manager
            print("  ✓ Chat management service")
            return ServiceResult(True, chat_manager)
            
        except ImportError:
            # Fallback to old location
            try:
                from chat.chat_manager import chat_manager
                print("  ✓ Chat management service (legacy location)")
                return ServiceResult(True, chat_manager)
                
            except ImportError as e:
                print(f"  ⚠️ Chat manager not available: {e}")
                return ServiceResult(False, None, f"Chat service not available: {str(e)}")
        except Exception as e:
            return ServiceResult(False, None, f"Failed to initialize chat service: {str(e)}")


def setup_recovery_context(registry: ServiceRegistry) -> None:
    """Set up recovery context for Flutter manager"""
    if registry.has('flutter_manager') and registry.has('chat_manager'):
        flutter_manager = registry.get('flutter_manager')
        chat_manager = registry.get('chat_manager')
        flutter_manager.set_recovery_chat_context(chat_manager, None)


def log_startup_info(registry: ServiceRegistry) -> None:
    """Log startup information if monitoring is available"""
    if registry.has('monitoring') and registry.get('monitoring_available'):
        monitoring = registry.get('monitoring')
        logger = monitoring['logger']
        flutter_manager = registry.get('flutter_manager')
        
        # Import LogCategory to use proper enum
        try:
            from src.utils.advanced_logger import LogCategory
            logger.info(LogCategory.SYSTEM, "Flutter server application starting",
                       context={
                           "port": 5000,
                           "project_path": flutter_manager.project_path,
                           "repo_url": flutter_manager.repo_url is not None,
                           "dev_mode": flutter_manager.dev_mode
                       },
                       tags=["startup", "flask"])
        except Exception as e:
            print(f"Warning: Could not log startup info: {e}")


def log_ready_info(registry: ServiceRegistry) -> None:
    """Log ready information if monitoring is available"""
    if registry.has('monitoring') and registry.get('monitoring_available'):
        monitoring = registry.get('monitoring')
        logger = monitoring['logger']
        flutter_manager = registry.get('flutter_manager')
        
        # Import LogCategory to use proper enum
        try:
            from src.utils.advanced_logger import LogCategory
            logger.info(LogCategory.SYSTEM, "Flask server ready to serve requests",
                       context={
                           "host": "0.0.0.0",
                           "port": 5000,
                           "debug_mode": True,
                           "flutter_status": flutter_manager.is_running,
                           "monitoring_active": True
                       },
                       tags=["startup", "ready"])
        except Exception as e:
            print(f"Warning: Could not log ready info: {e}")