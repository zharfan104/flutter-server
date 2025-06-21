/**
 * Chat Interface JavaScript for Flutter Development Server
 * Handles real-time AI chat functionality with code modification capabilities
 */

class ChatManager {
    constructor() {
        this.currentConversationId = null;
        this.pollInterval = null;
        this.lastMessageCount = 0;
        this.isPolling = false;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadConversations();
        this.autoExpandTextarea();
        
        // Check for pre-filled message from URL
        this.handleUrlParameters();
        
        // Start polling for new messages
        this.startPolling();
        
        console.log('ChatManager initialized');
    }
    
    setupEventListeners() {
        // Chat form submission
        const chatForm = document.getElementById('chat-form');
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Message input auto-expand and enter handling
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('input', (e) => {
            this.updateSendButton();
            this.autoExpandTextarea();
        });
        
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Initial send button state
        this.updateSendButton();
    }
    
    autoExpandTextarea() {
        const textarea = document.getElementById('message-input');
        textarea.style.height = 'auto';
        const newHeight = Math.min(textarea.scrollHeight, 120);
        textarea.style.height = newHeight + 'px';
    }
    
    updateSendButton() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const isLoading = sendButton.classList.contains('loading');
        sendButton.disabled = messageInput.value.trim() === '' || isLoading;
    }
    
    handleUrlParameters() {
        const urlParams = new URLSearchParams(window.location.search);
        const prefilledMessage = urlParams.get('message');
        
        if (prefilledMessage) {
            const messageInput = document.getElementById('message-input');
            messageInput.value = prefilledMessage;
            this.updateSendButton();
            this.autoExpandTextarea();
            messageInput.focus();
            
            // Clear URL parameter
            const url = new URL(window.location);
            url.searchParams.delete('message');
            window.history.replaceState({}, '', url);
        }
    }
    
    async loadConversations() {
        try {
            const response = await fetch('/api/chat/conversations');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderConversations(data.conversations);
                this.renderStats(data.stats);
                
                // Load the first conversation or create default
                if (data.conversations.length > 0) {
                    this.loadConversation(data.conversations[0].conversation_id);
                } else {
                    this.loadDefaultConversation();
                }
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
            this.showToast('Failed to load conversations', 'danger');
        }
    }
    
    renderConversations(conversations) {
        const container = document.getElementById('conversations-list');
        const mobileContainer = document.getElementById('mobile-conversations-list');
        
        if (conversations.length === 0) {
            const emptyState = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-chat-left-dots display-4"></i>
                    <p class="mt-2">No conversations yet</p>
                    <button class="btn btn-sm btn-primary" onclick="startNewConversation()">
                        Start Chatting
                    </button>
                </div>
            `;
            container.innerHTML = emptyState;
            if (mobileContainer) mobileContainer.innerHTML = emptyState;
            return;
        }
        
        const html = conversations.map(conv => `
            <div class="conversation-item p-2 mb-1 ${conv.conversation_id === this.currentConversationId ? 'active' : ''}" 
                 onclick="chatManager.loadConversation('${conv.conversation_id}')">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 text-truncate">
                        <div class="fw-medium small text-truncate">${this.escapeHtml(conv.title)}</div>
                        <div class="text-muted small text-truncate">${this.escapeHtml(conv.last_message)}</div>
                    </div>
                    <div class="text-end">
                        <small class="text-muted">${conv.formatted_time}</small>
                        <div class="small">
                            <span class="badge bg-secondary">${conv.message_count}</span>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = html;
        if (mobileContainer) mobileContainer.innerHTML = html;
    }
    
    renderStats(stats) {
        const container = document.getElementById('chat-stats');
        if (!container) return;
        
        container.innerHTML = `
            <div>📊 Stats</div>
            <div>Conversations: ${stats.total_conversations}</div>
            <div>Messages: ${stats.total_messages}</div>
            <div>Avg per chat: ${Math.round(stats.average_messages_per_conversation)}</div>
        `;
    }
    
    async loadDefaultConversation() {
        try {
            const response = await fetch('/api/chat/history');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentConversationId = data.conversation_id;
                this.renderMessages(data.messages);
                this.lastMessageCount = data.messages.length;
            }
        } catch (error) {
            console.error('Failed to load default conversation:', error);
        }
    }
    
    async loadConversation(conversationId) {
        try {
            this.currentConversationId = conversationId;
            
            // Update active conversation in sidebar
            document.querySelectorAll('.conversation-item').forEach(item => {
                item.classList.remove('active');
            });
            document.querySelectorAll(`[onclick*="${conversationId}"]`).forEach(item => {
                item.classList.add('active');
            });
            
            const response = await fetch(`/api/chat/history?conversation_id=${conversationId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderMessages(data.messages);
                this.lastMessageCount = data.messages.length;
                
                // Update conversation title
                const titleElement = document.getElementById('current-conversation-title');
                if (data.messages.length > 0) {
                    const firstUserMessage = data.messages.find(m => m.role === 'user');
                    if (firstUserMessage) {
                        const title = firstUserMessage.content.substring(0, 30) + (firstUserMessage.content.length > 30 ? '...' : '');
                        titleElement.textContent = title;
                    }
                }
            }
        } catch (error) {
            console.error('Failed to load conversation:', error);
            this.showToast('Failed to load conversation', 'danger');
        }
    }
    
    renderMessages(messages) {
        const container = document.getElementById('messages-container');
        const welcomeMessage = document.getElementById('welcome-message');
        
        if (messages.length === 0) {
            welcomeMessage.style.display = 'block';
            return;
        }
        
        welcomeMessage.style.display = 'none';
        
        // Clear existing messages (except welcome)
        const existingMessages = container.querySelectorAll('.message-bubble-container');
        existingMessages.forEach(msg => msg.remove());
        
        messages.forEach(message => {
            this.addMessageToUI(message);
        });
        
        this.scrollToBottom();
    }
    
    addMessageToUI(message) {
        const container = document.getElementById('messages-container');
        const welcomeMessage = document.getElementById('welcome-message');
        welcomeMessage.style.display = 'none';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble-container mb-3';
        
        const isUser = message.role === 'user';
        const avatarIcon = isUser ? 'person-circle' : 'robot';
        const avatarBg = isUser ? 'bg-primary' : 'bg-success';
        
        messageDiv.innerHTML = `
            <div class="d-flex ${isUser ? 'justify-content-end' : 'justify-content-start'} align-items-start">
                ${!isUser ? `
                    <div class="avatar-sm ${avatarBg} rounded-circle d-flex align-items-center justify-content-center me-2">
                        <i class="bi bi-${avatarIcon} text-white small"></i>
                    </div>
                ` : ''}
                <div class="message-bubble ${message.role} p-3">
                    <div class="message-content">${this.formatMessageContent(message.content)}</div>
                    <div class="message-time text-end mt-1">${message.formatted_time}</div>
                </div>
                ${isUser ? `
                    <div class="avatar-sm ${avatarBg} rounded-circle d-flex align-items-center justify-content-center ms-2">
                        <i class="bi bi-${avatarIcon} text-white small"></i>
                    </div>
                ` : ''}
            </div>
        `;
        
        container.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatMessageContent(content) {
        // Convert markdown-style formatting to HTML
        let formatted = this.escapeHtml(content);
        
        // Bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Code blocks
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');
        
        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Emoji substitutions for common patterns
        formatted = formatted.replace(/✅/g, '<span class="text-success">✅</span>');
        formatted = formatted.replace(/⚠️/g, '<span class="text-warning">⚠️</span>');
        formatted = formatted.replace(/ℹ️/g, '<span class="text-info">ℹ️</span>');
        
        return formatted;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const message = messageInput.value.trim();
        
        if (!message || sendButton.classList.contains('loading')) return;
        
        // Set immediate loading state
        this.setLoadingState(true);
        
        // Clear input
        messageInput.value = '';
        this.autoExpandTextarea();
        
        // Add user message to UI immediately
        const userMessage = {
            role: 'user',
            content: message,
            formatted_time: new Date().toLocaleTimeString('en-US', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            })
        };
        this.addMessageToUI(userMessage);
        
        // Show enhanced loading state
        this.showProcessingIndicator();
        
        try {
            const response = await fetch('/api/chat/send', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.currentConversationId = data.conversation_id;
                // Update to AI processing state
                this.updateProcessingIndicator('AI is processing your request...');
                
                // If request_id is provided, start monitoring the pipeline
                if (data.request_id) {
                    this.startPipelineMonitoring(data.request_id);
                }
                
                // AI response will be added via polling
            } else {
                throw new Error(data.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            this.setLoadingState(false);
            this.hideProcessingIndicator();
            this.showToast('Failed to send message: ' + error.message, 'danger');
            
            // Restore the message to input on error
            messageInput.value = message;
            this.updateSendButton();
            this.autoExpandTextarea();
        }
    }
    
    setLoadingState(isLoading) {
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const sendIcon = sendButton.querySelector('i');
        
        if (isLoading) {
            // Set loading state
            sendButton.classList.add('loading');
            sendButton.disabled = true;
            messageInput.disabled = true;
            
            // Change button to show spinner
            sendIcon.className = 'spinner-border spinner-border-sm';
            sendButton.setAttribute('title', 'Sending...');
        } else {
            // Remove loading state
            sendButton.classList.remove('loading');
            messageInput.disabled = false;
            
            // Restore send icon
            sendIcon.className = 'bi bi-send';
            sendButton.setAttribute('title', 'Send message');
            
            this.updateSendButton(); // Re-evaluate button state
        }
    }
    
    showProcessingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        const statusText = indicator.querySelector('.processing-status');
        
        if (statusText) {
            statusText.textContent = 'Sending message...';
        }
        
        indicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    updateProcessingIndicator(message) {
        const indicator = document.getElementById('typing-indicator');
        const statusText = indicator.querySelector('.processing-status');
        
        if (statusText) {
            statusText.textContent = message;
        }
    }
    
    hideProcessingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        indicator.style.display = 'none';
        
        // Reset loading states
        this.setLoadingState(false);
    }
    
    showTypingIndicator() {
        this.showProcessingIndicator();
    }
    
    hideTypingIndicator() {
        this.hideProcessingIndicator();
    }
    
    startPolling() {
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollInterval = setInterval(() => {
            this.checkForNewMessages();
        }, 2000); // Poll every 2 seconds
    }
    
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        this.isPolling = false;
    }
    
    async checkForNewMessages() {
        if (!this.currentConversationId) return;
        
        try {
            const response = await fetch(`/api/chat/history?conversation_id=${this.currentConversationId}`);
            const data = await response.json();
            
            if (data.status === 'success' && data.messages.length > this.lastMessageCount) {
                // New messages arrived
                const newMessages = data.messages.slice(this.lastMessageCount);
                newMessages.forEach(message => {
                    this.addMessageToUI(message);
                });
                
                this.lastMessageCount = data.messages.length;
                
                // Check if the last message is from assistant - if so, hide loading indicators
                const lastMessage = newMessages[newMessages.length - 1];
                if (lastMessage && lastMessage.role === 'assistant') {
                    this.hideProcessingIndicator();
                    
                    // Check if the message indicates code changes were made
                    if (this.messageIndicatesCodeChanges(lastMessage.content)) {
                        this.triggerFlutterReload();
                    }
                }
                
                // Update conversations list to reflect new activity
                this.loadConversations();
            }
        } catch (error) {
            console.error('Failed to check for new messages:', error);
        }
    }
    
    scrollToBottom() {
        const container = document.getElementById('messages-container');
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 100);
    }
    
    messageIndicatesCodeChanges(content) {
        // Check if the assistant message indicates that code was modified
        const codeChangeIndicators = [
            '🎉 I\'ve successfully implemented',
            'Changes Made:',
            'Modified Files:',
            'Created Files:',
            'Hot reload was automatically triggered',
            '✅ Code Analysis',
            '🔧 Error Fixing',
            'Pipeline completed'
        ];
        
        return codeChangeIndicators.some(indicator => content.includes(indicator));
    }
    
    triggerFlutterReload() {
        console.log('Code changes detected - refreshing Flutter app...');
        
        // Method 1: Refresh the Flutter iframe
        const flutterFrame = document.getElementById('flutter-frame');
        if (flutterFrame) {
            // Add a small delay to ensure backend changes are applied
            setTimeout(() => {
                flutterFrame.src = flutterFrame.src;
                this.showToast('Flutter app refreshed due to code changes', 'info');
            }, 1000);
        }
        
        // Method 2: Try to trigger hot reload via API (as backup)
        setTimeout(() => {
            fetch('/api/hot-reload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).catch(error => {
                console.log('Hot reload API call failed (this is normal):', error);
            });
        }, 500);
    }

    startPipelineMonitoring(requestId) {
        console.log('Starting pipeline monitoring for request:', requestId);
        
        // Notify the global monitoring system if available
        if (window.flutterDevServer && window.flutterDevServer.updatePipelineProgress) {
            window.flutterDevServer.updatePipelineProgress('AI processing chat request...', 10, 'running');
            
            // Start monitoring this pipeline
            if (window.monitorPipelineProgress) {
                window.monitorPipelineProgress(requestId);
            }
        }
    }

    showToast(message, type = 'info') {
        // Use the global toast function if available
        if (window.flutterDevServer && window.flutterDevServer.showToast) {
            window.flutterDevServer.showToast(message, type);
        } else {
            // Fallback: try to create a simple toast notification
            console.log(`Toast [${type}]: ${message}`);
            const toastContainer = document.getElementById('toast-container');
            if (toastContainer) {
                const toast = document.createElement('div');
                toast.className = `toast show align-items-center text-bg-${type} border-0`;
                toast.setAttribute('role', 'alert');
                toast.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">${message}</div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
                    </div>
                `;
                toastContainer.appendChild(toast);
                setTimeout(() => toast.remove(), 5000);
            }
        }
    }
}

