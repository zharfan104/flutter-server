"""
In-Memory Chat Manager
Handles conversation storage and management for AI chat interface
"""

import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: float
    message_id: str = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp,
            'message_id': self.message_id,
            'formatted_time': datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')
        }


@dataclass
class Conversation:
    """Represents a conversation thread"""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: float
    last_activity: float
    title: str = "New Conversation"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'conversation_id': self.conversation_id,
            'title': self.title,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'message_count': len(self.messages),
            'messages': [msg.to_dict() for msg in self.messages]
        }


class ChatManager:
    """
    In-memory chat manager for storing conversations and messages
    """
    
    def __init__(self):
        self.conversations: Dict[str, Conversation] = {}
        self.default_conversation_id = None
        print("ChatManager initialized with in-memory storage")
    
    def create_conversation(self, title: str = "New Conversation") -> str:
        """
        Create a new conversation
        
        Args:
            title: Title for the conversation
            
        Returns:
            conversation_id: Unique identifier for the conversation
        """
        conversation_id = str(uuid.uuid4())
        current_time = time.time()
        
        conversation = Conversation(
            conversation_id=conversation_id,
            messages=[],
            created_at=current_time,
            last_activity=current_time,
            title=title
        )
        
        self.conversations[conversation_id] = conversation
        
        # Set as default if it's the first conversation
        if self.default_conversation_id is None:
            self.default_conversation_id = conversation_id
        
        print(f"Created new conversation: {conversation_id}")
        return conversation_id
    
    def get_or_create_default_conversation(self) -> str:
        """
        Get the default conversation or create one if none exists
        
        Returns:
            conversation_id: Default conversation identifier
        """
        if self.default_conversation_id is None or self.default_conversation_id not in self.conversations:
            self.default_conversation_id = self.create_conversation("Flutter AI Assistant")
        
        return self.default_conversation_id
    
    def add_message(self, conversation_id: str, role: str, content: str) -> ChatMessage:
        """
        Add a message to a conversation
        
        Args:
            conversation_id: Conversation identifier
            role: 'user' or 'assistant'
            content: Message content
            
        Returns:
            ChatMessage: The created message
        """
        if conversation_id not in self.conversations:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=time.time()
        )
        
        conversation = self.conversations[conversation_id]
        conversation.messages.append(message)
        conversation.last_activity = time.time()
        
        # Update title if this is the first user message
        if role == 'user' and len(conversation.messages) == 1:
            # Generate a title from the first few words
            words = content.split()[:5]
            conversation.title = ' '.join(words) + ('...' if len(words) == 5 else '')
        
        print(f"Added {role} message to conversation {conversation_id}")
        return message
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation or None if not found
        """
        return self.conversations.get(conversation_id)
    
    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get messages from a conversation
        
        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages to return (most recent first)
            
        Returns:
            List of ChatMessage objects
        """
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        
        messages = conversation.messages
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_conversation_list(self) -> List[Dict]:
        """
        Get list of all conversations
        
        Returns:
            List of conversation summaries
        """
        conversations = []
        for conv in self.conversations.values():
            conversations.append({
                'conversation_id': conv.conversation_id,
                'title': conv.title,
                'created_at': conv.created_at,
                'last_activity': conv.last_activity,
                'message_count': len(conv.messages),
                'last_message': conv.messages[-1].content[:50] + '...' if conv.messages else '',
                'formatted_time': datetime.fromtimestamp(conv.last_activity).strftime('%Y-%m-%d %H:%M')
            })
        
        # Sort by last activity (most recent first)
        conversations.sort(key=lambda x: x['last_activity'], reverse=True)
        return conversations
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            bool: Success status
        """
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            
            # Reset default if this was the default conversation
            if self.default_conversation_id == conversation_id:
                if self.conversations:
                    # Set the most recent conversation as default
                    conversations = self.get_conversation_list()
                    self.default_conversation_id = conversations[0]['conversation_id'] if conversations else None
                else:
                    self.default_conversation_id = None
            
            print(f"Deleted conversation: {conversation_id}")
            return True
        
        return False
    
    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear all messages from a conversation
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            bool: Success status
        """
        conversation = self.get_conversation(conversation_id)
        if conversation:
            conversation.messages = []
            conversation.last_activity = time.time()
            print(f"Cleared conversation: {conversation_id}")
            return True
        
        return False
    
    def search_messages(self, query: str, conversation_id: Optional[str] = None) -> List[Dict]:
        """
        Search for messages containing specific text
        
        Args:
            query: Search query
            conversation_id: Optional conversation to search within
            
        Returns:
            List of matching messages with context
        """
        results = []
        conversations_to_search = [self.conversations[conversation_id]] if conversation_id else self.conversations.values()
        
        for conversation in conversations_to_search:
            for message in conversation.messages:
                if query.lower() in message.content.lower():
                    results.append({
                        'conversation_id': conversation.conversation_id,
                        'conversation_title': conversation.title,
                        'message': message.to_dict(),
                        'match_snippet': self._get_snippet(message.content, query)
                    })
        
        return results
    
    def _get_snippet(self, content: str, query: str, snippet_length: int = 100) -> str:
        """
        Get a snippet of text around the search query
        
        Args:
            content: Full text content
            query: Search query
            snippet_length: Length of snippet to return
            
        Returns:
            Text snippet with query highlighted
        """
        query_pos = content.lower().find(query.lower())
        if query_pos == -1:
            return content[:snippet_length] + '...'
        
        start = max(0, query_pos - snippet_length // 2)
        end = min(len(content), query_pos + len(query) + snippet_length // 2)
        
        snippet = content[start:end]
        if start > 0:
            snippet = '...' + snippet
        if end < len(content):
            snippet = snippet + '...'
        
        return snippet
    
    def get_stats(self) -> Dict:
        """
        Get statistics about conversations and messages
        
        Returns:
            Dictionary with usage statistics
        """
        total_conversations = len(self.conversations)
        total_messages = sum(len(conv.messages) for conv in self.conversations.values())
        user_messages = sum(
            len([msg for msg in conv.messages if msg.role == 'user'])
            for conv in self.conversations.values()
        )
        assistant_messages = total_messages - user_messages
        
        return {
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'average_messages_per_conversation': total_messages / total_conversations if total_conversations > 0 else 0,
            'active_conversations': len([conv for conv in self.conversations.values() if conv.messages])
        }
    
    def export_conversation(self, conversation_id: str) -> Optional[Dict]:
        """
        Export a conversation to a dictionary for backup/sharing
        
        Args:
            conversation_id: Conversation identifier
            
        Returns:
            Conversation data or None if not found
        """
        conversation = self.get_conversation(conversation_id)
        if conversation:
            return conversation.to_dict()
        
        return None
    
    def import_conversation(self, conversation_data: Dict) -> str:
        """
        Import a conversation from dictionary data
        
        Args:
            conversation_data: Conversation data
            
        Returns:
            conversation_id: Imported conversation identifier
        """
        conversation_id = str(uuid.uuid4())  # Generate new ID to avoid conflicts
        
        # Reconstruct messages
        messages = []
        for msg_data in conversation_data.get('messages', []):
            message = ChatMessage(
                role=msg_data['role'],
                content=msg_data['content'],
                timestamp=msg_data['timestamp'],
                message_id=msg_data.get('message_id', str(uuid.uuid4()))
            )
            messages.append(message)
        
        # Create conversation
        conversation = Conversation(
            conversation_id=conversation_id,
            messages=messages,
            created_at=conversation_data.get('created_at', time.time()),
            last_activity=conversation_data.get('last_activity', time.time()),
            title=conversation_data.get('title', 'Imported Conversation')
        )
        
        self.conversations[conversation_id] = conversation
        print(f"Imported conversation: {conversation_id}")
        return conversation_id


# Global chat manager instance
chat_manager = ChatManager()