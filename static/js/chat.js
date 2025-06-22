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
        this.isSending = false; // Prevent double sending
        this.currentRequestTimeout = null; // Track current request timeout
        
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
                
                // Load the first conversation or create default (but don't reload current conversation)
                if (data.conversations.length > 0) {
                    const firstConvId = data.conversations[0].conversation_id;
                    if (firstConvId !== this.currentConversationId) {
                        console.log('🔄 Loading different conversation:', firstConvId);
                        this.loadConversation(firstConvId);
                    } else {
                        console.log('✅ Skipping reload of current conversation:', firstConvId);
                    }
                } else if (!this.currentConversationId) {
                    console.log('🆕 Loading default conversation');
                    this.loadDefaultConversation();
                }
            }
        } catch (error) {
            console.error('Failed to load conversations:', error);
            // Skip showing toast - API is working fine, just empty conversations
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
            // Skip showing toast - API is working fine
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
    
    addSystemMessage(content) {
        const systemMessage = {
            role: 'system',
            content: content,
            formatted_time: new Date().toLocaleTimeString('en-US', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit',
                second: '2-digit'
            }),
            timestamp: Date.now() / 1000
        };
        this.addMessageToUI(systemMessage);
    }

    addMessageToUI(message) {
        const container = document.getElementById('messages-container');
        const welcomeMessage = document.getElementById('welcome-message');
        welcomeMessage.style.display = 'none';
        
        // Check for duplicates - avoid adding the same message twice
        // Use a simpler hash for better deduplication
        const contentHash = message.content.length + '-' + message.content.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '');
        const messageIdentifier = message.message_id || `${message.role}-${contentHash}`;
        const existingMessage = container.querySelector(`[data-message-id="${messageIdentifier}"]`);
        if (existingMessage) {
            console.log('🔄 Skipping duplicate message:', messageIdentifier, message.content.substring(0, 30));
            return;
        }
        
        console.log('✅ Adding message:', message.role, message.content.substring(0, 30));
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble-container mb-3';
        messageDiv.setAttribute('data-message-id', messageIdentifier);
        
        const isUser = message.role === 'user';
        const isSystem = message.role === 'system';
        const avatarIcon = isUser ? 'person-circle' : (isSystem ? 'exclamation-triangle' : 'robot');
        const avatarBg = isUser ? 'bg-primary' : (isSystem ? 'bg-warning' : 'bg-success');
        
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
        
        if (!message || sendButton.classList.contains('loading') || this.isSending) return;
        
        // Prevent double sending
        this.isSending = true;
        
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
            }),
            timestamp: Date.now() / 1000 // Add timestamp for deduplication
        };
        this.addMessageToUI(userMessage);
        
        // Don't immediately increment lastMessageCount - let polling handle it
        // This prevents sync issues between frontend and backend
        console.log('📊 User message added to UI, current lastMessageCount:', this.lastMessageCount);
        
        // Don't show processing indicator yet - wait for response to determine if needed
        
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
                
                // Add immediate AI response to UI
                const aiMessage = {
                    role: 'assistant',
                    content: data.message,
                    formatted_time: new Date().toLocaleTimeString('en-US', { 
                        hour12: false, 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                    }),
                    timestamp: Date.now() / 1000,
                    intent: data.intent
                };
                this.addMessageToUI(aiMessage);
                
                // Show appropriate indicator based on intent
                if (data.requires_code_modification) {
                    this.showProcessingIndicator('🔧 Working on code changes...');
                    console.log('🔧 Code modification started:', data.code_modification_request_id);
                    
                    // Set timeout for code modification to show completion message
                    setTimeout(() => {
                        this.hideProcessingIndicator();
                    }, 30000); // Hide after 30 seconds
                } else {
                    // For questions and follow-ups, no additional processing needed
                    console.log('💬 Conversation response completed');
                }
                
                // Reset sending flag after successful send
                this.isSending = false;
            } else {
                throw new Error(data.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            this.setLoadingState(false);
            this.hideProcessingIndicator();
            this.showToast('Failed to send message: ' + error.message, 'danger');
            
            // Reset sending flag on error
            this.isSending = false;
            
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
        // Disabled auto-polling - chat updates are now immediate via new modular system
        console.log('Chat polling disabled - using immediate response system');
        return;
        
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
            
            if (data.status === 'success') {
                // Check if there are any new messages (more robust approach)
                const currentMessages = data.messages;
                const currentCount = currentMessages.length;
                
                console.log('🔔 Polling check:', currentCount, 'messages vs', this.lastMessageCount, 'known');
                
                if (currentCount > this.lastMessageCount) {
                    // New messages arrived
                    console.log('🔔 Polling found new messages:', currentCount, 'vs', this.lastMessageCount);
                    const newMessages = currentMessages.slice(this.lastMessageCount);
                    console.log('📥 Processing', newMessages.length, 'new messages');
                    
                    // Filter out any messages that might already be in the UI to prevent duplicates
                    const container = document.getElementById('messages-container');
                    const existingMessageIds = new Set();
                    container.querySelectorAll('[data-message-id]').forEach(el => {
                        existingMessageIds.add(el.getAttribute('data-message-id'));
                    });
                    
                    newMessages.forEach(message => {
                        const messageId = message.message_id || `${message.role}-${message.content.length}-${message.content.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '')}`;
                        if (!existingMessageIds.has(messageId)) {
                            this.addMessageToUI(message);
                        } else {
                            console.log('🔄 Skipping duplicate message in polling:', messageId);
                        }
                    });
                    
                    this.lastMessageCount = currentCount;
                    console.log('📊 Updated lastMessageCount to:', this.lastMessageCount);
                    
                    // Check if the last message is from assistant - if so, hide loading indicators
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage && lastMessage.role === 'assistant') {
                        console.log('✅ Assistant response received, hiding processing indicator');
                        this.hideProcessingIndicator();
                        
                        // Clear the fallback timeout since we got a response
                        if (this.currentRequestTimeout) {
                            clearTimeout(this.currentRequestTimeout);
                            this.currentRequestTimeout = null;
                        }
                        
                        // Check if the message indicates code changes were made
                        if (this.messageIndicatesCodeChanges(lastMessage.content)) {
                            this.triggerFlutterReload();
                        }
                    }
                    
                    // Update conversations list to reflect new activity
                    this.loadConversations();
                } else if (this.lastMessageCount > currentCount) {
                    // Handle case where backend count is less (conversation was cleared, etc.)
                    console.log('🔄 Backend has fewer messages, resyncing');
                    this.renderMessages(currentMessages);
                    this.lastMessageCount = currentCount;
                }
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
            'Updated Files:',
            'Hot reload was automatically triggered',
            '✅ Code Analysis',
            '🔧 Error Fixing',
            'Pipeline completed',
            'successfully modified',
            'successfully created',
            'successfully updated',
            'code has been',
            'files have been',
            'implementation complete',
            'changes applied',
            'Flutter project updated'
        ];
        
        return codeChangeIndicators.some(indicator => content.toLowerCase().includes(indicator.toLowerCase()));
    }
    
    triggerFlutterReload() {
        // Use global hot reload function if available
        if (window.flutterDevServer && window.flutterDevServer.triggerFlutterHotReload) {
            window.flutterDevServer.triggerFlutterHotReload('Code changes detected in chat');
            return;
        }
        
        // Fallback: local implementation
        console.log('Code changes detected - refreshing Flutter app...');
        
        // Method 1: Refresh the Flutter iframe
        const flutterFrame = document.getElementById('flutter-app');
        if (flutterFrame) {
            // Show loading indicator if available
            if (window.showFlutterLoading) {
                window.showFlutterLoading();
            }
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

// Function to initialize chat (called from pages that include chat components)
function initializeChat() {
    if (!window.chatManager && document.getElementById('messages-container') && document.getElementById('chat-form')) {
        window.chatManager = new ChatManager();
        console.log('ChatManager initialized via initializeChat()');
    }
}

// Global functions for template usage
async function startNewConversation() {
    if (!window.chatManager) {
        console.warn('ChatManager not initialized - cannot start new conversation');
        return;
    }
    
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
    if (!window.chatManager) {
        console.warn('ChatManager not initialized - cannot clear conversation');
        return;
    }
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
    if (!window.chatManager) {
        console.warn('ChatManager not initialized - cannot delete conversation');
        return;
    }
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
    if (!window.chatManager) {
        console.warn('ChatManager not initialized - cannot export conversation');
        return;
    }
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
    // Only initialize ChatManager if the required elements exist (i.e., we're on the chat page)
    if (document.getElementById('messages-container') && document.getElementById('chat-form')) {
        window.chatManager = new ChatManager();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.chatManager) {
        window.chatManager.stopPolling();
    }
});