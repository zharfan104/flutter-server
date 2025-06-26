"""
Global Dependencies

Dependency injection and service registration
"""

from typing import Optional
from .flutter_management.service import FlutterManager


class ServiceContainer:
    """Simple service container for dependency injection"""
    
    def __init__(self):
        self._flutter_manager: Optional[FlutterManager] = None
        self._chat_manager = None
        self._monitoring_available = False
    
    def set_flutter_manager(self, manager: FlutterManager):
        """Set the Flutter manager instance"""
        self._flutter_manager = manager
    
    def get_flutter_manager(self) -> Optional[FlutterManager]:
        """Get the Flutter manager instance"""
        return self._flutter_manager
    
    def set_chat_manager(self, manager):
        """Set the chat manager instance"""
        self._chat_manager = manager
    
    def get_chat_manager(self):
        """Get the chat manager instance"""
        return self._chat_manager
    
    def set_monitoring_available(self, available: bool):
        """Set monitoring availability"""
        self._monitoring_available = available
    
    def is_monitoring_available(self) -> bool:
        """Check if monitoring is available"""
        return self._monitoring_available


# Global service container instance
services = ServiceContainer()