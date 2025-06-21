import os
import subprocess
import threading
import time
import json
import asyncio
from dataclasses import asdict
from flask import Flask, request, jsonify, Response, send_from_directory, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class FlutterManager:
    def __init__(self):
        self.flutter_process = None
        self.project_path = os.path.join(os.getcwd(), "project")
        self.output_buffer = []
        self.is_running = False
        self.ready = False
        self.repo_url = os.environ.get('REPO_URL')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        
    def setup_project(self):
        """Clone repository or create Flutter project if no repo URL"""
        if self.repo_url:
            print(f"Cloning repository: {self.repo_url}")
            if not os.path.exists(self.project_path):
                # Clone with token if provided
                if self.github_token:
                    # Insert token into URL
                    auth_url = self.repo_url.replace('https://', f'https://{self.github_token}@')
                    subprocess.run(["git", "clone", auth_url, "project"], cwd=os.getcwd(), check=True)
                else:
                    subprocess.run(["git", "clone", self.repo_url, "project"], cwd=os.getcwd(), check=True)
                print("Repository cloned!")
            else:
                print("Repository already exists")
        else:
            # Fallback to creating generic Flutter project
            if not os.path.exists(self.project_path):
                print("Creating generic Flutter project...")
                subprocess.run(["flutter", "create", "project"], cwd=os.getcwd(), check=True)
                print("Flutter project created!")
    
    def git_pull(self):
        """Pull latest changes from repository"""
        if not self.repo_url:
            return {"error": "No repository configured"}
        
        try:
            print("Pulling latest changes...")
            result = subprocess.run(
                ["git", "pull", "origin", "main"], 
                cwd=self.project_path, 
                capture_output=True, 
                text=True, 
                check=True
            )
            print(f"Git pull output: {result.stdout}")
            return {"status": "success", "output": result.stdout}
        except subprocess.CalledProcessError as e:
            print(f"Git pull failed: {e.stderr}")
            return {"error": f"Git pull failed: {e.stderr}"}
    
    def start_flutter(self):
        """Start Flutter web server"""
        if self.flutter_process:
            return {"error": "Flutter already running"}
        
        self.setup_project()
        
        # Build Flutter web app first
        print("Building Flutter web app...")
        try:
            build_result = subprocess.run(
                ["flutter", "build", "web"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=60
            )
            if build_result.returncode != 0:
                return {"error": f"Flutter build failed: {build_result.stderr}"}
            print("✓ Flutter web build completed")
        except subprocess.TimeoutExpired:
            return {"error": "Flutter build timed out"}
        except Exception as e:
            return {"error": f"Flutter build error: {str(e)}"}
        
        # Start a simple HTTP server to serve the built web app
        import http.server
        import socketserver
        import os
        
        web_dir = os.path.join(self.project_path, "build", "web")
        if not os.path.exists(web_dir):
            return {"error": "Flutter web build directory not found"}
        
        # Create a simple HTTP server in a separate process
        cmd = [
            "python3", "-m", "http.server", "8080",
            "--bind", "0.0.0.0",
            "--directory", web_dir
        ]
        
        print(f"Starting Flutter web server: {' '.join(cmd)}")
        
        self.flutter_process = subprocess.Popen(
            cmd,
            cwd=self.project_path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=0
        )
        
        self.is_running = True
        self.ready = True  # Static server is ready immediately
        
        # Start output reader thread
        threading.Thread(target=self._read_output, daemon=True).start()
        
        return {"status": "starting", "pid": self.flutter_process.pid}
    
    def _read_output(self):
        """Read Flutter output continuously"""
        while self.is_running and self.flutter_process:
            try:
                line = self.flutter_process.stdout.readline()
                if line:
                    print(f"Flutter: {line.strip()}")
                    self.output_buffer.append(line.strip())
                    
                    if len(self.output_buffer) > 1000:
                        self.output_buffer = self.output_buffer[-500:]
                    
                    if "is being served at" in line or "Running application at" in line:
                        self.ready = True
                        print("Flutter is ready!")
                
                if self.flutter_process.poll() is not None:
                    print("Flutter process ended")
                    self.is_running = False
                    break
                    
            except Exception as e:
                print(f"Error reading output: {e}")
                time.sleep(0.1)
    
    
    def hot_reload(self):
        """Trigger hot reload (rebuild for static web)"""
        if not self.flutter_process or not self.is_running:
            return {"error": "Flutter not running"}
        
        try:
            print("Rebuilding Flutter web app...")
            
            # Build Flutter web app
            build_result = subprocess.run(
                ["flutter", "build", "web"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if build_result.returncode == 0:
                print("✓ Flutter web rebuild completed")
                return {
                    "status": "rebuilt",
                    "success": True,
                    "message": "Flutter web app rebuilt successfully"
                }
            else:
                return {
                    "status": "rebuild_failed", 
                    "success": False,
                    "error": build_result.stderr
                }
            
        except subprocess.TimeoutExpired:
            return {"error": "Flutter rebuild timed out"}
        except Exception as e:
            return {"error": f"Failed to rebuild: {str(e)}"}
    
    
    def update_file(self, file_path, content):
        """Update a file in the Flutter project"""
        full_path = os.path.join(self.project_path, file_path)
        
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        return {"status": "file_updated", "path": full_path}
    
    def get_status(self):
        """Get Flutter process status"""
        if not self.flutter_process:
            return {"running": False, "ready": False, "recent_output": self.output_buffer[-10:]}
        
        is_alive = self.flutter_process.poll() is None
        
        return {
            "running": is_alive,
            "ready": self.ready,
            "pid": self.flutter_process.pid if is_alive else None,
            "recent_output": self.output_buffer[-10:],
            "output_length": len(self.output_buffer)
        }

# Initialize Flutter manager
flutter_manager = FlutterManager()

# Initialize chat manager
from chat.chat_manager import chat_manager

# API Routes - all prefixed with /api
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "flutter": flutter_manager.get_status()})

@app.route('/api/start', methods=['POST'])
def start_flutter():
    result = flutter_manager.start_flutter()
    return jsonify(result)

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify(flutter_manager.get_status())

@app.route('/api/hot-reload', methods=['POST'])
def hot_reload():
    result = flutter_manager.hot_reload()
    return jsonify(result)

@app.route('/api/files', methods=['PUT'])
def update_file():
    data = request.json
    file_path = data.get('file_path')
    content = data.get('content')
    auto_reload = data.get('auto_reload', True)
    
    if not file_path or content is None:
        return jsonify({"error": "file_path and content required"}), 400
    
    result = flutter_manager.update_file(file_path, content)
    
    if auto_reload and flutter_manager.is_running:
        time.sleep(0.5)
        reload_result = flutter_manager.hot_reload()
        result['reload'] = reload_result
    
    return jsonify(result)

@app.route('/api/test-flutter', methods=['GET'])
def test_flutter():
    """Test if we can reach Flutter directly"""
    import requests
    try:
        response = requests.get('http://127.0.0.1:8080', timeout=5)
        return jsonify({
            "status": "success",
            "flutter_reachable": True,
            "status_code": response.status_code,
            "content_length": len(response.text),
            "headers": dict(response.headers)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "flutter_reachable": False,
            "error": str(e)
        })

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get Flutter logs for debugging"""
    return jsonify({
        "logs": flutter_manager.output_buffer,
        "running": flutter_manager.is_running,
        "ready": flutter_manager.ready,
        "process_alive": flutter_manager.flutter_process.poll() is None if flutter_manager.flutter_process else False
    })

@app.route('/api/git-pull', methods=['POST'])
def git_pull_and_reload():
    """Pull latest changes and trigger hot reload"""
    result = flutter_manager.git_pull()
    
    if result.get("error"):
        return jsonify(result), 400
    
    # Auto hot reload after successful pull if Flutter is running
    if flutter_manager.is_running:
        time.sleep(0.5)  # Give git pull time to complete
        reload_result = flutter_manager.hot_reload()
        result['hot_reload'] = reload_result
    
    return jsonify(result)

@app.route('/api/file/<path:file_path>', methods=['GET'])
def get_file(file_path):
    """Get file contents for editor"""
    try:
        full_path = os.path.join(flutter_manager.project_path, file_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                "status": "success",
                "content": content,
                "path": file_path
            })
        else:
            return jsonify({"status": "error", "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/api/file/<path:file_path>', methods=['PUT'])
def save_file(file_path):
    """Save file contents from editor"""
    try:
        data = request.json
        content = data.get('content', '')
        auto_reload = data.get('auto_reload', True)
        
        result = flutter_manager.update_file(file_path, content)
        
        if auto_reload and flutter_manager.is_running and file_path.endswith('.dart'):
            time.sleep(0.5)
            reload_result = flutter_manager.hot_reload()
            result['reload'] = reload_result
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# Code modification endpoints
@app.route('/api/modify-code', methods=['POST'])
def modify_code():
    """Generate and apply code modifications using LLM"""
    try:
        from code_modification.code_modifier import CodeModificationService, ModificationRequest
        from utils.status_tracker import status_tracker
        import uuid
        
        data = request.json
        description = data.get('description', '')
        target_files = data.get('target_files')
        user_id = data.get('user_id', 'anonymous')
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        # Create modification request
        request_id = str(uuid.uuid4())
        modification_request = ModificationRequest(
            description=description,
            target_files=target_files,
            user_id=user_id,
            request_id=request_id
        )
        
        # Create status tracking
        status_tracker.create_task(request_id, total_steps=4, metadata={
            "type": "code_modification",
            "description": description,
            "user_id": user_id
        })
        
        # Initialize code modification service
        code_modifier = CodeModificationService(flutter_manager.project_path)
        
        # Execute modification in background thread
        import threading
        
        def execute_modification():
            try:
                status_tracker.start_task(request_id, "Analyzing project structure...")
                status_tracker.update_progress(request_id, 25, "Determining target files...")
                
                # Execute the modification
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(code_modifier.modify_code(modification_request))
                
                if result.success:
                    status_tracker.update_progress(request_id, 75, "Applying modifications...")
                    
                    # Trigger hot reload if Flutter is running
                    if flutter_manager.is_running and result.modified_files:
                        reload_result = flutter_manager.hot_reload()
                        result.metadata = {"hot_reload": reload_result}
                    
                    status_tracker.complete_task(request_id, asdict(result))
                else:
                    status_tracker.fail_task(request_id, f"Modification failed: {', '.join(result.errors)}")
                    
            except Exception as e:
                status_tracker.fail_task(request_id, str(e))
        
        thread = threading.Thread(target=execute_modification, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "started",
            "request_id": request_id,
            "message": "Code modification started"
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to start code modification: {str(e)}"}), 500

@app.route('/api/modify-status/<request_id>', methods=['GET'])
def get_modification_status(request_id):
    """Get status of code modification request"""
    try:
        from utils.status_tracker import status_tracker
        
        task_summary = status_tracker.get_task_summary(request_id)
        if not task_summary:
            return jsonify({"error": "Request not found"}), 404
        
        return jsonify(task_summary)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/analyze-project', methods=['POST'])
def analyze_project_structure():
    """Analyze Flutter project structure"""
    try:
        from code_modification.project_analyzer import FlutterProjectAnalyzer
        
        analyzer = FlutterProjectAnalyzer(flutter_manager.project_path)
        project_summary = analyzer.generate_project_summary()
        
        return jsonify({
            "status": "success",
            "analysis": project_summary
        })
        
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500

@app.route('/api/suggest-files', methods=['POST'])
def suggest_modification_files():
    """Suggest files for modification based on description"""
    try:
        from code_modification.project_analyzer import FlutterProjectAnalyzer
        
        data = request.json
        description = data.get('description', '')
        
        if not description:
            return jsonify({"error": "Description is required"}), 400
        
        analyzer = FlutterProjectAnalyzer(flutter_manager.project_path)
        suggested_files = analyzer.suggest_files_for_modification(description)
        
        return jsonify({
            "status": "success",
            "suggested_files": suggested_files
        })
        
    except Exception as e:
        return jsonify({"error": f"Suggestion failed: {str(e)}"}), 500

@app.route('/api/modification-history', methods=['GET'])
def get_modification_history():
    """Get history of code modifications"""
    try:
        from utils.status_tracker import status_tracker
        
        # Get all modification tasks
        all_tasks = status_tracker.get_all_tasks()
        modification_tasks = {
            task_id: status_tracker.get_task_summary(task_id)
            for task_id, task in all_tasks.items()
            if task.metadata and task.metadata.get("type") == "code_modification"
        }
        
        return jsonify({
            "status": "success",
            "history": modification_tasks,
            "statistics": status_tracker.get_statistics()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chat API endpoints
@app.route('/api/chat/send', methods=['POST'])
def chat_send_message():
    """Send a message to AI chat and get response"""
    try:
        data = request.json
        message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        
        if not message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        # Get or create conversation
        if not conversation_id:
            conversation_id = chat_manager.get_or_create_default_conversation()
        elif not chat_manager.get_conversation(conversation_id):
            return jsonify({"error": "Conversation not found"}), 404
        
        # Add user message
        user_message = chat_manager.add_message(conversation_id, 'user', message)
        
        # Generate AI response in background thread
        def generate_ai_response():
            try:
                from code_modification.llm_executor import SimpleLLMExecutor
                from code_modification.project_analyzer import FlutterProjectAnalyzer
                from code_modification.code_modifier import CodeModificationService, ModificationRequest
                import uuid
                
                # Initialize services
                llm_executor = SimpleLLMExecutor()
                if not llm_executor.is_available():
                    ai_response = "I'm sorry, but I'm not properly configured with API keys. Please set up ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables to enable AI chat functionality."
                    chat_manager.add_message(conversation_id, 'assistant', ai_response)
                    return
                
                # Get project context
                project_analyzer = FlutterProjectAnalyzer(flutter_manager.project_path)
                try:
                    project_summary = project_analyzer.generate_project_summary()
                    project_context = json.dumps(project_summary, indent=2)
                except Exception as e:
                    project_context = f"Error analyzing project: {str(e)}"
                
                # Get recent conversation history
                recent_messages = chat_manager.get_messages(conversation_id, limit=10)
                conversation_history = ""
                for msg in recent_messages[:-1]:  # Exclude the current message
                    conversation_history += f"{msg.role.title()}: {msg.content}\n\n"
                
                # Create system prompt for Flutter development assistance
                system_prompt = f"""You are an expert Flutter development assistant. You help developers with their Flutter projects through conversational interface.

Project Context:
{project_context}

Recent Conversation:
{conversation_history}

Your capabilities:
1. Answer Flutter development questions
2. Provide code suggestions and examples
3. Help debug issues
4. Recommend best practices and packages
5. Analyze project structure
6. Suggest improvements

When the user asks for code changes or modifications:
1. Acknowledge the request
2. Explain what you're going to do
3. Use the existing code modification system to make changes
4. Confirm the changes were applied

Be helpful, concise, and practical. Always consider the current project context when providing advice."""

                # Determine if this requires code modification
                modification_keywords = ['add', 'create', 'modify', 'change', 'update', 'fix', 'implement', 'build', 'make']
                needs_modification = any(keyword in message.lower() for keyword in modification_keywords)
                
                if needs_modification and "don't" not in message.lower() and "how to" not in message.lower():
                    # This looks like a code modification request
                    try:
                        # Use code modification service
                        code_modifier = CodeModificationService(flutter_manager.project_path)
                        request_id = str(uuid.uuid4())
                        
                        modification_request = ModificationRequest(
                            description=message,
                            user_id='chat_user',
                            request_id=request_id
                        )
                        
                        # Execute modification
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(code_modifier.modify_code(modification_request))
                        
                        if result.success:
                            ai_response = f"I've successfully made the requested changes to your Flutter project!\n\n"
                            ai_response += f"**Changes Summary:** {result.changes_summary}\n\n"
                            ai_response += f"**Modified Files:** {', '.join(result.modified_files)}\n\n"
                            
                            # Trigger hot reload if Flutter is running
                            if flutter_manager.is_running and result.modified_files:
                                reload_result = flutter_manager.hot_reload()
                                if reload_result.get('success'):
                                    ai_response += "✅ Hot reload triggered successfully! You should see the changes in your app now."
                                else:
                                    ai_response += "⚠️ Hot reload was attempted but may not have worked. You might need to restart your Flutter app."
                            else:
                                ai_response += "ℹ️ Please start your Flutter development server to see the changes."
                        else:
                            ai_response = f"I encountered some issues while trying to make the changes:\n\n"
                            ai_response += f"**Errors:** {', '.join(result.errors)}\n\n"
                            ai_response += "Let me provide some guidance instead:\n\n"
                            
                            # Fall back to providing advice
                            messages = [{"role": "user", "content": f"The user asked: {message}\n\nProvide helpful guidance about how to implement this in Flutter."}]
                            response = llm_executor.execute(messages=messages, system_prompt=system_prompt)
                            ai_response += response.text
                    
                    except Exception as e:
                        print(f"Error in code modification: {e}")
                        ai_response = f"I had trouble modifying the code directly, but I can still help you with guidance!\n\n"
                        
                        # Fall back to providing advice
                        messages = [{"role": "user", "content": message}]
                        response = llm_executor.execute(messages=messages, system_prompt=system_prompt)
                        ai_response += response.text
                
                else:
                    # Regular conversation - provide advice and guidance
                    messages = [{"role": "user", "content": message}]
                    response = llm_executor.execute(messages=messages, system_prompt=system_prompt)
                    ai_response = response.text
                
                # Add AI response to conversation
                chat_manager.add_message(conversation_id, 'assistant', ai_response)
                
            except Exception as e:
                print(f"Error generating AI response: {e}")
                error_response = f"I'm sorry, I encountered an error while processing your request: {str(e)}"
                chat_manager.add_message(conversation_id, 'assistant', error_response)
        
        # Start AI response generation in background
        thread = threading.Thread(target=generate_ai_response, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "success",
            "message": "Message sent, AI is processing...",
            "conversation_id": conversation_id,
            "user_message": user_message.to_dict()
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to send message: {str(e)}"}), 500

@app.route('/api/chat/history', methods=['GET'])
def chat_get_history():
    """Get conversation history"""
    try:
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

@app.route('/api/chat/new', methods=['POST'])
def chat_new_conversation():
    """Create a new conversation"""
    try:
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

@app.route('/api/chat/conversations', methods=['GET'])
def chat_list_conversations():
    """Get list of all conversations"""
    try:
        conversations = chat_manager.get_conversation_list()
        stats = chat_manager.get_stats()
        
        return jsonify({
            "status": "success",
            "conversations": conversations,
            "stats": stats
        })
        
    except Exception as e:
        return jsonify({"error": f"Failed to list conversations: {str(e)}"}), 500

@app.route('/api/chat/conversation/<conversation_id>', methods=['DELETE'])
def chat_delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
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

@app.route('/api/chat/conversation/<conversation_id>/clear', methods=['POST'])
def chat_clear_conversation(conversation_id):
    """Clear all messages from a conversation"""
    try:
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

@app.route('/api/demo/update-counter', methods=['POST'])
def demo_update_counter():
    data = request.json
    message = data.get('message', 'Hello from API!')
    
    new_content = f'''
import 'package:flutter/material.dart';

void main() {{
  runApp(const MyApp());
}}

class MyApp extends StatelessWidget {{
  const MyApp({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: const MyHomePage(title: 'Flutter Hot Reload Demo'),
    );
  }}
}}

class MyHomePage extends StatefulWidget {{
  const MyHomePage({{super.key, required this.title}});
  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}}

class _MyHomePageState extends State<MyHomePage> {{
  int _counter = 0;

  void _incrementCounter() {{
    setState(() {{
      _counter++;
    }});
  }}

  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Text(
              '{message}',
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 20),
            const Text(
              'You have pushed the button this many times:',
            ),
            Text(
              '$_counter',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: _incrementCounter,
        tooltip: 'Increment',
        child: const Icon(Icons.add),
      ),
    );
  }}
}}
'''
    
    result = flutter_manager.update_file('lib/main.dart', new_content)
    
    if flutter_manager.is_running:
        time.sleep(0.5)
        reload_result = flutter_manager.hot_reload()
        result['reload'] = reload_result
    
    return jsonify(result)

# Flutter static assets routing (similar to nginx config)
@app.route('/canvaskit/<path:path>')
@app.route('/assets/<path:path>')
@app.route('/manifest.json')
@app.route('/favicon.ico')
@app.route('/favicon.png') 
@app.route('/icons/<path:path>')
@app.route('/flutter_bootstrap.js')
def flutter_static_assets(filename=None, path=None):
    """Proxy Flutter static assets to the Flutter development server"""
    import requests
    
    try:
        # Build the correct URL based on the request
        request_path = request.path.lstrip('/')
        flutter_url = f'http://127.0.0.1:8080/{request_path}'
        
        resp = requests.get(flutter_url, stream=True, timeout=10)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
                
        # Set proper headers for static assets
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        # Copy important headers from Flutter server
        for header in ['Content-Type', 'Content-Length']:
            if header in resp.headers:
                headers[header] = resp.headers[header]
        
        return Response(generate(), 
                       status=resp.status_code,
                       headers=headers)
    except Exception as e:
        print(f"Error serving static asset {request.path}: {str(e)}")
        return f"Asset not available: {str(e)}", 404

# Handle other JS/CSS/image files with file extensions
@app.route('/<path:filename>')
def static_file_handler(filename):
    """Handle static files like .js, .css, .png, etc."""
    import requests
    
    # Check if this looks like a static asset based on extension
    static_extensions = ['.js', '.js.map', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.woff', '.woff2', '.ttf', '.ico']
    
    if any(filename.endswith(ext) for ext in static_extensions):
        try:
            flutter_url = f'http://127.0.0.1:8080/{filename}'
            resp = requests.get(flutter_url, stream=True, timeout=10)
            
            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    yield chunk
                    
            # Set proper headers for static assets
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            # Copy important headers from Flutter server
            for header in ['Content-Type', 'Content-Length']:
                if header in resp.headers:
                    headers[header] = resp.headers[header]
            
            return Response(generate(), 
                           status=resp.status_code,
                           headers=headers)
        except Exception as e:
            print(f"Error serving static file {filename}: {str(e)}")
            return f"Asset not available: {str(e)}", 404
    
    # Not a static asset, return 404
    return "Not Found", 404

# Flutter app proxy route
@app.route('/app')
@app.route('/app/')
@app.route('/app/<path:path>')
def flutter_app(path=''):
    """Proxy Flutter app requests to the Flutter development server"""
    import requests
    try:
        flutter_url = f'http://127.0.0.1:8080/{path}'
        resp = requests.get(flutter_url, stream=True)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
                
        return Response(generate(), 
                       status=resp.status_code,
                       headers=dict(resp.headers))
    except Exception as e:
        return f"Flutter app not available: {str(e)}", 503

# Landing page with instructions and embedded app
@app.route('/')
def index():
    return render_template('index.html')

# Code editor page
@app.route('/editor')
def editor():
    return render_template('editor.html')

# Project overview page
@app.route('/project')
def project_overview():
    return render_template('project.html')

# AI Chat page
@app.route('/chat')
def chat():
    return render_template('chat.html')

def main():
    print("Starting Flask server on port 5000...")
    print("Auto-starting Flutter development server...")
    print("Access the web interface at: http://localhost:5000")
    
    # Auto-start Flutter development server
    try:
        # Check if port 8080 is available
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        port_available = sock.connect_ex(('localhost', 8080)) != 0
        sock.close()
        
        if not port_available:
            print("Warning: Port 8080 is already in use. Attempting to free it...")
            import subprocess
            subprocess.run(["pkill", "-9", "-f", "dart"], stderr=subprocess.DEVNULL)
            time.sleep(1)
        
        result = flutter_manager.start_flutter()
        if result.get('error'):
            print(f"Warning: Flutter auto-start failed: {result['error']}")
            print("You can still start Flutter manually via the web interface or API")
        else:
            print(f"✓ Flutter development server starting (PID: {result.get('pid')})")
            print("Waiting for Flutter to initialize...")
            # Give Flutter a moment to start up
            time.sleep(2)
    except Exception as e:
        print(f"Warning: Failed to auto-start Flutter: {str(e)}")
        print("You can still start Flutter manually via the web interface or API")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    main()