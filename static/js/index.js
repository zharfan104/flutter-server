/**
 * Main Index Page JavaScript Functions
 * Handles initialization and common utility functions for the dashboard
 */

// Additional functions for integrated view
function openFullScreen() {
    window.open('/app', '_blank');
}

function quickChatMessage(message) {
    // Use ChatManager if available, otherwise open chat page
    if (window.chatManager && window.chatManager.sendMessage) {
        const messageInput = document.getElementById('message-input');
        if (messageInput) {
            messageInput.value = message;
            messageInput.dispatchEvent(new Event('input'));
            // Use ChatManager's sendMessage directly to avoid double event handling
            window.chatManager.sendMessageStream();
        }
    } else {
        // Fallback: open chat page in new tab
        const chatUrl = `/chat?message=${encodeURIComponent(message)}`;
        window.open(chatUrl, '_blank');
    }
}

// Utility function for HTML escaping
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize both dashboard and chat functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize chat if the functions exist
    if (typeof initializeChat === 'function') {
        initializeChat();
    }
    
    // Initialize advanced logging and monitoring
    if (typeof initializeAdvancedLogging === 'function') {
        initializeAdvancedLogging();
    }
    
    // Initialize pipeline monitoring
    if (typeof monitorChatRequests === 'function') {
        monitorChatRequests();
    }
    
    // Initialize performance monitoring
    if (typeof initializePerformanceMonitoring === 'function') {
        initializePerformanceMonitoring();
    }
    
    // Update AI status
    const aiStatusElement = document.getElementById('ai-status');
    if (aiStatusElement) {
        aiStatusElement.textContent = 'Ready';
    }
    
    // Auto-start Flutter if not running
    setTimeout(() => {
        if (typeof checkStatus === 'function') {
            checkStatus();
        }
    }, 1000);
});