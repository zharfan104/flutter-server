/**
 * Code Editor JavaScript for Flutter Development Server
 * Handles Monaco editor, file management, and AI-powered code modification
 */

class CodeEditor {
    constructor() {
        this.editor = null;
        this.currentFile = 'lib/main.dart';
        this.openTabs = new Map();
        this.unsavedChanges = new Set();
        this.fileTree = [];
        
        this.init();
    }
    
    init() {
        this.initMonacoEditor();
        this.loadFileTree();
        this.loadInitialFile();
        this.bindEditorEvents();
    }
    
    /**
     * Initialize Monaco Editor
     */
    initMonacoEditor() {
        require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@latest/min/vs' } });
        
        require(['vs/editor/editor.main'], () => {
            // Register Dart language support
            monaco.languages.register({ id: 'dart' });
            
            // Set Dart language configuration
            monaco.languages.setLanguageConfiguration('dart', {
                comments: {
                    lineComment: '//',
                    blockComment: ['/*', '*/']
                },
                brackets: [
                    ['{', '}'],
                    ['[', ']'],
                    ['(', ')']
                ],
                autoClosingPairs: [
                    { open: '{', close: '}' },
                    { open: '[', close: ']' },
                    { open: '(', close: ')' },
                    { open: '"', close: '"' },
                    { open: "'", close: "'" }
                ],
                surroundingPairs: [
                    { open: '{', close: '}' },
                    { open: '[', close: ']' },
                    { open: '(', close: ')' },
                    { open: '"', close: '"' },
                    { open: "'", close: "'" }
                ]
            });
            
            // Create the editor
            this.editor = monaco.editor.create(document.getElementById('monaco-editor'), {
                value: '// Loading...',
                language: 'dart',
                theme: 'vs-dark',
                automaticLayout: true,
                minimap: { enabled: true },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                wordWrap: 'on',
                tabSize: 2,
                insertSpaces: true
            });
            
            // Set up editor event handlers
            this.setupEditorHandlers();
        });
    }
    
