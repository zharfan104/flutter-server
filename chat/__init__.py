"""
Chat module for Flutter development server
Provides in-memory conversation management and AI chat capabilities
"""

from .chat_manager import ChatManager, ChatMessage, Conversation, chat_manager

__all__ = [
    'ChatManager',
    'ChatMessage', 
    'Conversation',
    'chat_manager'
]