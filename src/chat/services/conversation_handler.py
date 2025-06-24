"""
Conversation Handler for Flutter Development Chat
Handles pure conversational interactions (QUESTION and FOLLOW_UP intents)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@dataclass
class ConversationResponse:
    """Response from conversation handler"""
    content: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationHandler:
    """
    Handles conversational interactions that don't require code modifications
    Focuses on providing helpful Flutter development guidance and information
    """
    
    def __init__(self):
        self.conversation_system_prompt = self._build_conversation_prompt()
        self.system_prompt = self.conversation_system_prompt  # Alias for compatibility
        self._llm_executor = None  # Lazy initialize
    
    @property
    def llm_executor(self):
        """Get or create LLM executor instance"""
        if self._llm_executor is None:
            from code_modification.llm_executor import SimpleLLMExecutor
            self._llm_executor = SimpleLLMExecutor()
        return self._llm_executor
    
    def _build_conversation_prompt(self) -> str:
        """Build the system prompt for conversational responses"""
        return """You are an expert Flutter development assistant providing helpful guidance and information.

Your role is to:
- Answer Flutter development questions with practical, actionable advice
- Provide code examples and explanations when helpful
- Recommend best practices and popular packages
- Help debug issues by asking clarifying questions
- Be encouraging and supportive in follow-up conversations

**Guidelines:**
- Be concise but thorough
- Focus on practical Flutter development advice
- Include code examples when relevant (use proper Dart/Flutter syntax)
- Mention specific packages or tools when appropriate
- Ask follow-up questions if more context would be helpful
- For follow-up conversations, be natural and encouraging

**Current Context:**
- This is a Flutter development environment with hot reload capabilities
- The user has access to code modification features
- Focus on Flutter 3.x best practices and modern approaches

Be helpful, practical, and encouraging. If you need more information to provide better guidance, ask specific questions."""
    
    async def handle_question(
        self,
        message: str,
        conversation_history: Optional[str] = None,
        project_context: Optional[str] = None
    ) -> ConversationResponse:
        """
        Handle a question-type message
        
        Args:
            message: User's question
            conversation_history: Recent conversation context
            project_context: Current Flutter project context
            
        Returns:
            ConversationResponse with helpful guidance
        """
        try:
            from code_modification.llm_executor import SimpleLLMExecutor
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, f"Handling question: {message[:100]}...")
            
            # Initialize LLM executor
            llm_executor = SimpleLLMExecutor()
            if not llm_executor.is_available():
                return self._fallback_question_response(message)
            
            # Build enhanced prompt with context
            enhanced_prompt = self.conversation_system_prompt
            
            if project_context:
                enhanced_prompt += f"\n\n**Current Project Context:**\n{project_context}"
            
            if conversation_history:
                enhanced_prompt += f"\n\n**Recent Conversation:**\n{conversation_history}"
            
            # Prepare messages for LLM
            messages = [
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            # Execute conversation
            response = llm_executor.execute(
                messages=messages,
                system_prompt=enhanced_prompt
            )
            
            conversation_response = ConversationResponse(
                content=response.text.strip(),
                metadata={
                    "token_usage": response.usage.__dict__ if response.usage else None,
                    "model": response.model
                }
            )
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, "Question handled successfully")
            
            return conversation_response
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CHAT, f"Error handling question: {e}")
            
            return self._fallback_question_response(message)
    
    async def handle_followup(
        self,
        message: str,
        conversation_history: Optional[str] = None,
        project_context: Optional[str] = None
    ) -> ConversationResponse:
        """
        Handle a follow-up conversation message
        
        Args:
            message: User's follow-up message
            conversation_history: Recent conversation context
            project_context: Current Flutter project context
            
        Returns:
            ConversationResponse with natural conversational reply
        """
        try:
            from code_modification.llm_executor import SimpleLLMExecutor
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, f"Handling follow-up: {message[:100]}...")
            
            # Initialize LLM executor
            llm_executor = SimpleLLMExecutor()
            if not llm_executor.is_available():
                return self._fallback_followup_response(message)
            
            # Build enhanced prompt for natural conversation
            followup_prompt = """You are a friendly Flutter development assistant having a natural conversation.

The user is engaging in casual conversation or follow-up comments. Respond naturally and encouragingly.

Guidelines:
- Be conversational and friendly
- Keep responses concise unless more detail is requested
- Stay focused on Flutter development context
- Be encouraging and supportive
- If the user seems to want to continue working, gently guide them toward their next steps

