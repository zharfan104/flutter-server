"""
Code Modification Router

API endpoints for AI-powered code modification operations
"""

from flask import Blueprint, jsonify, request, Response
import uuid
import asyncio
import json
import time
from typing import Optional

# Create blueprint for code modification routes
code_modification_bp = Blueprint('code_modification', __name__, url_prefix='/api')

# Dependencies will be injected
flutter_manager = None


def set_dependencies(**services):
    """Standardized dependency injection"""
    global flutter_manager
    if 'flutter_manager' in services:
        flutter_manager = services['flutter_manager']


@code_modification_bp.route('/modify-code', methods=['POST'])
def modify_code():
    """Synchronous code modification endpoint"""
    try:
        from .services.code_modifier import CodeModificationService, ModificationRequest
        
        data = request.json
        description = data.get('description', '')
        target_files = data.get('target_files')
        user_id = data.get('user_id', 'anonymous')
        max_retries = data.get('max_retries', 3)
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        # Create modification request
        request_id = str(uuid.uuid4())
        modification_request = ModificationRequest(
            description=description,
            target_files=target_files,
            user_id=user_id,
            request_id=request_id,
            max_retries=max_retries
        )
        
        # Initialize code modification service
        code_modifier = CodeModificationService(flutter_manager.project_path)
        
        # Run modification synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                code_modifier.modify_code(modification_request)
            )
            
            # Convert result to dict if needed
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result
            
            return jsonify(result_dict)
        
        finally:
            loop.close()
    
    except Exception as e:
        return jsonify({"error": f"Code modification failed: {str(e)}"}), 500


