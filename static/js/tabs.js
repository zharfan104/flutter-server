/**
 * Tab Management and Code Preview Functions
 * Handles tab switching and live code generation preview
 */

// Code preview functions
function updateCodePreview(fileName, content) {
    const currentFileElement = document.getElementById('currentFile');
    const codeElement = document.getElementById('codePreview');
    
    if (currentFileElement) {
        currentFileElement.textContent = fileName || 'Generating...';
    }
    
    if (codeElement) {
        // Replace \\n with actual line breaks after escaping HTML
        const formattedContent = escapeHtml(content).replace(/\\n/g, '\n');
        codeElement.innerHTML = formattedContent + '<span class="typing-cursor">▋</span>';
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