Recent conversation context will help you respond appropriately."""
            
            if project_context:
                followup_prompt += f"\n\n**Current Project Context:**\n{project_context}"
            
            if conversation_history:
                followup_prompt += f"\n\n**Recent Conversation:**\n{conversation_history}"
            
            # Prepare messages for LLM
            messages = [
                {
                    "role": "user",
                    "content": message
                }
            ]
            
            # Execute conversation
            response = llm_executor.execute(
                messages=messages,
                system_prompt=followup_prompt
            )
            
            conversation_response = ConversationResponse(
                content=response.text.strip(),
                metadata={
                    "token_usage": response.usage.__dict__ if response.usage else None,
                    "model": response.model
                }
            )
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, "Follow-up handled successfully")
            
            return conversation_response
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CHAT, f"Error handling follow-up: {e}")
            
            return self._fallback_followup_response(message)
    
    def _fallback_question_response(self, message: str) -> ConversationResponse:
        """Fallback response when LLM is unavailable for questions"""
        message_lower = message.lower()
        
        # Common Flutter topics with fallback responses
        if 'state management' in message_lower or 'provider' in message_lower:
            return ConversationResponse(
                content="For state management in Flutter, I recommend starting with Provider or Riverpod. Provider is simpler for beginners, while Riverpod offers more advanced features. Both help you manage app state efficiently and trigger UI rebuilds when data changes."
            )
        
        if 'navigation' in message_lower or 'route' in message_lower:
            return ConversationResponse(
                content="Flutter navigation uses Navigator.push() and Navigator.pop() for basic routing. For complex apps, consider using named routes or packages like GoRouter for type-safe navigation. The Navigator 2.0 API offers more control for advanced use cases."
            )
        
        if 'widget' in message_lower or 'ui' in message_lower:
            return ConversationResponse(
                content="Flutter uses a widget tree to build UI. StatelessWidget for static content, StatefulWidget for dynamic content. Remember: everything is a widget! Use Container for styling, Column/Row for layout, and ListView for scrollable lists."
            )
        
        if 'performance' in message_lower or 'optimization' in message_lower:
            return ConversationResponse(
                content="For Flutter performance: use const constructors when possible, avoid rebuilding large widget trees, use ListView.builder for long lists, and consider using keys for widget identity. The Flutter Inspector helps identify performance bottlenecks."
            )
        
        # Generic fallback
        return ConversationResponse(
            content=f"That's a great question about Flutter development! While I don't have a specific answer ready, I'd recommend checking the Flutter documentation or asking for more specific details so I can provide better guidance."
        )
    
    def _prepare_question_messages(
        self,
        message: str,
        conversation_history: Optional[str] = None,
        project_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare messages for question handling"""
        # Build enhanced prompt with context
        enhanced_prompt = self.conversation_system_prompt
        
        if project_context:
            enhanced_prompt += f"\n\n**Current Project Context:**\n{project_context}"
        
        if conversation_history:
            enhanced_prompt += f"\n\n**Recent Conversation:**\n{conversation_history}"
        
        # Note: The system prompt will be passed separately to the LLM executor
        # So we just return the user message here
        return [
            {
                "role": "user",
                "content": message
            }
        ]
    
    def _prepare_followup_messages(
        self,
        message: str,
        conversation_history: Optional[str] = None,
        project_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Prepare messages for follow-up handling"""
        # For follow-ups, we want a more conversational tone
        followup_prompt = """You are continuing a friendly Flutter development conversation.
        
Be natural, encouraging, and helpful. If the user is:
- Thanking you: Be gracious and offer continued support
- Expressing satisfaction: Celebrate with them and encourage their progress
- Asking clarification: Provide clear, helpful explanations
- Saying goodbye: Be warm and invite them back

Keep responses conversational and supportive."""
        
        if project_context:
            followup_prompt += f"\n\n**Current Project Context:**\n{project_context}"
        
        if conversation_history:
            followup_prompt += f"\n\n**Recent Conversation:**\n{conversation_history}"
        
        # Update the system prompt for follow-ups
        self.system_prompt = followup_prompt
        
        return [
            {
                "role": "user",
                "content": message
            }
        ]
    
    def _fallback_followup_response(self, message: str) -> ConversationResponse:
        """Fallback response when LLM is unavailable for follow-ups"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['thank', 'thanks']):
            return ConversationResponse(
                content="You're very welcome! Happy Flutter coding! Let me know if you need help with anything else."
            )
        
        if any(word in message_lower for word in ['great', 'awesome', 'perfect', 'good']):
            return ConversationResponse(
                content="Glad to hear it! I'm here whenever you need help with your Flutter development."
            )
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey']):
            return ConversationResponse(
                content="Hello! I'm here to help with your Flutter development. What would you like to work on today?"
            )
        
        if any(word in message_lower for word in ['bye', 'goodbye', 'see you']):
            return ConversationResponse(
                content="Goodbye! Happy coding, and feel free to come back anytime you need Flutter help!"
            )
        
        # Generic friendly response
        return ConversationResponse(
            content="I'm here to help with your Flutter development! Feel free to ask any questions or let me know what you'd like to work on."
        )


# Global instance
conversation_handler = ConversationHandler()