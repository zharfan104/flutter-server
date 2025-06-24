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
    from src.utils.advanced_logger import logger, LogCategory
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
        
        # Current conversation ID for streaming
        self.currentConversationId = None
    
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
            
            # Store conversation ID for streaming methods
            self.currentConversationId = conversation_id
            
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
    
    async def handle_message_stream(self, request: ChatRequest):
        """
        Handle chat message with streaming progress updates
        
        Args:
            request: ChatRequest with message and context
            
        Yields:
            StreamProgress objects and chat responses during processing
        """
        from code_modification.llm_executor import StreamProgress
        
        try:
            request_id = str(uuid.uuid4())
            
            yield StreamProgress(
                stage="analyzing",
                message="Processing your message...",
                progress_percent=0.0,
                metadata={"request_id": request_id}
            )
            
            # Get or create conversation
            conversation_id = request.conversation_id
            if not conversation_id and self.chat_manager:
                conversation_id = self.chat_manager.get_or_create_default_conversation()
            elif not conversation_id:
                conversation_id = str(uuid.uuid4())
            
            # Store conversation ID for streaming methods
            self.currentConversationId = conversation_id
            
            yield StreamProgress(
                stage="analyzing",
                message="Understanding your request...",
                progress_percent=10.0
            )
            
            # Add user message to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'user', request.message)
            
            # Get conversation and project context
            conversation_history = self._get_conversation_context(conversation_id)
            project_context = self._get_project_context()
            
            yield StreamProgress(
                stage="analyzing",
                message="Classifying intent and analyzing context...",
                progress_percent=20.0
            )
            
            # Step 1: Classify intent and get immediate response
            classified_response = await intent_classifier.classify_message(
                message=request.message,
                conversation_history=conversation_history,
                project_context=project_context
            )
            
            yield StreamProgress(
                stage="analyzing",
                message=f"Detected intent: {classified_response.intent.value}",
                progress_percent=30.0,
                metadata={"intent": classified_response.intent.value}
            )
            
            # Step 2: Handle based on intent with streaming
            if classified_response.intent == ChatIntent.CODE_CHANGE:
                yield StreamProgress(
                    stage="generating",
                    message="Starting code modification...",
                    progress_percent=40.0
                )
                
                # Stream code modification process
                async for progress in self._handle_code_modification_stream(request, classified_response, request_id):
                    yield progress
                    
            elif classified_response.intent == ChatIntent.QUESTION:
                yield StreamProgress(
                    stage="generating",
                    message="Generating detailed response...",
                    progress_percent=50.0
                )
                
                # Stream question response generation
                async for progress in self._handle_question_stream(request, classified_response, conversation_history, project_context):
                    yield progress
                    
            elif classified_response.intent == ChatIntent.FOLLOW_UP:
                yield StreamProgress(
                    stage="generating",
                    message="Generating follow-up response...",
                    progress_percent=60.0
                )
                
                # Stream follow-up response generation
                async for progress in self._handle_followup_stream(request, classified_response, conversation_history, project_context):
                    yield progress
            
            # Send final chat response
            yield {
                "event_type": "chat_response",
                "message": classified_response.message,
                "conversation_id": conversation_id,
                "intent": classified_response.intent.value,
                "requires_code_modification": classified_response.intent == ChatIntent.CODE_CHANGE,
                "code_modification_request_id": request_id if classified_response.intent == ChatIntent.CODE_CHANGE else None,
                "metadata": {
                    "request_id": request_id,
                    "classification_confidence": classified_response.confidence
                }
            }
            
            # Add AI response to conversation
            if self.chat_manager:
                self.chat_manager.add_message(conversation_id, 'assistant', classified_response.message)
            
            yield StreamProgress(
                stage="complete",
                message="Chat response completed",
                progress_percent=100.0,
                metadata={"conversation_id": conversation_id}
            )
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"Error processing message: {str(e)}",
                progress_percent=0.0,
                metadata={"error": str(e)}
            )
    
    async def _handle_code_modification_stream(self, request: ChatRequest, classified_response, request_id: str):
        """Stream code modification process"""
        from code_modification.llm_executor import StreamProgress
        from code_modification.code_modifier import CodeModificationService, ModificationRequest
        
        try:
            yield StreamProgress(
                stage="generating",
                message="Initializing code modification service...",
                progress_percent=45.0
            )
            
            # Initialize code modification service
            if not self.flutter_manager:
                yield StreamProgress(
                    stage="error",
                    message="Flutter manager not available",
                    progress_percent=0.0
                )
                return
            
            code_modifier = CodeModificationService(str(self.flutter_manager.project_path))
            
            # Create modification request
            modification_request = ModificationRequest(
                description=request.message,
                user_id=request.user_id,
                request_id=request_id
            )
            
            yield StreamProgress(
                stage="generating",
                message="Starting code generation with AI...",
                progress_percent=50.0
            )
            
            # Stream the code modification process
            async for progress in code_modifier.modify_code_stream(modification_request):
                if hasattr(progress, 'to_dict'):
                    # Forward StreamProgress with chat context
                    progress.metadata = progress.metadata or {}
                    progress.metadata.update({
                        "chat_request_id": request_id,
                        "conversation_type": "code_modification"
                    })
                    yield progress
                elif isinstance(progress, dict):
                    # Forward result events
                    yield progress
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"Code modification failed: {str(e)}",
                progress_percent=0.0,
                metadata={"error": str(e)}
            )
    
    async def _handle_question_stream(self, request: ChatRequest, classified_response, conversation_history, project_context):
        """Stream question response generation"""
        from code_modification.llm_executor import StreamProgress
        
        yield StreamProgress(
            stage="generating",
            message="AI is thinking about your question...",
            progress_percent=60.0
        )
        
        # This could be enhanced to use streaming LLM for question responses
        yield StreamProgress(
            stage="generating",
            message="Generating detailed answer...",
            progress_percent=80.0
        )
        
        # For now, use the existing logic (could be enhanced with streaming)
        yield StreamProgress(
            stage="generating",
            message="Finalizing response...",
            progress_percent=90.0
        )
    
    async def _handle_followup_stream(self, request: ChatRequest, classified_response, conversation_history, project_context):
        """Stream follow-up response generation"""
        from code_modification.llm_executor import StreamProgress
        
        yield StreamProgress(
            stage="generating",
            message="Processing follow-up conversation...",
            progress_percent=70.0
        )
        
        # This could be enhanced to use streaming LLM for follow-up responses
        yield StreamProgress(
            stage="generating",
            message="Generating contextual response...",
            progress_percent=85.0
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
    
    async def _handle_question_stream(self, request: ChatRequest, classified_response, conversation_history, project_context):
        """Stream question response generation with real-time token streaming"""
        from code_modification.llm_executor import StreamProgress
        
        try:
            # Get the LLM executor from conversation handler
            llm_executor = conversation_handler.llm_executor
            
            # Prepare messages for streaming
            messages = conversation_handler._prepare_question_messages(
                request.message,
                conversation_history,
                project_context
            )
            
            accumulated_response = ""
            
            # Stream the LLM response
            async for chunk in llm_executor.execute_stream_with_progress(
                messages=messages,
                system_prompt=conversation_handler.system_prompt
            ):
                if isinstance(chunk, str):
                    # This is a text chunk - send it as streaming text
                    accumulated_response += chunk
                    yield {
                        "event_type": "text",
                        "text": chunk,
                        "accumulated": accumulated_response
                    }
                elif hasattr(chunk, 'stage'):
                    # This is a StreamProgress object
                    yield chunk
            
            # Send the complete response with proper intent
            yield {
                "event_type": "chat_response",
                "message": accumulated_response,
                "conversation_id": request.conversation_id,
                "intent": "question",
                "metadata": {
                    "streamed": True,
                    "token_count": len(accumulated_response.split())
                }
            }
            
            # Add to conversation history
            if self.chat_manager and accumulated_response:
                self.chat_manager.add_message(
                    request.conversation_id or self.currentConversationId, 
                    'assistant', 
                    accumulated_response
                )
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"Error generating response: {str(e)}",
                progress_percent=0.0,
                metadata={"error": str(e)}
            )
    
    async def _handle_followup_stream(self, request: ChatRequest, classified_response, conversation_history, project_context):
        """Stream follow-up response generation with real-time token streaming"""
        from code_modification.llm_executor import StreamProgress
        
        try:
            # Get the LLM executor from conversation handler
            llm_executor = conversation_handler.llm_executor
            
            # Prepare messages for streaming
            messages = conversation_handler._prepare_followup_messages(
                request.message,
                conversation_history,
                project_context
            )
            
            accumulated_response = ""
            
            # Stream the LLM response
            async for chunk in llm_executor.execute_stream_with_progress(
                messages=messages,
                system_prompt=conversation_handler.system_prompt
            ):
                if isinstance(chunk, str):
                    # This is a text chunk - send it as streaming text
                    accumulated_response += chunk
                    yield {
                        "event_type": "text",
                        "text": chunk,
                        "accumulated": accumulated_response
                    }
                elif hasattr(chunk, 'stage'):
                    # This is a StreamProgress object
                    yield chunk
            
            # Send the complete response
            yield {
                "event_type": "chat_response",
                "message": accumulated_response,
                "conversation_id": request.conversation_id,
                "intent": "follow_up",
                "metadata": {
                    "streamed": True,
                    "token_count": len(accumulated_response.split())
                }
            }
            
            # Add to conversation history
            if self.chat_manager and accumulated_response:
                self.chat_manager.add_message(
                    request.conversation_id or self.currentConversationId,
                    'assistant',
                    accumulated_response
                )
            
        except Exception as e:
            yield StreamProgress(
                stage="error",
                message=f"Error generating follow-up response: {str(e)}",
                progress_percent=0.0,
                metadata={"error": str(e)}
            )
    
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