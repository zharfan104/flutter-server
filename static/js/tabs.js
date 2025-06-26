/**
 * Tab Management and Code Preview Functions
 * Handles tab switching and live code generation preview
 */

// Code preview functions
/**
 * Update the Live Code Generation tab preview
 * @param {string} fileName - Name of the file being processed
 * @param {string} content - Content to display
 * @param {string} stage - Stage of processing: 'analyzing' or 'generating'
 * @param {object} data - Additional data for analysis phase (optional)
 * 
 * Examples:
 * updateCodePreview('main.dart', code, 'generating'); // Code generation
 * updateCodePreview(null, aiResponse, 'analyzing', streamData); // File determination
 */
function updateCodePreview(fileName, content, stage = 'generating', data = null) {
    const currentFileElement = document.getElementById('currentFile');
    const codeElement = document.getElementById('codePreview');
    
    if (stage === 'analyzing') {
        // File determination phase - show analysis preview
        updateAnalysisPreview(data || {message: fileName || 'Analyzing...'}, content);
    } else {
        // Code generation phase - original behavior
        if (currentFileElement) {
            // Avoid duplicate "Generating" text
            const displayName = fileName && fileName.toLowerCase().includes('generating') 
                ? fileName 
                : `⚡ Generating ${fileName || 'code'}...`;
            currentFileElement.innerHTML = displayName;
        }
        
        if (codeElement) {
            // Replace \\n with actual line breaks after escaping HTML
            const formattedContent = escapeHtml(content).replace(/\\n/g, '\n');
            codeElement.innerHTML = formattedContent + '<span class="typing-cursor">▋</span>';
        }
    }
}

/**
 * Show live preview of file analysis during the determining phase
 * Adapted from editor.js updateAnalysisPreview function
 */
function updateAnalysisPreview(data, accumulatedContent = '') {
    const currentFileElement = document.getElementById('currentFile');
    const codePreviewElement = document.getElementById('codePreview');
    
    if (currentFileElement) {
        // Show different messages based on the analysis phase
        if (data.message && data.message.includes('analyzing project structure')) {
            currentFileElement.innerHTML = `🔍 Analyzing project structure...`;
        } else if (data.message && data.message.includes('determining files')) {
            currentFileElement.innerHTML = `📋 Determining files to modify...`;
        } else if (data.message && data.message.includes('Identified')) {
            // Extract file counts from metadata if available
            const metadata = data.metadata || {};
            const modifyCount = metadata.files_to_modify ? metadata.files_to_modify.length : 'multiple';
            const createCount = metadata.files_to_create ? metadata.files_to_create.length : 0;
            const deleteCount = metadata.files_to_delete ? metadata.files_to_delete.length : 0;
            currentFileElement.innerHTML = `✅ Found ${modifyCount} files to modify, ${createCount} to create, ${deleteCount} to delete`;
        } else {
            currentFileElement.innerHTML = `🔍 ${data.message || 'AI is analyzing...'}`;
        }
    }
    
    if (codePreviewElement) {
        if (accumulatedContent) {
            // Show AI's reasoning during file determination
            const preview = accumulatedContent.slice(-800); // Show more text for analysis
            codePreviewElement.innerHTML = `${escapeHtml(preview)}<span class="typing-cursor">▋</span>`;
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
            
            codePreviewElement.innerHTML = escapeHtml(output);
        } else {
            // Show the current analysis message
            codePreviewElement.innerHTML = `// ${data.message || 'AI is analyzing your Flutter project...'}\n// Please wait while the AI determines which files to modify...<span class="typing-cursor">▋</span>`;
        }
    }
}

function clearCodePreview() {
    const currentFileElement = document.getElementById('currentFile');
    const codeElement = document.getElementById('codePreview');
    
    if (currentFileElement) {
        currentFileElement.textContent = 'Waiting for code generation...';
    }
    
    if (codeElement) {
        codeElement.innerHTML = '';
    }
}

function switchToCodeGenTab() {
    const codeGenTab = document.getElementById('code-generation-tab');
    const codeGenBadge = document.getElementById('code-gen-badge');
    
    if (codeGenBadge) {
        // Show badge
        codeGenBadge.style.display = 'inline';
    }
    
    if (codeGenTab && typeof bootstrap !== 'undefined') {
        // Switch to code generation tab
        const tab = new bootstrap.Tab(codeGenTab);
        tab.show();
    }
}

function switchToAppPreviewTab() {
    const appPreviewTab = document.getElementById('app-preview-tab');
    const codeGenBadge = document.getElementById('code-gen-badge');
    
    if (codeGenBadge) {
        // Hide badge
        codeGenBadge.style.display = 'none';
    }
    
    if (appPreviewTab && typeof bootstrap !== 'undefined') {
        // Switch to app preview tab
        const tab = new bootstrap.Tab(appPreviewTab);
        tab.show();
    }
}