// Global functions for template usage
async function startNewConversation() {
    try {
        const response = await fetch('/api/chat/new', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            chatManager.loadConversation(data.conversation_id);
            chatManager.loadConversations(); // Refresh conversations list
            chatManager.showToast('New conversation started', 'success');
        } else {
            throw new Error(data.error || 'Failed to create conversation');
        }
    } catch (error) {
        console.error('Failed to start new conversation:', error);
        chatManager.showToast('Failed to start new conversation', 'danger');
    }
}

async function clearCurrentConversation() {
    if (!chatManager.currentConversationId) return;
    
    if (!confirm('Are you sure you want to clear this conversation? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/chat/conversation/${chatManager.currentConversationId}/clear`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            chatManager.loadConversation(chatManager.currentConversationId);
            chatManager.showToast('Conversation cleared', 'success');
        } else {
            throw new Error(data.error || 'Failed to clear conversation');
        }
    } catch (error) {
        console.error('Failed to clear conversation:', error);
        chatManager.showToast('Failed to clear conversation', 'danger');
    }
}

async function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/chat/conversation/${conversationId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            chatManager.loadConversations(); // Refresh conversations list
            if (chatManager.currentConversationId === conversationId) {
                chatManager.loadDefaultConversation();
            }
            chatManager.showToast('Conversation deleted', 'success');
        } else {
            throw new Error(data.error || 'Failed to delete conversation');
        }
    } catch (error) {
        console.error('Failed to delete conversation:', error);
        chatManager.showToast('Failed to delete conversation', 'danger');
    }
}

function exportConversation() {
    if (!chatManager.currentConversationId) return;
    
    // Get current conversation data and download as JSON
    fetch(`/api/chat/history?conversation_id=${chatManager.currentConversationId}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `conversation-${chatManager.currentConversationId}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                
                chatManager.showToast('Conversation exported', 'success');
            }
        })
        .catch(error => {
            console.error('Failed to export conversation:', error);
            chatManager.showToast('Failed to export conversation', 'danger');
        });
}

// Initialize chat manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.chatManager = new ChatManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.chatManager) {
        window.chatManager.stopPolling();
    }
});