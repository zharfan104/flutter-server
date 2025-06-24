"""
Chat Router

API endpoints for AI chat functionality
"""

from flask import Blueprint, jsonify, request, Response
import uuid
import asyncio
import json
from typing import Optional

# Create blueprint for chat routes
chat_bp = Blueprint('chat', __name__, url_prefix='/api/chat')

# Dependencies will be injected
flutter_manager = None
chat_manager = None


def set_dependencies(**services):
    """Standardized dependency injection"""
    global flutter_manager, chat_manager
    if 'flutter_manager' in services:
        flutter_manager = services['flutter_manager']
    if 'chat_manager' in services:
        chat_manager = services['chat_manager']


@chat_bp.route('/send', methods=['POST'])
def send_message():
    """Send a message to AI chat and get response"""
    try:
        from .services.chat_service import chat_service, ChatRequest
        
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if not flutter_manager or not chat_manager:
            return jsonify({"error": "Required services not available"}), 500
        
        # Set dependencies if not already set
        chat_service.set_dependencies(flutter_manager=flutter_manager, chat_manager=chat_manager)
        
        # Create chat request
        chat_request = ChatRequest(
            message=message,
            conversation_id=conversation_id
        )
        
        # Handle the message using the modular chat service
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            chat_response = loop.run_until_complete(chat_service.handle_message(chat_request))
        finally:
            loop.close()
        
        # Return immediate response with intent information
        response_data = {
            "status": "success",
            "conversation_id": chat_response.conversation_id,
            "message": chat_response.message,
            "intent": chat_response.intent.value,
            "requires_code_modification": chat_response.requires_code_modification
        }
        
        if chat_response.code_modification_request_id:
            response_data["code_modification_request_id"] = chat_response.code_modification_request_id
        
        if chat_response.metadata:
            response_data["metadata"] = chat_response.metadata
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500