    /**
     * Setup Monaco editor event handlers
     */
    setupEditorHandlers() {
        if (!this.editor) return;
        
        // Track content changes
        this.editor.onDidChangeModelContent(() => {
            this.markFileAsModified(this.currentFile);
            this.updateCursorPosition();
        });
        
        // Track cursor position
        this.editor.onDidChangeCursorPosition(() => {
            this.updateCursorPosition();
        });
        
        // Handle save shortcut
        this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
            this.saveFile();
        });
        
        // Handle format shortcut
        this.editor.addCommand(monaco.KeyMod.Shift | monaco.KeyMod.Alt | monaco.KeyCode.KeyF, () => {
            this.formatCode();
        });
    }
    
    /**
     * Update cursor position display
     */
    updateCursorPosition() {
        if (!this.editor) return;
        
        const position = this.editor.getPosition();
        const positionElement = document.getElementById('cursor-position');
        if (positionElement) {
            positionElement.textContent = `Ln ${position.lineNumber}, Col ${position.column}`;
        }
    }
    
    /**
     * Load file tree from server
     */
    async loadFileTree() {
        try {
            // Fetch real project structure from API
            const response = await fetch('/api/project-structure');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.fileTree = this.transformProjectStructureToTree(data.project_structure);
                this.renderFileTree();
                console.log('File tree loaded successfully');
            } else {
                throw new Error(data.error || 'Failed to load project structure');
            }
        } catch (error) {
            console.error('Failed to load file tree:', error);
            this.log(`Error loading file tree: ${error.message}`);
            
            // Fallback to basic file tree
            this.fileTree = this.getFallbackFileTree();
            this.renderFileTree();
        }
    }
    
    /**
     * Transform project structure data into file tree format
     */
    transformProjectStructureToTree(projectStructure) {
        const tree = [];
        
        // Add lib folder with actual file structure
        const libStructure = projectStructure.file_structure || {};
        const libFolder = {
            name: 'lib',
            type: 'folder',
            children: this.buildLibChildren(libStructure)
        };
        tree.push(libFolder);
        
        // Add other important files that typically exist in Flutter projects
        const commonFiles = [
            { name: 'pubspec.yaml', type: 'file', path: 'pubspec.yaml' },
            { name: 'pubspec.lock', type: 'file', path: 'pubspec.lock' },
            { name: 'README.md', type: 'file', path: 'README.md' },
            { name: 'analysis_options.yaml', type: 'file', path: 'analysis_options.yaml' }
        ];
        
        // Only add files that actually exist (you could enhance this with a file existence check)
        tree.push(...commonFiles);
        
        return tree;
    }
    
    /**
     * Build children nodes for lib folder from file structure
     */
    buildLibChildren(libStructure) {
        const children = [];
        
        // Process each directory in lib structure
        Object.entries(libStructure).forEach(([dirName, files]) => {
            if (dirName === '.') {
                // Root files in lib (like main.dart)
                files.forEach(fileName => {
                    children.push({
                        name: fileName,
                        type: 'file',
                        path: `lib/${fileName}`
                    });
                });
            } else {
                // Subdirectory with files
                const dirFiles = files.map(fileName => ({
                    name: fileName,
                    type: 'file',
                    path: `lib/${dirName}/${fileName}`
                }));
                
                children.push({
                    name: dirName,
                    type: 'folder',
                    children: dirFiles
                });
            }
        });
        
        return children;
    }
    
    /**
     * Get fallback file tree when API fails
     */
    getFallbackFileTree() {
        return [
            { name: 'lib', type: 'folder', children: [
                { name: 'main.dart', type: 'file', path: 'lib/main.dart' }
            ]},
            { name: 'pubspec.yaml', type: 'file', path: 'pubspec.yaml' }
        ];
    }
    
    /**
     * Render file tree in sidebar
     */
    renderFileTree() {
        const fileTreeElement = document.getElementById('file-tree');
        if (!fileTreeElement) return;
        
        const renderNode = (node, level = 0) => {
            const indent = '  '.repeat(level);
            // Initialize folders as expanded by default, show proper icon
            const icon = node.type === 'folder' ? 'folder-open' : 'file-earmark-code';
            const className = node.type === 'folder' ? 'file-item folder' : 'file-item';
            
            let html = `<div class="${className}" data-path="${node.path || ''}" style="padding-left: ${level * 20 + 10}px;">
                <i class="bi bi-${icon}"></i>${node.name}
            </div>`;
            
            if (node.children && node.type === 'folder') {
                html += node.children.map(child => renderNode(child, level + 1)).join('');
            }
            
            return html;
        };
        
        fileTreeElement.innerHTML = this.fileTree.map(node => renderNode(node)).join('');
        
        // Bind click events
        fileTreeElement.addEventListener('click', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (fileItem) {
                if (fileItem.classList.contains('folder')) {
                    // Toggle folder expansion
                    this.toggleFolder(fileItem);
                } else if (fileItem.dataset.path) {
                    // Open file
                    this.openFile(fileItem.dataset.path);
                }
            }
        });
    }
    
    /**
     * Toggle folder expansion/collapse
     */
    toggleFolder(folderElement) {
        const icon = folderElement.querySelector('i');
        const nextElements = [];
        let nextSibling = folderElement.nextElementSibling;
        
        // Find all child elements (they have higher padding-left)
        const folderPadding = parseInt(folderElement.style.paddingLeft);
        while (nextSibling && parseInt(nextSibling.style.paddingLeft) > folderPadding) {
            nextElements.push(nextSibling);
            nextSibling = nextSibling.nextElementSibling;
        }
        
        // Toggle visibility and icon
        const isExpanded = icon.classList.contains('bi-folder-open');
        if (isExpanded) {
            // Collapse
            icon.className = 'bi bi-folder';
            nextElements.forEach(el => el.style.display = 'none');
        } else {
            // Expand
            icon.className = 'bi bi-folder-open';
            nextElements.forEach(el => el.style.display = 'block');
        }
    }
    
    /**
     * Load initial file
     */
    loadInitialFile() {
        this.loadFile('lib/main.dart');
    }
    
    /**
     * Load file content
     */
    async loadFile(filePath = null) {
        const targetFile = filePath || this.currentFile;
        
        try {
            this.setEditorStatus('Loading...');
            
            const response = await fetch(`/api/file/${targetFile}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                if (this.editor) {
                    this.editor.setValue(data.content);
                    this.currentFile = targetFile;
                    this.openTabs.set(targetFile, data.content);
                    this.unsavedChanges.delete(targetFile);
                    this.updateTabStatus(targetFile, false);
                }
                this.setEditorStatus(`Loaded ${targetFile}`);
                this.log(`Loaded file: ${targetFile}`);
            } else {
                if (this.editor) {
                    this.editor.setValue('// File not found or error loading');
                }
                this.setEditorStatus(`Error: ${data.error}`);
                this.log(`Error loading file: ${data.error}`);
            }
        } catch (error) {
            this.setEditorStatus('Network error');
            this.log(`Error loading file: ${error.message}`);
        }
    }
    
    /**
     * Save current file
     */
    async saveFile() {
        if (!this.editor) return;
        
        try {
            this.setEditorStatus('Saving...');
            
            const content = this.editor.getValue();
            const response = await fetch(`/api/file/${this.currentFile}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    content: content,
                    auto_reload: this.currentFile.endsWith('.dart')
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'file_updated') {
                this.openTabs.set(this.currentFile, content);
                this.unsavedChanges.delete(this.currentFile);
                this.updateTabStatus(this.currentFile, false);
                
                const reloadInfo = data.reload ? 'Hot reloaded.' : '';
                this.setEditorStatus(`Saved! ${reloadInfo}`);
                this.log(`Saved file: ${this.currentFile}`);
                
                if (data.reload) {
                    this.log(`Hot reload: ${JSON.stringify(data.reload)}`);
                    // Refresh app preview
                    setTimeout(() => {
                        if (window.flutterDevServer) {
                            window.flutterDevServer.refreshApp();
                        }
                    }, 1000);
                }
            } else {
                this.setEditorStatus('Save failed');
                this.log(`Error saving file: ${JSON.stringify(data)}`);
            }
        } catch (error) {
            this.setEditorStatus('Network error');
            this.log(`Error saving file: ${error.message}`);
        }
    }
    
    /**
     * Format code using Monaco's built-in formatter
     */
    formatCode() {
        if (!this.editor) return;
        
        this.editor.getAction('editor.action.formatDocument').run();
        this.setEditorStatus('Code formatted');
        this.log('Code formatted');
    }
    
    /**
     * Open file in new tab
     */
    async openFile(filePath) {
        if (filePath === this.currentFile) return;
        
        // Save current file content in tab cache
        if (this.editor) {
            this.openTabs.set(this.currentFile, this.editor.getValue());
        }
        
        // Check if file is already cached
        if (this.openTabs.has(filePath)) {
            this.editor.setValue(this.openTabs.get(filePath));
            this.currentFile = filePath;
            this.setEditorStatus(`Switched to ${filePath}`);
        } else {
            await this.loadFile(filePath);
        }
        
        this.updateActiveTab(filePath);
    }
    
    /**
     * Mark file as modified
     */
    markFileAsModified(filePath) {
        this.unsavedChanges.add(filePath);
        this.updateTabStatus(filePath, true);
    }
    
    /**
     * Update tab status indicator
     */
    updateTabStatus(filePath, isModified) {
        const fileName = filePath.split('/').pop();
        const tabId = fileName.replace('.', '-') + '-status';
        const statusElement = document.getElementById(tabId);
        
        if (statusElement) {
            statusElement.textContent = isModified ? '●' : '○';
            statusElement.className = `ms-2 badge ${isModified ? 'bg-warning' : 'bg-secondary'}`;
        }
    }
    
    /**
     * Update active tab appearance
     */
    updateActiveTab(filePath) {
        // Remove active class from all tabs
        document.querySelectorAll('.nav-link').forEach(tab => {
            tab.classList.remove('active');
        });
        
        // Add active class to current tab
        const fileName = filePath.split('/').pop();
        const tabId = fileName.replace('.', '-') + '-tab';
        const tabElement = document.getElementById(tabId);
        if (tabElement) {
            tabElement.classList.add('active');
        }
    }
    
    /**
     * Set editor status message
     */
    setEditorStatus(message) {
        const statusElement = document.getElementById('editor-status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }
    
    /**
     * Log message to mini console
     */
    log(message) {
        const consoleElement = document.getElementById('mini-console');
        if (!consoleElement) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.innerHTML = `<span class="text-success">[${timestamp}]</span> ${message}`;
        
        consoleElement.appendChild(logEntry);
        
        // Keep only last 50 entries
        const entries = consoleElement.children;
        if (entries.length > 50) {
            consoleElement.removeChild(entries[0]);
        }
        
        consoleElement.scrollTop = consoleElement.scrollHeight;
    }
    
    /**
     * Check if there are unsaved changes
     */
    hasUnsavedChanges() {
        return this.unsavedChanges.size > 0;
    }
    
    /**
     * Add new tab
     */
    addNewTab() {
        const fileModal = new bootstrap.Modal(document.getElementById('fileModal'));
        this.populateFileList();
        fileModal.show();
    }
    
    /**
     * Populate file list in modal
     */
    populateFileList() {
        const fileList = document.getElementById('file-list');
        if (!fileList) return;
        
        const allFiles = this.getAllFiles(this.fileTree);
        fileList.innerHTML = allFiles.map(file => `
            <div class="list-group-item list-group-item-action" onclick="openFileFromModal('${file.path}')">
                <i class="bi bi-file-earmark-code me-2"></i>
                ${file.path}
            </div>
        `).join('');
    }
    
    /**
     * Get all files from tree structure
     */
    getAllFiles(nodes) {
        const files = [];
        
        const traverse = (node) => {
            if (node.type === 'file') {
                files.push(node);
            } else if (node.children) {
                node.children.forEach(traverse);
            }
        };
        
        nodes.forEach(traverse);
        return files;
    }
    
    /**
     * Request AI code modification
     */
    async requestAIModification() {
        const aiRequest = document.getElementById('ai-request');
        if (!aiRequest || !aiRequest.value.trim()) {
            window.flutterDevServer?.showToast('Please enter a modification request', 'warning');
            return;
        }
        
        const request = aiRequest.value.trim();
        const aiModal = new bootstrap.Modal(document.getElementById('aiModal'));
        aiModal.show();
        
        this.log(`AI modification requested: ${request}`);
        this.updateAIProgress(10, 'Analyzing request...');
        
        try {
            // Simulate AI processing
            await this.simulateAIProcess(request);
        } catch (error) {
            this.log(`AI modification failed: ${error.message}`);
            this.updateAIProgress(0, 'Failed');
        }
    }
    
    /**
     * Process AI modification request using streaming API
     */
    async simulateAIProcess(request) {
        try {
            this.updateAIProgress(10, 'Connecting to AI service...');
            this.logAI('Starting streaming modification request...');
            
            // Use EventSource for streaming
            const eventSource = new EventSource('/api/stream/modify-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    description: request,
                    user_id: 'editor_user'
                })
            });
            
            // Since EventSource doesn't support POST directly, use fetch with streaming
            const response = await fetch('/api/stream/modify-code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    description: request,
                    user_id: 'editor_user'
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Streaming request failed');
            }
            
            // Process streaming response
            await this.processStreamingResponse(response);
            
        } catch (error) {
            this.updateAIProgress(0, `Failed: ${error.message}`);
            this.logAI(`Error: ${error.message}`);
            throw error;
        }
    }
    
    /**
     * Process streaming response from AI service
     */
    async processStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentFile = null;
        let accumulatedContent = '';
        
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('event:')) {
                        // Handle event type
                        const eventType = line.substring(6).trim();
                        
                    } else if (line.startsWith('data:')) {
                        // Handle data
                        const dataStr = line.substring(5).trim();
                        if (!dataStr) continue;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            
                            // Handle different event types
                            if (data.stage) {
                                // Progress update
                                const progress = data.progress_percent || 0;
                                this.updateAIProgress(progress, data.message);
                                this.logAI(data.message);
                                
                                // Handle different stages
                                if (data.stage === 'analyzing') {
                                    // File determination phase
                                    if (typeof switchToCodeGenTab === 'function') {
                                        switchToCodeGenTab();
                                    }
                                    this.updateAnalysisPreview(data);
                                    
                                    // Handle analysis streaming chunks
                                    if (data.metadata && data.metadata.streaming && data.metadata.chunk) {
                                        accumulatedContent += data.metadata.chunk;
                                        this.updateAnalysisPreview(data, accumulatedContent);
                                    }
                                    
                                } else if (data.stage === 'generating') {
                                    // Code generation phase - existing logic
                                    if (data.metadata) {
                                        if (data.metadata.current_file !== currentFile) {
                                            if (currentFile && accumulatedContent) {
                                                // Show preview of previous file
                                                this.showFilePreview(currentFile, accumulatedContent);
                                            }
                                            currentFile = data.metadata.current_file;
                                            accumulatedContent = '';
                                        }
                                        
                                        if (data.metadata.text_chunk || data.metadata.chunk) {
                                            const chunk = data.metadata.text_chunk || data.metadata.chunk;
                                            accumulatedContent += chunk;
                                            // Update live preview
                                            this.updateLivePreview(currentFile, accumulatedContent);
                                        }
                                    }
                                }
                                
                                // Handle completion
                                if (data.stage === 'complete') {
                                    if (typeof clearCodePreview === 'function') {
                                        clearCodePreview();
                                    }
                                    this.logAI('AI modification completed successfully!');
                                    await this.loadFileTree();
                                    window.flutterDevServer?.showToast('AI modification completed', 'success');
                                } else if (data.stage === 'error') {
                                    if (typeof clearCodePreview === 'function') {
                                        clearCodePreview();
                                    }
                                    throw new Error(data.message);
                                }
                            } else if (data.text) {
                                // Raw text chunk - accumulate for preview
                                accumulatedContent += data.text;
                                this.updateLivePreview(currentFile, accumulatedContent);
                            } else if (data.event_type === 'result') {
                                // Final result
                                this.logAI(`Modified ${data.modified_files.length} files, created ${data.created_files.length} files`);
                                if (data.modified_files.includes(this.activeTab)) {
                                    await this.loadFile(this.activeTab);
                                    this.logAI(`Reloaded modified file: ${this.activeTab}`);
                                }
                            }
                            
                        } catch (e) {
                            console.error('Failed to parse streaming data:', e, dataStr);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }
    }
    
    /**
     * Show live preview of file being generated
     */
    updateLivePreview(fileName, content) {
        // Update the Live Code Generation tab
        const currentFileElement = document.getElementById('currentFile');
        const codePreviewElement = document.getElementById('codePreview');
        
        if (currentFileElement) {
            currentFileElement.innerHTML = `⚡ Generating ${fileName || 'code'}...`;
        }
        
        if (codePreviewElement) {
            // Show last 500 characters with typing effect
            const preview = content.slice(-500);
            codePreviewElement.innerHTML = `${this.escapeHtml(preview)}<span class="typing-cursor">▋</span>`;
        }
        
        // Also update the deprecated ai-preview element if it exists (backward compatibility)
        const previewElement = document.getElementById('ai-preview');
        if (previewElement) {
            const preview = content.slice(-500);
            previewElement.innerHTML = `
                <div class="text-muted small">Generating ${fileName || 'content'}...</div>
                <pre class="mt-2 p-2 bg-light rounded"><code>${this.escapeHtml(preview)}<span class="typing-cursor">▋</span></code></pre>
            `;
        }
    }
    
    /**
     * Show live preview of file analysis during the determining phase
     */
    updateAnalysisPreview(data, accumulatedContent = '') {
        const currentFileElement = document.getElementById('currentFile');
        const codePreviewElement = document.getElementById('codePreview');
        
        if (currentFileElement) {
            // Show different messages based on the analysis phase
            if (data.message.includes('analyzing project structure')) {
                currentFileElement.innerHTML = `🔍 Analyzing project structure...`;
            } else if (data.message.includes('determining files')) {
                currentFileElement.innerHTML = `📋 Determining files to modify...`;
            } else if (data.message.includes('Identified')) {
                // Extract file counts from metadata if available
                const metadata = data.metadata || {};
                const modifyCount = metadata.files_to_modify ? metadata.files_to_modify.length : 'multiple';
                const createCount = metadata.files_to_create ? metadata.files_to_create.length : 0;
                const deleteCount = metadata.files_to_delete ? metadata.files_to_delete.length : 0;
                currentFileElement.innerHTML = `✅ Found ${modifyCount} files to modify, ${createCount} to create, ${deleteCount} to delete`;
            } else {
                currentFileElement.innerHTML = `🔍 ${data.message}`;
            }
        }
        
        if (codePreviewElement) {
            if (accumulatedContent) {
                // Show AI's reasoning during file determination
                const preview = accumulatedContent.slice(-800); // Show more text for analysis
                codePreviewElement.innerHTML = `${this.escapeHtml(preview)}<span class="typing-cursor">▋</span>`;
            } else if (data.metadata && data.metadata.files_to_modify) {
                // Show the determined file list
                const files = data.metadata;
                let output = '// AI Analysis Results\n\n';
                
                if (files.files_to_modify && files.files_to_modify.length > 0) {
                    output += `// Files to modify (${files.files_to_modify.length}):\n`;
                    files.files_to_modify.forEach(file => {
                        output += `// - ${file}\n`;
                    });
                    output += '\n';
                }
                
                if (files.files_to_create && files.files_to_create.length > 0) {
                    output += `// Files to create (${files.files_to_create.length}):\n`;
                    files.files_to_create.forEach(file => {
                        output += `// + ${file}\n`;
                    });
                    output += '\n';
                }
                
                if (files.files_to_delete && files.files_to_delete.length > 0) {
                    output += `// Files to delete (${files.files_to_delete.length}):\n`;
                    files.files_to_delete.forEach(file => {
                        output += `// - ${file}\n`;
                    });
                }
                
                codePreviewElement.innerHTML = this.escapeHtml(output);
            } else {
                // Show the current analysis message
                codePreviewElement.innerHTML = `// ${data.message}\n// AI is analyzing your Flutter project...<span class="typing-cursor">▋</span>`;
            }
        }
    }
    
    /**
     * Show file preview after completion
     */
    showFilePreview(fileName, content) {
        this.logAI(`Completed generating ${fileName}`);
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Poll AI modification status (deprecated - using streaming now)
     */
    async pollAIModificationStatus_deprecated(requestId, maxAttempts = 30) {
        let attempts = 0;
        const pollInterval = 2000; // 2 seconds
        
        const poll = async () => {
            try {
                // DEPRECATED: This endpoint no longer exists in modular backend
                // const response = await fetch(`/api/modify-status/${requestId}`);
                // Using streaming instead - this function is deprecated
                throw new Error('Deprecated function - use streaming instead');
                const status = await response.json();
                
                if (!response.ok) {
                    throw new Error(status.error || 'Status check failed');
                }
                
                // Update progress
                this.updateAIProgress(status.progress_percent, status.current_step);
                this.logAI(status.current_step);
                
                // Check if completed
                if (status.status === 'completed') {
                    this.logAI('AI modification completed successfully!');
                    this.logAI(`Summary: ${status.result?.changes_summary || 'Changes applied'}`);
                    
                    // Refresh file tree and reload current file if it was modified
                    await this.loadFileTree();
                    if (status.result && status.result.modified_files && 
                        status.result.modified_files.includes(this.activeTab)) {
                        await this.loadFile(this.activeTab);
                        this.logAI(`Reloaded modified file: ${this.activeTab}`);
                    }
                    
                    window.flutterDevServer?.showToast('AI modification completed', 'success');
                    return; // Stop polling
                } else if (status.status === 'failed') {
                    this.updateAIProgress(0, `Failed: ${status.error_message}`);
                    this.logAI(`Failed: ${status.error_message}`);
                    throw new Error(status.error_message);
                } else if (status.status === 'cancelled') {
                    this.updateAIProgress(0, 'Cancelled');
                    this.logAI('AI modification was cancelled');
                    throw new Error('Modification was cancelled');
                }
                
                // Continue polling if still in progress
                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, pollInterval);
                } else {
                    throw new Error('Modification status check timed out');
                }
                
            } catch (error) {
                this.updateAIProgress(0, `Error: ${error.message}`);
                this.logAI(`Error checking status: ${error.message}`);
                throw error;
            }
        };
        
        // Start polling
        setTimeout(poll, pollInterval);
    }
    
    /**
     * Update AI progress
     */
    updateAIProgress(progress, text) {
        const progressBar = document.getElementById('ai-progress-bar');
        const progressText = document.getElementById('ai-progress-text');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (progressText) {
            progressText.textContent = text;
        }
    }
    
    /**
     * Log AI progress
     */
    logAI(message) {
        const aiLog = document.getElementById('ai-log');
        if (!aiLog) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.innerHTML = `<span class="text-muted">[${timestamp}]</span> ${message}`;
        
        aiLog.appendChild(logEntry);
        aiLog.scrollTop = aiLog.scrollHeight;
    }
    
    /**
     * Cancel AI generation
     */
    cancelAIGeneration() {
        this.updateAIProgress(0, 'Cancelled');
        this.logAI('AI generation cancelled by user');
    }
    
    /**
     * Refresh file tree
     */
    refreshFileTree() {
        this.loadFileTree();
        this.log('File tree refreshed');
    }
}

// Initialize code editor when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.codeEditor = new CodeEditor();
});

// Global functions for template usage
function loadFile() {
    return window.codeEditor?.loadFile();
}

function saveFile() {
    return window.codeEditor?.saveFile();
}

function formatCode() {
    return window.codeEditor?.formatCode();
}

function addNewTab() {
    return window.codeEditor?.addNewTab();
}

function refreshFileTree() {
    return window.codeEditor?.refreshFileTree();
}

function requestAIModification() {
    return window.codeEditor?.requestAIModification();
}

function cancelAIGeneration() {
    return window.codeEditor?.cancelAIGeneration();
}

function openFileFromModal(filePath) {
    const fileModal = bootstrap.Modal.getInstance(document.getElementById('fileModal'));
    fileModal.hide();
    return window.codeEditor?.openFile(filePath);
}

// Override hasUnsavedChanges for global use
window.hasUnsavedChanges = function() {
    return window.codeEditor?.hasUnsavedChanges() || false;
};