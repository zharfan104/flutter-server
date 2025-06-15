import os
import subprocess
import threading
import time
import json
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class FlutterManager:
    def __init__(self):
        self.flutter_process = None
        self.project_path = "/home/flutter/project"
        self.output_buffer = []
        self.is_running = False
        self.ready = False
        
    def create_project(self):
        """Create Flutter project if it doesn't exist"""
        if not os.path.exists(self.project_path):
            print("Creating Flutter project...")
            subprocess.run(["flutter", "create", "myapp"], cwd="/app", check=True)
            print("Flutter project created!")
    
    def start_flutter(self):
        """Start Flutter web server"""
        if self.flutter_process:
            return {"error": "Flutter already running"}
        
        self.create_project()
        
        cmd = [
            "flutter", "run", "-d", "web-server",
            "--web-port=8080",
            "--web-hostname=0.0.0.0",  # Listen on all interfaces so nginx can proxy
            "--dart-define=FLUTTER_WEB_USE_SKIA=true"
        ]
        
        print(f"Starting Flutter with command: {' '.join(cmd)}")
        
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
        """Trigger hot reload"""
        if not self.flutter_process or not self.is_running:
            return {"error": "Flutter not running"}
        
        try:
            print("Sending hot reload command...")
            self.flutter_process.stdin.write('r\n')
            self.flutter_process.stdin.flush()
            
            time.sleep(0.5)
            
            recent_output = self.output_buffer[-20:]
            reload_success = any("Reloaded" in line for line in recent_output)
            
            return {
                "status": "reload_triggered",
                "success": reload_success,
                "recent_output": recent_output[-5:]
            }
            
        except Exception as e:
            return {"error": f"Failed to hot reload: {str(e)}"}
    
    
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