@code_modification_bp.route('/stream/modify-code', methods=['POST'])
def modify_code_stream():
    """Stream code modifications using Server-Sent Events"""
    try:
        from .services.code_modifier import CodeModificationService, ModificationRequest
        
        data = request.json
        description = data.get('description', '')
        target_files = data.get('target_files')
        user_id = data.get('user_id', 'anonymous')
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        # Create modification request
        request_id = str(uuid.uuid4())
        modification_request = ModificationRequest(
            description=description,
            target_files=target_files,
            user_id=user_id,
            request_id=request_id
        )
        
        def generate_sse_stream():
            """Generator function for SSE stream"""
            try:
                # Send initial connection event
                yield f"event: connected\\ndata: {json.dumps({'request_id': request_id, 'message': 'Connected to streaming service'})}\\n\\n"
                
                # Initialize code modification service
                code_modifier = CodeModificationService(flutter_manager.project_path)
                
                # Create async event loop for streaming
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                async def stream_modification():
                    try:
                        # Check if streaming method exists
                        if hasattr(code_modifier, 'modify_code_stream'):
                            async for event in code_modifier.modify_code_stream(modification_request):
                                if hasattr(event, 'to_dict'):
                                    # StreamProgress object
                                    yield f"event: progress\\ndata: {json.dumps(event.to_dict())}\\n\\n"
                                elif isinstance(event, dict):
                                    # Status update
                                    if 'event_type' in event:
                                        yield f"event: {event['event_type']}\\ndata: {json.dumps(event)}\\n\\n"
                                    else:
                                        yield f"event: update\\ndata: {json.dumps(event)}\\n\\n"
                                elif isinstance(event, str):
                                    # Text chunk
                                    yield f"event: text\\ndata: {json.dumps({'text': event})}\\n\\n"
                        else:
                            # Fallback to synchronous modification
                            result = await code_modifier.modify_code(modification_request)
                            if hasattr(result, 'to_dict'):
                                result_dict = result.to_dict()
                            else:
                                result_dict = result
                            yield f"event: complete\\ndata: {json.dumps(result_dict)}\\n\\n"
                    
                    except Exception as e:
                        error_data = {
                            'error': str(e),
                            'stage': 'error',
                            'message': f'Streaming failed: {str(e)}'
                        }
                        yield f"event: error\\ndata: {json.dumps(error_data)}\\n\\n"
                    
                    finally:
                        # Send completion event
                        yield f"event: complete\\ndata: {json.dumps({'message': 'Stream ended'})}\\n\\n"
                
                # Run the async streaming
                async_gen = stream_modification()
                
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
                    'message': f'Failed to start streaming: {str(e)}'
                }
                yield f"event: error\\ndata: {json.dumps(error_data)}\\n\\n"
        
        # Return SSE response
        return Response(
            generate_sse_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        return jsonify({"error": f"Failed to start streaming: {str(e)}"}), 500


@code_modification_bp.route('/project-structure', methods=['GET'])
def get_project_structure():
    """Get detailed project structure analysis"""
    try:
        from .services.project_analyzer import FlutterProjectAnalyzer
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        analyzer = FlutterProjectAnalyzer(flutter_manager.project_path)
        project_summary = analyzer.generate_project_summary()
        
        # Get additional metadata
        project_metadata = {
            "analysis_timestamp": time.time(),
            "project_path": str(flutter_manager.project_path),
            "flutter_status": flutter_manager.get_status(),
            "cache_status": "live_analysis"
        }
        
        return jsonify({
            "status": "success",
            "project_structure": project_summary,
            "metadata": project_metadata
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "error": str(e)
        }), 500


@code_modification_bp.route('/validate-code', methods=['POST'])
def validate_code():
    """Validate Dart code using analyzer"""
    try:
        from .services.dart_analysis import DartAnalyzer
        
        data = request.json
        code_content = data.get('code', '')
        file_path = data.get('file_path', 'temp.dart')
        
        if not code_content:
            return jsonify({"error": "Code content is required"}), 400
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        # Initialize Dart analyzer
        analyzer = DartAnalyzer(flutter_manager.project_path)
        
        # Validate code
        validation_result = analyzer.validate_code_content(code_content, file_path)
        
        return jsonify({
            "status": "success",
            "validation_result": validation_result
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


@code_modification_bp.route('/fix-dart-errors', methods=['POST'])
def fix_dart_errors():
    """Fix dart analysis errors using SimpleDartAnalysisFixer"""
    try:
        from .services.simple_dart_fixer import SimpleDartAnalysisFixer
        
        data = request.json if request.json else {}
        max_attempts = data.get('max_attempts', 5)
        target_path = data.get('target_path')  # Optional specific path to analyze
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        # Create SimpleDartAnalysisFixer
        dart_fixer = SimpleDartAnalysisFixer(
            str(flutter_manager.project_path), 
            max_attempts=max_attempts
        )
        
        # Run fixing synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(dart_fixer.fix_until_clean())
            
            # Convert result to dict
            result_dict = {
                "success": result.success,
                "initial_error_count": result.initial_error_count,
                "final_error_count": result.final_error_count,
                "attempts_made": result.attempts_made,
                "files_processed": result.files_processed,
                "total_duration": result.total_duration,
                "error_message": result.error_message
            }
            
            return jsonify(result_dict)
        
        finally:
            loop.close()
    
    except Exception as e:
        return jsonify({"error": f"Dart error fixing failed: {str(e)}"}), 500


@code_modification_bp.route('/stream/fix-dart-errors', methods=['POST'])
def fix_dart_errors_stream():
    """Stream dart error fixing process using Server-Sent Events"""
    try:
        from .services.simple_dart_fixer import SimpleDartAnalysisFixer
        
        data = request.json if request.json else {}
        max_attempts = data.get('max_attempts', 5)
        target_path = data.get('target_path')
        
        if not flutter_manager:
            return jsonify({"error": "Flutter manager not available"}), 500
        
        def generate_fix_stream():
            try:
                # Create SimpleDartAnalysisFixer
                dart_fixer = SimpleDartAnalysisFixer(
                    str(flutter_manager.project_path), 
                    max_attempts=max_attempts
                )
                
                # Create event loop for async execution
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Send initial status
                    yield f"data: {json.dumps({'stage': 'starting', 'message': 'Starting dart error fixing...', 'progress_percent': 0})}\n\n"
                    
                    # Run the fixing process
                    async def run_fixing():
                        return await dart_fixer.fix_until_clean()
                    
                    result = loop.run_until_complete(run_fixing())
                    
                    # Send progress updates (simplified since we don't have streaming in SimpleDartAnalysisFixer yet)
                    if result.success:
                        yield f"data: {json.dumps({'stage': 'complete', 'message': f'Fixed all errors! Processed {len(result.files_processed)} files.', 'progress_percent': 100, 'success': True})}\n\n"
                    else:
                        yield f"data: {json.dumps({'stage': 'partial', 'message': f'Fixed {result.initial_error_count - result.final_error_count} of {result.initial_error_count} errors.', 'progress_percent': 90, 'success': False})}\n\n"
                    
                    # Send final result
                    result_dict = {
                        "stage": "result",
                        "success": result.success,
                        "initial_error_count": result.initial_error_count,
                        "final_error_count": result.final_error_count,
                        "attempts_made": result.attempts_made,
                        "files_processed": result.files_processed,
                        "total_duration": result.total_duration,
                        "error_message": result.error_message
                    }
                    
                    yield f"data: {json.dumps(result_dict)}\n\n"
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                error_data = {
                    "stage": "error",
                    "message": f"Error fixing failed: {str(e)}",
                    "error": str(e)
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return Response(generate_fix_stream(), mimetype='text/event-stream')
    
    except Exception as e:
        return jsonify({"error": f"Failed to start dart error fixing stream: {str(e)}"}), 500


@code_modification_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for code modification service"""
    try:
        # Check if required services are available
        services_available = {
            "flutter_manager": flutter_manager is not None,
            "project_path_exists": False,
            "dart_analyzer": False,
            "llm_services": False
        }
        
        if flutter_manager:
            import os
            services_available["project_path_exists"] = os.path.exists(flutter_manager.project_path)
        
        # Check if Dart analyzer is available
        try:
            from .services.dart_analysis import DartAnalyzer
            services_available["dart_analyzer"] = True
        except ImportError:
            pass
        
        # Check if LLM services are available
        try:
            from .services.llm_executor import LLMExecutor
            services_available["llm_services"] = True
        except ImportError:
            pass
        
        all_healthy = all(services_available.values())
        
        return jsonify({
            "healthy": all_healthy,
            "services": services_available,
            "service": "code_modification"
        })
    
    except Exception as e:
        return jsonify({
            "healthy": False,
            "error": str(e),
            "service": "code_modification"
        }), 500