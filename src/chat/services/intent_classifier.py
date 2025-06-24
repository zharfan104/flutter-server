"""
Intent Classification Service for Flutter Development Chat
Classifies user messages into CODE_CHANGE, QUESTION, or FOLLOW_UP intents
"""

import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class ChatIntent(Enum):
    """Chat intent types"""
    CODE_CHANGE = "CODE_CHANGE"
    QUESTION = "QUESTION"
    FOLLOW_UP = "FOLLOW_UP"


@dataclass
class ClassifiedResponse:
    """Classified chat response"""
    intent: ChatIntent
    message: str
    confidence: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


class IntentClassifier:
    """
    Classifies user chat messages into different intents and provides appropriate responses
    """
    
    def __init__(self):
        self.classification_system_prompt = self._build_classification_prompt()
    
    def _build_classification_prompt(self) -> str:
        """Build the system prompt for intent classification"""
        return """You are an expert Flutter development assistant that classifies user requests and provides appropriate responses.

Your task is to:
1. Classify the user's message into one of three intents: CODE_CHANGE, QUESTION, or FOLLOW_UP
2. Provide an appropriate response message
3. Return the result as valid JSON

**Intent Types:**

**CODE_CHANGE**: User wants to modify, add, create, or change code/files
- Examples: "Add a login button", "Create a new screen", "Fix the navigation", "Update the theme"
- Response: Acknowledge what you'll do (e.g., "I'll add a login button to your app!")

**QUESTION**: User asks for information, help, or guidance without wanting immediate code changes
- Examples: "How do I use Provider?", "What's the best way to handle state?", "Explain BLoC pattern"
- Response: Provide helpful information and guidance

**FOLLOW_UP**: Casual conversation, thanks, greetings, or follow-up comments
- Examples: "Thanks!", "Hello", "That's great!", "Can you explain more about..."
- Response: Natural conversational response

**CRITICAL**: Always respond with valid JSON in this exact format:
{
  "intent": "CODE_CHANGE|QUESTION|FOLLOW_UP",
  "message": "your response message here"
}

Be concise but helpful. For CODE_CHANGE intents, be specific about what you'll do. For QUESTION intents, provide practical Flutter-focused guidance. For FOLLOW_UP intents, be natural and encouraging."""
    
    async def classify_message(
        self, 
        message: str, 
        conversation_history: Optional[str] = None,
        project_context: Optional[str] = None
    ) -> ClassifiedResponse:
        """
        Classify a user message and generate appropriate response
        
        Args:
            message: User's message to classify
            conversation_history: Recent conversation context
            project_context: Current Flutter project context
            
        Returns:
            ClassifiedResponse with intent, message, and metadata
        """
        try:
            from code_modification.llm_executor import SimpleLLMExecutor
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, f"Classifying message: {message[:100]}...")
            
            # Initialize LLM executor
            llm_executor = SimpleLLMExecutor()
            if not llm_executor.is_available():
                # Fallback classification without LLM
                return self._fallback_classification(message)
            
            # Build enhanced prompt with context
            enhanced_prompt = self.classification_system_prompt
            
            if project_context:
                enhanced_prompt += f"\n\n**Current Project Context:**\n{project_context}"
            
            if conversation_history:
                enhanced_prompt += f"\n\n**Recent Conversation:**\n{conversation_history}"
            
            # Prepare messages for LLM
            messages = [
                {
                    "role": "user", 
                    "content": f"Classify this message and respond appropriately:\n\n\"{message}\""
                }
            ]
            
            # Execute classification
            response = llm_executor.execute(
                messages=messages,
                system_prompt=enhanced_prompt
            )
            
            # Parse JSON response
            try:
                result = json.loads(response.text.strip())
                intent_str = result.get("intent", "QUESTION")
                response_message = result.get("message", "I'm here to help with your Flutter development!")
                
                # Validate intent
                try:
                    intent = ChatIntent(intent_str)
                except ValueError:
                    intent = ChatIntent.QUESTION
                
                classified_response = ClassifiedResponse(
                    intent=intent,
                    message=response_message,
                    confidence=0.9,
                    metadata={
                        "raw_response": response.text,
                        "token_usage": response.usage.__dict__ if response.usage else None
                    }
                )
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.CHAT, f"Message classified as {intent.value}")
                
                return classified_response
                
            except json.JSONDecodeError as e:
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.CHAT, f"Failed to parse LLM JSON response: {e}")
                
                # Try to extract intent and message from malformed response
                return self._extract_from_malformed_response(response.text, message)
                
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CHAT, f"Error in intent classification: {e}")
            
            # Fallback to rule-based classification
            return self._fallback_classification(message)
    
    def _fallback_classification(self, message: str) -> ClassifiedResponse:
        """Fallback rule-based classification when LLM is unavailable"""
        message_lower = message.lower()
        
        # Code change keywords
        code_keywords = [
            'add', 'create', 'make', 'build', 'implement', 'modify', 'change', 
            'update', 'fix', 'remove', 'delete', 'refactor', 'generate'
        ]
        
        # Question keywords
        question_keywords = [
            'how', 'what', 'why', 'when', 'where', 'which', 'explain', 
            'tell me', 'show me', 'help me understand', '?'
        ]
        
        # Follow-up keywords
        followup_keywords = [
            'thanks', 'thank you', 'hello', 'hi', 'bye', 'goodbye', 
            'ok', 'okay', 'great', 'awesome', 'perfect', 'nice'
        ]
        
        # Check for code change intent
        if any(keyword in message_lower for keyword in code_keywords):
            return ClassifiedResponse(
                intent=ChatIntent.CODE_CHANGE,
                message=f"I'll help you with that change! Let me work on implementing: {message}",
                confidence=0.7
            )
        
        # Check for question intent
        if any(keyword in message_lower for keyword in question_keywords):
            return ClassifiedResponse(
                intent=ChatIntent.QUESTION,
                message="I'd be happy to help explain that! Let me provide some guidance.",
                confidence=0.7
            )
        
        # Check for follow-up intent
        if any(keyword in message_lower for keyword in followup_keywords):
            return ClassifiedResponse(
                intent=ChatIntent.FOLLOW_UP,
                message="You're welcome! I'm here to help with your Flutter development.",
                confidence=0.7
            )
        
        # Default to question if uncertain
        return ClassifiedResponse(
            intent=ChatIntent.QUESTION,
            message="I'm here to help with your Flutter development! Could you provide more details about what you'd like to do?",
            confidence=0.5
        )
    
    def _extract_from_malformed_response(self, response_text: str, original_message: str) -> ClassifiedResponse:
        """Try to extract intent and message from malformed LLM response"""
        response_lower = response_text.lower()
        
        # Look for intent keywords in response
        if 'code_change' in response_lower:
            intent = ChatIntent.CODE_CHANGE
        elif 'question' in response_lower:
            intent = ChatIntent.QUESTION
        elif 'follow_up' in response_lower:
            intent = ChatIntent.FOLLOW_UP
        else:
            # Fallback to rule-based
            return self._fallback_classification(original_message)
        
        # Try to extract message part
        lines = response_text.split('\n')
        message = None
        for line in lines:
            if '"message"' in line.lower() or 'message:' in line.lower():
                # Try to extract the message value
                if ':' in line:
                    message = line.split(':', 1)[1].strip().strip('"\'')
                    break
        
        if not message:
            message = "I'll help you with that!"
        
        return ClassifiedResponse(
            intent=intent,
            message=message,
            confidence=0.6,
            metadata={"malformed_response": response_text}
        )


# Global instance
intent_classifier = IntentClassifier()