# Landing page with instructions and embedded app
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Flutter Hot Reload API</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 20px;
                max-width: 1800px;
                margin: 0 auto;
            }
            .panel {
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .app-panel {
                display: flex;
                flex-direction: column;
                min-height: 600px;
            }
            .flutter-container {
                flex: 1;
                border: 2px solid #ddd;
                border-radius: 8px;
                overflow: hidden;
                background: white;
            }
            iframe {
                width: 100%;
                height: 100%;
                border: none;
                min-height: 500px;
            }
            code { 
                background: #f4f4f4; 
                padding: 2px 6px; 
                border-radius: 3px;
            }
            pre { 
                background: #f4f4f4; 
                padding: 15px; 
                border-radius: 5px;
                overflow-x: auto; 
            }
            .status { 
                margin: 20px 0; 
                padding: 15px; 
                background: #e8f5e9; 
                border-radius: 5px;
                border-left: 4px solid #4caf50;
            }
            .controls {
                margin: 20px 0;
                padding: 15px;
                background: #e3f2fd;
                border-radius: 5px;
                border-left: 4px solid #2196f3;
            }
            button {
                background: #2196f3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
                font-size: 14px;
            }
            button:hover {
                background: #1976d2;
            }
            input[type="text"] {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin: 5px;
                width: 200px;
            }
            .log {
                background: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                max-height: 200px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 12px;
                margin-top: 10px;
            }
            h1 {
                text-align: center;
                color: #333;
                margin-bottom: 30px;
                grid-column: 1 / -1;
            }
            .editor-panel {
                display: flex;
                flex-direction: column;
                min-height: 600px;
            }
            .code-editor {
                flex: 1;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                resize: none;
                background: #1e1e1e;
                color: #d4d4d4;
                line-height: 1.5;
                min-height: 400px;
            }
            .editor-controls {
                margin-bottom: 10px;
            }
            .file-tabs {
                display: flex;
                gap: 5px;
                margin-bottom: 10px;
            }
            .file-tab {
                padding: 8px 12px;
                background: #e0e0e0;
                border: none;
                border-radius: 4px 4px 0 0;
                cursor: pointer;
                font-size: 12px;
            }
            .file-tab.active {
                background: #1e1e1e;
                color: white;
            }
            .editor-status {
                font-size: 12px;
                color: #666;
                margin-top: 5px;
            }
            @media (max-width: 1200px) {
                .container {
                    grid-template-columns: 1fr 1fr;
                }
                .editor-panel {
                    grid-column: 1 / -1;
                    order: -1;
                }
            }
            @media (max-width: 768px) {
                .container {
                    grid-template-columns: 1fr;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Flutter Hot Reload API</h1>
            
            <div class="panel editor-panel">
                <h2>📝 Code Editor</h2>
                
                <div class="file-tabs">
                    <button class="file-tab active" onclick="switchFile('main.dart')">main.dart</button>
                    <button class="file-tab" onclick="switchFile('pubspec.yaml')">pubspec.yaml</button>
                </div>
                
                <div class="editor-controls">
                    <button onclick="saveFile()">💾 Save & Hot Reload</button>
                    <button onclick="loadFile()">🔄 Reload from Server</button>
                    <span class="editor-status" id="editor-status">Ready</span>
                </div>
                
                <textarea id="code-editor" class="code-editor" placeholder="Loading file..."></textarea>
            </div>
            
            <div class="panel">
                <h2>🚀 Controls</h2>
                
                <div class="status">
                    <h3>Status: <span id="status">Checking...</span></h3>
                    <div id="flutter-info"></div>
                </div>
                
                <div class="controls">
                    <h3>Quick Actions:</h3>
                    <button onclick="startFlutter()">Start Flutter</button>
                    <button onclick="checkStatus()">Check Status</button>
                    <button onclick="hotReload()">Hot Reload</button>
                    <button onclick="getLogs()">Get Flutter Logs</button>
                    <button onclick="testFlutter()">Test Flutter Connection</button>
                    <br>
                    <input type="text" id="messageInput" placeholder="Enter custom message" value="Hello from Hot Reload!">
                    <button onclick="updateCounter()">Update Counter</button>
                </div>
                
                <h2>📡 API Endpoints:</h2>
                <ul>
                    <li><code>GET /api/health</code> - Check server health</li>
                    <li><code>POST /api/start</code> - Start Flutter</li>
                    <li><code>GET /api/status</code> - Get Flutter status</li>
                    <li><code>POST /api/hot-reload</code> - Trigger hot reload</li>
                    <li><code>PUT /api/files</code> - Update files</li>
                    <li><code>POST /api/demo/update-counter</code> - Demo update</li>
                </ul>
                
                <h2>🧪 Test Hot Reload (curl):</h2>
                <pre>
curl -X POST http://localhost:80/api/demo/update-counter \\
  -H "Content-Type: application/json" \\
  -d '{"message": "Hello from Hot Reload!"}'
                </pre>
                
                <div id="logs" class="log"></div>
            </div>
            
            <div class="panel app-panel">
                <h2>📱 Flutter App</h2>
                <div class="flutter-container">
                    <iframe id="flutter-app" src="/app" title="Flutter App">
                        <p>Flutter app will appear here once started. Click "Start Flutter" and wait 30-60 seconds.</p>
                    </iframe>
                </div>
            </div>
        </div>
        
        <script>
            let logContainer = document.getElementById('logs');
            let currentFile = 'lib/main.dart';
            let editor = document.getElementById('code-editor');
            let editorStatus = document.getElementById('editor-status');
            
            function log(message) {
                logContainer.innerHTML += new Date().toLocaleTimeString() + ': ' + message + '\\n';
                logContainer.scrollTop = logContainer.scrollHeight;
            }
            
            function setEditorStatus(message) {
                editorStatus.textContent = message;
            }
            
            function switchFile(fileName) {
                // Map display name to actual path
                const fileMap = {
                    'main.dart': 'lib/main.dart',
                    'pubspec.yaml': 'pubspec.yaml'
                };
                
                currentFile = fileMap[fileName] || fileName;
                
                // Update tab appearance
                document.querySelectorAll('.file-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                event.target.classList.add('active');
                
                loadFile();
            }
            
            function loadFile() {
                setEditorStatus('Loading...');
                fetch('/api/file/' + currentFile)
                    .then(r => r.json())
                    .then(data => {
                        if (data.status === 'success') {
                            editor.value = data.content;
                            setEditorStatus('Loaded ' + currentFile);
                            log('Loaded file: ' + currentFile);
                        } else {
                            editor.value = '// File not found or error loading';
                            setEditorStatus('Error: ' + data.error);
                            log('Error loading file: ' + data.error);
                        }
                    })
                    .catch(e => {
                        setEditorStatus('Network error');
                        log('Error loading file: ' + e);
                    });
            }
            
            function saveFile() {
                setEditorStatus('Saving...');
                fetch('/api/file/' + currentFile, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        content: editor.value,
                        auto_reload: currentFile.endsWith('.dart')
                    })
                })
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'file_updated') {
                        setEditorStatus('Saved! ' + (data.reload ? 'Hot reloaded.' : ''));
                        log('Saved file: ' + currentFile);
                        if (data.reload) {
                            log('Hot reload: ' + JSON.stringify(data.reload));
                            // Refresh iframe to show changes
                            setTimeout(() => {
                                document.getElementById('flutter-app').src = '/app?' + Date.now();
                            }, 1000);
                        }
                    } else {
                        setEditorStatus('Save failed');
                        log('Error saving file: ' + JSON.stringify(data));
                    }
                })
                .catch(e => {
                    setEditorStatus('Network error');
                    log('Error saving file: ' + e);
                });
            }
            
            function startFlutter() {
                log('Starting Flutter...');
                fetch('/api/start', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        log('Flutter start response: ' + JSON.stringify(data));
                        if (!data.error) {
                            log('Flutter is starting, please wait 30-60 seconds for compilation...');
                            // Refresh the iframe after a delay
                            setTimeout(() => {
                                document.getElementById('flutter-app').src = '/app?' + Date.now();
                                checkStatus();
                            }, 30000);
                        }
                    })
                    .catch(e => log('Error: ' + e));
            }
            
            function checkStatus() {
                fetch('/api/status')
                    .then(r => r.json())
                    .then(data => {
                        document.getElementById('status').textContent = 
                            data.running ? (data.ready ? 'Running & Ready' : 'Starting...') : 'Stopped';
                        document.getElementById('flutter-info').innerHTML = 
                            'Running: ' + data.running + '<br>Ready: ' + data.ready + 
                            (data.pid ? '<br>PID: ' + data.pid : '');
                        log('Status: ' + JSON.stringify(data));
                    })
                    .catch(e => log('Error checking status: ' + e));
            }
            
            function hotReload() {
                log('Triggering hot reload...');
                fetch('/api/hot-reload', { method: 'POST' })
                    .then(r => r.json())
                    .then(data => {
                        log('Hot reload response: ' + JSON.stringify(data));
                    })
                    .catch(e => log('Error: ' + e));
            }
            
            function updateCounter() {
                const message = document.getElementById('messageInput').value;
                log('Updating counter with message: ' + message);
                fetch('/api/demo/update-counter', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                })
                .then(r => r.json())
                .then(data => {
                    log('Update response: ' + JSON.stringify(data));
                    // Refresh iframe to show changes
                    setTimeout(() => {
                        document.getElementById('flutter-app').src = '/app?' + Date.now();
                    }, 1000);
                })
                .catch(e => log('Error: ' + e));
            }
            
            function getLogs() {
                log('Fetching Flutter logs...');
                fetch('/api/logs')
                    .then(r => r.json())
                    .then(data => {
                        log('=== FLUTTER LOGS ===');
                        data.logs.forEach(line => log('Flutter: ' + line));
                        log('=== END LOGS ===');
                        log('Process info: running=' + data.running + ', ready=' + data.ready + ', alive=' + data.process_alive);
                    })
                    .catch(e => log('Error fetching logs: ' + e));
            }
            
            function testFlutter() {
                log('Testing Flutter connection...');
                fetch('/api/test-flutter')
                    .then(r => r.json())
                    .then(data => {
                        log('Flutter test result: ' + JSON.stringify(data));
                        if (data.flutter_reachable) {
                            log('✅ Flutter is reachable! Status: ' + data.status_code);
                        } else {
                            log('❌ Flutter not reachable: ' + data.error);
                        }
                    })
                    .catch(e => log('Error testing Flutter: ' + e));
            }
            
            // Check status on page load
            checkStatus();
            
            // Load initial file
            loadFile();
            
            // Auto-refresh status every 10 seconds
            setInterval(checkStatus, 10000);
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("Starting Flask server on port 5000...")
    threading.Thread(target=lambda: flutter_manager.start_flutter(), daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)