@chat_bp.route('/stream', methods=['POST'])
def chat_stream():
    """Stream chat responses using Server-Sent Events"""
    try:
        from .services.chat_service import ChatService, ChatRequest
        
        data = request.json
        message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        user_id = data.get('user_id', 'anonymous')
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        if not flutter_manager or not chat_manager:
            return jsonify({"error": "Required services not available"}), 500
        
        def generate_chat_sse_stream():
            """Generator function for chat SSE stream"""
            try:
                # Send initial connection event
                yield f"event: connected\\ndata: {json.dumps({'message': 'Connected to chat stream'})}\\n\\n"
                
                # Initialize chat service
                chat_service = ChatService(flutter_manager, chat_manager)
                
                # Create chat request
                chat_request = ChatRequest(
                    message=message,
                    conversation_id=conversation_id,
                    user_id=user_id
                )
                
                # Create async event loop for streaming
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_chat():
                    try:
                        # Check if streaming method exists
                        if hasattr(chat_service, 'handle_message_stream'):
                            async for event in chat_service.handle_message_stream(chat_request):
                                if hasattr(event, 'to_dict'):
                                    # StreamProgress object
                                    yield f"event: progress\\ndata: {json.dumps(event.to_dict())}\\n\\n"
                                elif isinstance(event, dict):
                                    # Chat response or status update
                                    event_type = event.get('event_type', 'chat')
                                    yield f"event: {event_type}\\ndata: {json.dumps(event)}\\n\\n"
                                elif isinstance(event, str):
                                    # Text chunk
                                    yield f"event: text\\ndata: {json.dumps({'text': event})}\\n\\n"
                        else:
                            # Fallback to synchronous chat
                            result = await chat_service.handle_message(chat_request)
                            if hasattr(result, 'to_dict'):
                                result_dict = result.to_dict()
                            else:
                                result_dict = result
                            yield f"event: complete\\ndata: {json.dumps(result_dict)}\\n\\n"
                    
                    except Exception as e:
                        error_data = {
                            'error': str(e),
                            'stage': 'error',
                            'message': f'Chat streaming failed: {str(e)}'
                        }
                        yield f"event: error\\ndata: {json.dumps(error_data)}\\n\\n"
                    
                    finally:
                        # Send completion event
                        yield f"event: complete\\ndata: {json.dumps({'message': 'Chat stream ended'})}\\n\\n"
                
                # Run the async streaming
                async_gen = stream_chat()
                
                try:
                    while True:
                        chunk = loop.run_until_complete(async_gen.__anext__())
                        yield chunk
                except StopAsyncIteration:
                    pass
                finally:
                    loop.close()
                    
            except Exception as e:
                error_data = {
                    'error': str(e),
                    'stage': 'error',
                    'message': f'Failed to start chat streaming: {str(e)}'
                }
                yield f"event: error\\ndata: {json.dumps(error_data)}\\n\\n"
        
        # Return SSE response
        return Response(
            generate_chat_sse_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to start chat streaming: {str(e)}"}), 500


@chat_bp.route('/history', methods=['GET'])
def get_history():
    """Get conversation history"""
    try:
        if not chat_manager:
            return jsonify({"error": "Chat manager not available"}), 500
        
        conversation_id = request.args.get('conversation_id')
        limit = request.args.get('limit', type=int)
        
        if not conversation_id:
            conversation_id = chat_manager.get_or_create_default_conversation()
        
        messages = chat_manager.get_messages(conversation_id, limit=limit)
        
        return jsonify({
            "status": "success",
            "conversation_id": conversation_id,
            "messages": [msg.to_dict() for msg in messages]
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to get history: {str(e)}"}), 500


@chat_bp.route('/new', methods=['POST'])
def new_conversation():
    """Create a new conversation"""
    try:
        if not chat_manager:
            return jsonify({"error": "Chat manager not available"}), 500
        
        data = request.json or {}
        title = data.get('title', 'New Conversation')
        
        conversation_id = chat_manager.create_conversation(title)
        
        return jsonify({
            "status": "success",
            "conversation_id": conversation_id,
            "message": "New conversation created"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to create conversation: {str(e)}"}), 500


@chat_bp.route('/conversations', methods=['GET'])
def list_conversations():
    """Get list of all conversations"""
    try:
        if not chat_manager:
            return jsonify({"error": "Chat manager not available"}), 500
        
        conversations = chat_manager.get_conversation_list()
        stats = chat_manager.get_stats()
        
        return jsonify({
            "status": "success",
            "conversations": conversations,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to list conversations: {str(e)}"}), 500


@chat_bp.route('/conversation/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        if not chat_manager:
            return jsonify({"error": "Chat manager not available"}), 500
        
        success = chat_manager.delete_conversation(conversation_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Conversation deleted"
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500


@chat_bp.route('/conversation/<conversation_id>/clear', methods=['POST'])
def clear_conversation(conversation_id):
    """Clear all messages from a conversation"""
    try:
        if not chat_manager:
            return jsonify({"error": "Chat manager not available"}), 500
        
        success = chat_manager.clear_conversation(conversation_id)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Conversation cleared"
            })
        else:
            return jsonify({"error": "Conversation not found"}), 404
            
    except Exception as e:
        return jsonify({"error": f"Failed to clear conversation: {str(e)}"}), 500


@chat_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for chat service"""
    try:
        services_available = {
            "chat_manager": chat_manager is not None,
            "flutter_manager": flutter_manager is not None,
            "chat_service": False,
            "intent_classifier": False
        }
        
        # Check if chat service is available
        try:
            from .services.chat_service import chat_service
            services_available["chat_service"] = True
        except ImportError:
            pass
        
        # Check if intent classifier is available
        try:
            from .services.intent_classifier import IntentClassifier
            services_available["intent_classifier"] = True
        except ImportError:
            pass
        
        all_healthy = all(services_available.values())
        
        return jsonify({
            "healthy": all_healthy,
            "services": services_available,
            "service": "chat"
        })
    
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e),
            "service": "chat"
        }), 500