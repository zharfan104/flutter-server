"""
Main Chat Service for Flutter Development Server
Orchestrates intent classification, conversation handling, and code modifications
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from dataclasses import dataclass

from .intent_classifier import intent_classifier, ChatIntent, ClassifiedResponse
from .conversation_handler import conversation_handler, ConversationResponse

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@dataclass
class ChatRequest:
    """Chat request container"""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ChatResponse:
    """Chat response container"""
    message: str
    conversation_id: str
    intent: ChatIntent
    requires_code_modification: bool = False
    code_modification_request_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatService:
    """
    Main chat orchestration service
    
    Coordinates between:
    - Intent classification
    - Conversational responses
    - Code modification requests
    - Data persistence
    """
    
    def __init__(self, flutter_manager=None, chat_manager=None):
        self.flutter_manager = flutter_manager
        self.chat_manager = chat_manager
        
        # Background task tracking
        self.active_code_modifications = {}
    
    def set_dependencies(self, flutter_manager=None, chat_manager=None):
        """Set dependencies after initialization"""
        if flutter_manager:
            self.flutter_manager = flutter_manager
        if chat_manager:
            self.chat_manager = chat_manager
    
    async def handle_message(self, request: ChatRequest) -> ChatResponse:
        """
        Main entry point for handling chat messages
        
        Args:
            request: ChatRequest with message and context
            
        Returns:
            ChatResponse with immediate response and potential background actions
        """
        try:
            request_id = str(uuid.uuid4())
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, f"Handling chat message [req:{request_id[:8]}]: {request.message[:100]}...")
            
            # Get or create conversation
            conversation_id = request.conversation_id
            if not conversation_id and self.chat_manager:
                conversation_id = self.chat_manager.get_or_create_default_conversation()
            elif not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # Add user message to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'user', request.message)
            
            # Get conversation and project context
            conversation_history = self._get_conversation_context(conversation_id)
            project_context = self._get_project_context()
            
            # Step 1: Classify intent and get immediate response
            classified_response = await intent_classifier.classify_message(
                message=request.message,
                conversation_history=conversation_history,
                project_context=project_context
            )
            
            # Step 2: Handle based on intent
            chat_response = ChatResponse(
                message=classified_response.message,
                conversation_id=conversation_id,
                intent=classified_response.intent,
                metadata={
                    "request_id": request_id,
                    "classification_confidence": classified_response.confidence,
                    "classification_metadata": classified_response.metadata
                }
            )
            
            if classified_response.intent == ChatIntent.CODE_CHANGE:
                # Handle code modification intent
                chat_response = await self._handle_code_modification_intent(
                    request, classified_response, chat_response, request_id
                )
                
            elif classified_response.intent == ChatIntent.QUESTION:
                # Handle question intent with detailed response
                chat_response = await self._handle_question_intent(
                    request, classified_response, chat_response,
                    conversation_history, project_context
                )
                
            elif classified_response.intent == ChatIntent.FOLLOW_UP:
                # Handle follow-up conversation
                chat_response = await self._handle_followup_intent(
                    request, classified_response, chat_response,
                    conversation_history, project_context
                )
            
            # Add AI response to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'assistant', chat_response.message)
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CHAT, f"Chat message handled successfully [req:{request_id[:8]}] - Intent: {classified_response.intent.value}")
            
            return chat_response
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CHAT, f"Error handling chat message: {e}")
            
            # Return error response
            return ChatResponse(
                message=f"I'm sorry, I encountered an error processing your message: {str(e)}",
                conversation_id=conversation_id or str(uuid.uuid4()),
                intent=ChatIntent.FOLLOW_UP,
                metadata={"error": str(e)}
            )
    
    async def _handle_code_modification_intent(
        self, 
        request: ChatRequest, 
        classified_response: ClassifiedResponse, 
        chat_response: ChatResponse,
        request_id: str
    ) -> ChatResponse:
        """Handle code modification intent"""
        
        # Set code modification flags
        chat_response.requires_code_modification = True
        chat_response.code_modification_request_id = request_id
        
        # Start background code modification in a separate thread
        import threading
        
        def run_background_modification():
            # Create a new event loop for this thread
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._execute_code_modification_background(
                    message=request.message,
                    conversation_id=chat_response.conversation_id,
                    request_id=request_id
                ))
            finally:
                loop.close()
        
        background_thread = threading.Thread(target=run_background_modification, daemon=True)
        background_thread.start()
        
        # Track active modification
        self.active_code_modifications[request_id] = {
            "conversation_id": chat_response.conversation_id,
            "original_message": request.message,
            "status": "started"
        }
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.CODE_MOD, f"Code modification started [req:{request_id[:8]}]: {request.message[:100]}...")
        
        return chat_response
    
    async def _handle_question_intent(
        self,
        request: ChatRequest,
        classified_response: ClassifiedResponse,
        chat_response: ChatResponse,
        conversation_history: Optional[str],
        project_context: Optional[str]
    ) -> ChatResponse:
        """Handle question intent with detailed conversational response"""
        
        # Get detailed conversational response
        conversation_response = await conversation_handler.handle_question(
            message=request.message,
            conversation_history=conversation_history,
            project_context=project_context
        )
        
        # Update chat response with detailed answer
        chat_response.message = conversation_response.content
        if conversation_response.metadata:
            chat_response.metadata.update(conversation_response.metadata)
        
        return chat_response
    
    async def _handle_followup_intent(
        self,
        request: ChatRequest,
        classified_response: ClassifiedResponse,
        chat_response: ChatResponse,
        conversation_history: Optional[str],
        project_context: Optional[str]
    ) -> ChatResponse:
        """Handle follow-up conversation intent"""
        
        # Get conversational follow-up response
        conversation_response = await conversation_handler.handle_followup(
            message=request.message,
            conversation_history=conversation_history,
            project_context=project_context
        )
        
        # Update chat response with conversational reply
        chat_response.message = conversation_response.content
        if conversation_response.metadata:
            chat_response.metadata.update(conversation_response.metadata)
        
        return chat_response
    
    async def _execute_code_modification_background(
        self, 
        message: str, 
        conversation_id: str, 
        request_id: str
    ):
        """Execute code modification in background"""
        try:
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.CODE_MOD, f"Starting background code modification [req:{request_id[:8]}]")
            
            # Update status
            if request_id in self.active_code_modifications:
                self.active_code_modifications[request_id]["status"] = "processing"
            
            # Import and execute code modification
            from code_modification.code_modifier import CodeModificationService, ModificationRequest
            
            if not self.flutter_manager:
                raise Exception("Flutter manager not available for code modifications")
            
            modifier = CodeModificationService(self.flutter_manager.project_path)
            
            mod_request = ModificationRequest(
                description=message,
                request_id=request_id
            )
            
            # Execute modification
            mod_result = await modifier.modify_code(mod_request)
            
            # Prepare result message
            if mod_result.success:
                result_message = f"🎉 Code modification completed!\n\n"
                result_message += f"**Changes:** {mod_result.changes_summary}\n\n"
                
                if mod_result.modified_files:
                    result_message += f"**Modified Files:** {', '.join(mod_result.modified_files)}\n"
                if mod_result.created_files:
                    result_message += f"**Created Files:** {', '.join(mod_result.created_files)}\n"
                if mod_result.deleted_files:
                    result_message += f"**Deleted Files:** {', '.join(mod_result.deleted_files)}\n"
                
                if self.flutter_manager and self.flutter_manager.is_running:
                    # Set up recovery chat context
                    if self.chat_manager:
                        self.flutter_manager.set_recovery_chat_context(self.chat_manager, conversation_id)
                    
                    # Trigger hot reload with error recovery
                    hot_reload_result = self.flutter_manager.hot_reload(with_error_recovery=True, max_retries=3)
                    
                    if hot_reload_result.get("success"):
                        if hot_reload_result.get("status") == "error_recovery_success":
                            result_message += f"\n🔄 Hot reload succeeded after error recovery ({hot_reload_result.get('attempts', 1)} attempts)"
                            result_message += f"\n🤖 AI fixed: {hot_reload_result.get('fix_applied', 'compilation errors')}"
                        else:
                            result_message += "\n🔄 Hot reload triggered - changes are live!"
                    else:
                        if hot_reload_result.get("status") == "error_recovery_failed":
                            result_message += f"\n❌ Hot reload failed after {hot_reload_result.get('attempts', 3)} error recovery attempts"
                            result_message += f"\n🔧 Manual intervention may be required"
                            
                            # Send additional error recovery message
                            if self.chat_manager:
                                error_recovery_message = f"⚠️ **Error Recovery Failed**\n\n"
                                error_recovery_message += f"Despite {hot_reload_result.get('attempts', 3)} AI recovery attempts, compilation errors persist:\n\n"
                                error_recovery_message += f"```\n{hot_reload_result.get('final_error', 'Unknown error')}\n```\n\n"
                                error_recovery_message += "Please review the errors and ask me to fix specific issues."
                                self.chat_manager.add_message(conversation_id, 'assistant', error_recovery_message)
                        else:
                            result_message += f"\n❌ Hot reload failed: {hot_reload_result.get('error', 'Unknown error')}"
                else:
                    result_message += "\nℹ️ Start your Flutter server to see the changes."
                
                if MONITORING_AVAILABLE:
                    logger.info(LogCategory.CODE_MOD, f"Code modification completed successfully [req:{request_id[:8]}]")
            else:
                result_message = f"❌ Code modification encountered issues:\n\n"
                if mod_result.errors:
                    result_message += f"**Errors:** {', '.join(mod_result.errors)}\n\n"
                result_message += "The code may have been partially modified. Please check your project files."
                
                if MONITORING_AVAILABLE:
                    logger.warn(LogCategory.CODE_MOD, f"Code modification failed [req:{request_id[:8]}]: {', '.join(mod_result.errors)}")
            
            # Add result message to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'assistant', result_message)
            
            # Update status
            if request_id in self.active_code_modifications:
                self.active_code_modifications[request_id]["status"] = "completed"
                self.active_code_modifications[request_id]["result"] = mod_result
            
        except Exception as e:
            error_message = f"❌ Code modification failed: {str(e)}"
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.CODE_MOD, f"Background code modification error [req:{request_id[:8]}]: {e}")
            
            # Add error message to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'assistant', error_message)
            
            # Update status
            if request_id in self.active_code_modifications:
                self.active_code_modifications[request_id]["status"] = "failed"
                self.active_code_modifications[request_id]["error"] = str(e)
    
    def _get_conversation_context(self, conversation_id: str) -> Optional[str]:
        """Get recent conversation context"""
        if not self.chat_manager:
            return None
        
        try:
            recent_messages = self.chat_manager.get_messages(conversation_id, limit=10)
            context = ""
            for msg in recent_messages[-5:]:  # Last 5 messages
                context += f"{msg.role.title()}: {msg.content}\n\n"
            return context.strip()
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.CHAT, f"Failed to get conversation context: {e}")
            return None
    
    def _get_project_context(self) -> Optional[str]:
        """Get current Flutter project context"""
        if not self.flutter_manager:
            return None
        
        try:
            from code_modification.project_analyzer import FlutterProjectAnalyzer
            analyzer = FlutterProjectAnalyzer(self.flutter_manager.project_path)
            project_summary = analyzer.generate_project_summary()
            
            # Create concise context
            context = f"Flutter Project: {project_summary.get('project_name', 'Unknown')}\n"
            context += f"Dependencies: {len(project_summary.get('dependencies', []))}\n"
            context += f"Dart Files: {len(project_summary.get('dart_files', []))}\n"
            
            if project_summary.get('architecture_pattern'):
                context += f"Architecture: {project_summary['architecture_pattern']}\n"
            
            return context
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.CHAT, f"Failed to get project context: {e}")
            return None
    
    def get_modification_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get status of active code modification"""
        return self.active_code_modifications.get(request_id)
    
    def get_active_modifications(self) -> Dict[str, Dict[str, Any]]:
        """Get all active code modifications"""
        return self.active_code_modifications.copy()


# Global instance
chat_service = ChatService()