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
        this.isGeneratingCode = false; // Track if we're generating code
        
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
            this.sendMessageStream(); // Use streaming version by default
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
                this.sendMessageStream(); // Use streaming version by default
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
        // Create consistent identifier regardless of whether message has backend ID
        const contentHash = message.content.length + '-' + message.content.substring(0, 30).replace(/[^a-zA-Z0-9]/g, '');
        const timeHash = message.formatted_time ? message.formatted_time.replace(/[^0-9]/g, '') : '';
        const consistentId = `${message.role}-${contentHash}-${timeHash}`;
        
        // Check multiple ways to avoid duplicates
        const existingByConsistentId = container.querySelector(`[data-message-consistent-id="${consistentId}"]`);
        const existingByBackendId = message.message_id ? container.querySelector(`[data-message-id="${message.message_id}"]`) : null;
        
        if (existingByConsistentId || existingByBackendId) {
            console.log('🔄 Skipping duplicate message:', {
                consistentId,
                backendId: message.message_id,
                content: message.content.substring(0, 30)
            });
            return;
        }
        
        console.log('✅ Adding message:', message.role, message.content.substring(0, 30));
        
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-bubble-container mb-3';
        messageDiv.setAttribute('data-message-consistent-id', consistentId);
        if (message.message_id) {
            messageDiv.setAttribute('data-message-id', message.message_id);
        }
        
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
        
        // Increment lastMessageCount to prevent polling from thinking this is a new message
        this.lastMessageCount++;
        console.log('📊 User message added to UI, updated lastMessageCount:', this.lastMessageCount);
        
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
                
                // Increment lastMessageCount for AI response too
                this.lastMessageCount++;
                console.log('📊 AI response added to UI, updated lastMessageCount:', this.lastMessageCount);
                
                // Show appropriate indicator based on intent
                if (data.requires_code_modification) {
                    this.showProcessingIndicator('🔧 Working on code changes...');
                    console.log('🔧 Code modification started:', data.code_modification_request_id);
                    
                    // Start conditional polling to detect completion
                    this.startConditionalPolling();
                    
                    // Set fallback timeout for code modification (much longer)
                    this.currentRequestTimeout = setTimeout(() => {
                        console.log('⏰ Code modification timeout reached, stopping polling');
                        this.hideProcessingIndicator();
                        this.stopConditionalPolling();
                    }, 300000); // 5 minutes fallback timeout
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
    
    async sendMessageStream() {
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
            timestamp: Date.now() / 1000
        };
        this.addMessageToUI(userMessage);
        this.lastMessageCount++; // Update count for user message
        
        // Show streaming indicator
        this.showStreamingIndicator('Connecting to AI...');
        
        try {
            console.log('🚀 [FRONTEND] Starting chat stream request...');
            console.log('🚀 [FRONTEND] Message:', message);
            console.log('🚀 [FRONTEND] Conversation ID:', this.currentConversationId);
            
            // EventSource doesn't support POST, so we use fetch with SSE streaming
            const response = await fetch('/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.currentConversationId,
                    user_id: 'user'
                })
            });
            
            console.log('🚀 [FRONTEND] Response received:', response.status, response.statusText);
            console.log('🚀 [FRONTEND] Response headers:', [...response.headers.entries()]);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let streamTimeout;
            let chunkCount = 0;
            
            console.log('🌊 [FRONTEND] Starting streaming response...');
            console.log('🌊 [FRONTEND] Reader created:', !!reader);
            
            // Set up timeout for inactive streams
            const resetTimeout = () => {
                if (streamTimeout) clearTimeout(streamTimeout);
                streamTimeout = setTimeout(() => {
                    console.warn('🔴 [FRONTEND] Stream timeout - no data received for 30 seconds');
                    reader.cancel();
                }, 30000); // 30 second timeout
            };
            
            resetTimeout();
            
            while (true) {
                console.log(`🔄 [FRONTEND] Reading chunk ${chunkCount + 1}...`);
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('🌊 [FRONTEND] Stream completed after', chunkCount, 'chunks');
                    if (streamTimeout) clearTimeout(streamTimeout);
                    break;
                }
                
                chunkCount++;
                console.log(`📦 [FRONTEND] Chunk ${chunkCount} received:`, value?.length, 'bytes');
                
                resetTimeout(); // Reset timeout on each data chunk
                
                const rawText = decoder.decode(value, { stream: true });
                console.log(`📝 [FRONTEND] Raw chunk text:`, rawText);
                
                buffer += rawText;
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer
                
                console.log(`📋 [FRONTEND] Processing ${lines.length} lines from buffer`);
                
                for (const line of lines) {
                    if (line.trim() === '') {
                        console.log('⏭️ [FRONTEND] Skipping empty line');
                        continue; // Skip empty lines
                    }
                    
                    console.log(`📄 [FRONTEND] Processing line:`, line);
                    
                    if (line.startsWith('data: ')) {
                        try {
                            const dataStr = line.slice(6);
                            console.log(`📊 [FRONTEND] Parsing SSE data:`, dataStr);
                            const data = JSON.parse(dataStr);
                            console.log(`✅ [FRONTEND] Parsed SSE data:`, data);
                            this.handleStreamEvent(data);
                        } catch (e) {
                            console.warn('❌ [FRONTEND] Failed to parse SSE data:', line, e);
                        }
                    } else if (line.startsWith('event: ')) {
                        // Handle event type if needed
                        const eventType = line.slice(8);
                        console.log('📡 [FRONTEND] SSE Event type:', eventType);
                    } else {
                        console.log('❓ [FRONTEND] Unknown line format:', line);
                    }
                }
            }
            
            if (streamTimeout) clearTimeout(streamTimeout);
            
        } catch (error) {
            console.error('Streaming failed:', error);
            
            // Clean up timeout if it exists
            if (typeof streamTimeout !== 'undefined' && streamTimeout) {
                clearTimeout(streamTimeout);
            }
            
            this.hideStreamingIndicator();
            this.setLoadingState(false);
            
            // Better error messaging based on error type
            let errorMessage = 'Failed to send message';
            if (error.message.includes('ERR_INCOMPLETE_CHUNKED_ENCODING')) {
                errorMessage = 'Connection interrupted - please try again';
            } else if (error.message.includes('timeout')) {
                errorMessage = 'Request timed out - please try again';
            } else {
                errorMessage = 'Failed to send message: ' + error.message;
            }
            
            this.showToast(errorMessage, 'danger');
            
            // Restore the message to input on error
            messageInput.value = message;
            this.updateSendButton();
            this.autoExpandTextarea();
        } finally {
            this.isSending = false;
        }
    }
    
    handleStreamEvent(data) {
        console.log('🎯 [FRONTEND] handleStreamEvent called with:', data);
        console.log('🎯 [FRONTEND] Event type:', typeof data, 'Stage:', data?.stage);
        
        // Track if we're in code generation mode
        if (data.stage === 'generating' && data.metadata && data.metadata.current_file) {
            this.isGeneratingCode = true;
            
            // Clear any streaming message in chat
            if (this.currentStreamingMessage) {
                const cursor = this.currentStreamingMessage.querySelector('.typing-cursor');
                if (cursor) cursor.remove();
                this.currentStreamingMessage = null;
                this.currentStreamingContent = '';
            }
        }
        
        // Handle different types of stream events
        if (data.stage) {
            // Progress update
            this.updateStreamingProgress(data);
            
            // Handle code generation updates
            if (data.stage === 'generating' && data.metadata) {
                if (data.metadata.current_file) {
                    // Switch to code generation tab when we start generating code
                    if (window.switchToCodeGenTab) {
                        window.switchToCodeGenTab();
                    }
                    
                    // Update code preview
                    if (window.updateCodePreview) {
                        const content = data.partial_content || '';
                        window.updateCodePreview(data.metadata.current_file, content);
                    }
                } else if (data.metadata.chunk && window.updateCodePreview) {
                    // Append chunk to current code preview
                    const codeEl = document.getElementById('codePreview');
                    if (codeEl) {
                        const currentContent = codeEl.textContent.replace('▋', '');
                        window.updateCodePreview(data.metadata.current_file || 'Generating...', currentContent + data.metadata.chunk);
                    }
                }
                
                // Handle file completion
                if (data.metadata.file_complete && window.updateCodePreview) {
                    const codeEl = document.getElementById('codePreview');
                    if (codeEl) {
                        // Remove cursor and add a newline for next file
                        codeEl.innerHTML = codeEl.innerHTML.replace('<span class="typing-cursor">▋</span>', '') + '\n\n';
                    }
                }
            }
        } else if (data.event_type === 'chat_response') {
            // For chat response, show it immediately without streaming if we're generating code
            if (this.isGeneratingCode || data.requires_code_modification) {
                this.handleChatResponse(data);
            } else {
                // Otherwise, handle normally
                if (!this.currentStreamingMessage) {
                    this.handleChatResponse(data);
                } else {
                    // Just finalize the streaming message
                    this.finalizeStreamingMessage(data);
                }
            }
        } else if (data.event_type === 'result') {
            // Code modification result
            this.handleCodeModificationResult(data);
            this.isGeneratingCode = false; // Reset flag
            
            // Switch back to app preview after a delay if successful
            if (data.success && window.switchToAppPreviewTab) {
                setTimeout(() => {
                    window.switchToAppPreviewTab();
                }, 3000);
            }
        } else if (data.event_type === 'text') {
            // Only append streaming text if we're NOT generating code
            if (!this.isGeneratingCode) {
                this.appendStreamingText(data.text);
            }
        }
    }
    
    updateStreamingProgress(progress) {
        const indicator = document.getElementById('typing-indicator');
        const statusText = indicator.querySelector('.processing-status');
        const progressBar = this.getOrCreateProgressBar();
        
        // Update message
        if (statusText) {
            statusText.textContent = progress.message || 'Processing...';
        }
        
        // Update progress bar
        if (progressBar && progress.progress_percent !== undefined) {
            progressBar.style.width = `${progress.progress_percent}%`;
            progressBar.setAttribute('aria-valuenow', progress.progress_percent);
        }
        
        // Show partial content if available (but not if we're generating code)
        if (progress.partial_content && !this.isGeneratingCode) {
            this.showPartialContent(progress.partial_content);
        }
        
        // Handle different stages
        switch (progress.stage) {
            case 'analyzing':
                this.setIndicatorColor('info');
                break;
            case 'generating':
                this.setIndicatorColor('primary');
                // Update status if in code generation
                if (progress.metadata && progress.metadata.current_file) {
                    const statusText = `Generating ${progress.metadata.current_file}...`;
                    if (statusText) {
                        indicator.querySelector('.processing-status').textContent = statusText;
                    }
                }
                break;
            case 'applying':
                this.setIndicatorColor('warning');
                break;
            case 'complete':
                this.hideStreamingIndicator();
                this.setLoadingState(false);
                break;
            case 'error':
                this.setIndicatorColor('danger');
                this.showToast(progress.message, 'danger');
                this.hideStreamingIndicator();
                this.setLoadingState(false);
                break;
        }
    }
    
    handleChatResponse(data) {
        console.log('💬 Chat response received:', data);
        
        // Add AI response to conversation
        if (this.currentConversationId !== data.conversation_id) {
            this.currentConversationId = data.conversation_id;
        }
        
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
        this.lastMessageCount++;
        
        // Handle code modification if needed
        if (data.requires_code_modification) {
            // Just show a simple status, not streaming indicator
            const indicator = document.getElementById('typing-indicator');
            const statusText = indicator.querySelector('.processing-status');
            if (statusText) {
                statusText.textContent = '🔧 Generating code...';
            }
            indicator.style.display = 'block';
            
            // Switch to code generation tab
            if (window.switchToCodeGenTab) {
                window.switchToCodeGenTab();
            }
            
            // Set flag to prevent streaming in chat
            this.isGeneratingCode = true;
        }
    }
    
    handleCodeModificationResult(data) {
        console.log('🔧 Code modification result:', data);
        
        if (data.success) {
            this.showToast('Code modification completed successfully!', 'success');
            
            // Trigger hot reload if Flutter is running
            this.triggerFlutterReload();
        } else {
            this.showToast('Code modification failed: ' + (data.errors || []).join(', '), 'danger');
        }
        
        this.hideStreamingIndicator();
        this.setLoadingState(false);
        
        // Reset code generation flag
        this.isGeneratingCode = false;
    }
    
    showStreamingIndicator(message) {
        const indicator = document.getElementById('typing-indicator');
        const statusText = indicator.querySelector('.processing-status');
        
        if (statusText) {
            statusText.textContent = message || 'Processing...';
        }
        
        // Create progress bar if it doesn't exist
        this.getOrCreateProgressBar();
        
        indicator.style.display = 'block';
        this.scrollToBottom();
    }
    
    hideStreamingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        indicator.style.display = 'none';
        
        // Remove any partial content display
        this.clearPartialContent();
    }
    
    getOrCreateProgressBar() {
        const indicator = document.getElementById('typing-indicator');
        let progressContainer = indicator.querySelector('.progress-container');
        
        if (!progressContainer) {
            progressContainer = document.createElement('div');
            progressContainer.className = 'progress-container mt-2';
            progressContainer.innerHTML = `
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar bg-primary" role="progressbar" 
                         style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    </div>
                </div>
            `;
            indicator.appendChild(progressContainer);
        }
        
        return progressContainer.querySelector('.progress-bar');
    }
    
    setIndicatorColor(type) {
        const progressBar = document.querySelector('#typing-indicator .progress-bar');
        if (progressBar) {
            progressBar.className = `progress-bar bg-${type}`;
        }
    }
    
    showPartialContent(content) {
        const indicator = document.getElementById('typing-indicator');
        let partialContainer = indicator.querySelector('.partial-content');
        
        if (!partialContainer) {
            partialContainer = document.createElement('div');
            partialContainer.className = 'partial-content mt-2 p-2 bg-light rounded';
            partialContainer.style.fontSize = '0.8em';
            partialContainer.style.fontFamily = 'monospace';
            partialContainer.style.maxHeight = '100px';
            partialContainer.style.overflow = 'auto';
            indicator.appendChild(partialContainer);
        }
        
        partialContainer.textContent = content;
        this.scrollToBottom();
    }
    
    clearPartialContent() {
        const indicator = document.getElementById('typing-indicator');
        const partialContainer = indicator.querySelector('.partial-content');
        const progressContainer = indicator.querySelector('.progress-container');
        
        if (partialContainer) {
            partialContainer.remove();
        }
        if (progressContainer) {
            progressContainer.remove();
        }
    }
    
    appendStreamingText(text) {
        // Create or get the streaming message element
        if (!this.currentStreamingMessage) {
            // Show typing indicator first
            this.showStreamingIndicator('AI is typing...');
            
            // Create a new message element for streaming
            const messagesContainer = document.getElementById('messages-container');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message assistant mb-3 d-flex align-items-end streaming-message';
            messageDiv.innerHTML = `
                <div class="avatar-sm bg-primary rounded-circle d-flex align-items-center justify-content-center me-2">
                    <i class="bi bi-robot text-white small"></i>
                </div>
                <div class="message-bubble assistant p-3">
                    <div class="message-content streaming-content"></div>
                    <div class="message-time text-end mt-1">${new Date().toLocaleTimeString('en-US', { 
                        hour12: false, 
                        hour: '2-digit', 
                        minute: '2-digit',
                        second: '2-digit'
                    })}</div>
                </div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            this.currentStreamingMessage = messageDiv.querySelector('.streaming-content');
            this.currentStreamingContent = '';
            
            // Hide the typing indicator now that we're showing real content
            this.hideStreamingIndicator();
        }
        
        // Append the text chunk
        this.currentStreamingContent += text;
        this.currentStreamingMessage.innerHTML = this.formatMessageContent(this.currentStreamingContent);
        
        // Add typing animation cursor
        if (!this.currentStreamingMessage.querySelector('.typing-cursor')) {
            const cursor = document.createElement('span');
            cursor.className = 'typing-cursor';
            cursor.textContent = '▌';
            cursor.style.animation = 'blink 1s infinite';
            this.currentStreamingMessage.appendChild(cursor);
        }
        
        this.scrollToBottom();
    }
    
    finalizeStreamingMessage(data) {
        // Remove typing cursor
        if (this.currentStreamingMessage) {
            const cursor = this.currentStreamingMessage.querySelector('.typing-cursor');
            if (cursor) cursor.remove();
            
            // Update with final content if different
            if (data.message && data.message !== this.currentStreamingContent) {
                this.currentStreamingMessage.innerHTML = this.formatMessageContent(data.message);
            }
            
            // Update message metadata
            const messageDiv = this.currentStreamingMessage.closest('.message');
            if (messageDiv) {
                messageDiv.classList.remove('streaming-message');
                messageDiv.dataset.intent = data.intent;
            }
        }
        
        // Clear streaming state
        this.currentStreamingMessage = null;
        this.currentStreamingContent = '';
        this.lastMessageCount++;
        
        // Handle code modification if needed
        if (data.requires_code_modification) {
            this.showStreamingIndicator('🔧 Starting code modifications...');
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
        // Default polling disabled - use startConditionalPolling instead
        console.log('Default polling disabled - use conditional polling for background operations');
        return;
        
        if (this.isPolling) return;
        
        this.isPolling = true;
        this.pollInterval = setInterval(() => {
            this.checkForNewMessages();
        }, 2000); // Poll every 2 seconds
    }
    
    startConditionalPolling() {
        // Start polling only for background code modifications
        if (this.isPolling) {
            console.log('🔄 Polling already active, skipping start');
            return;
        }
        
        console.log('🔄 Starting conditional polling for background operations');
        this.isPolling = true;
        this.pollInterval = setInterval(() => {
            console.log('📡 Polling for new messages...');
            this.checkForNewMessages();
        }, 3000); // Poll every 3 seconds for background updates
    }
    
    stopConditionalPolling() {
        // Stop polling when background operations complete
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
            this.isPolling = false;
            console.log('✅ Stopped conditional polling - background operations complete');
        }
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
                    
                    // Add new messages (addMessageToUI handles duplicate detection)
                    newMessages.forEach(message => {
                        console.log('📥 Adding new message from polling:', message.role, message.content.substring(0, 30));
                        this.addMessageToUI(message);
                    });
                    
                    this.lastMessageCount = currentCount;
                    console.log('📊 Updated lastMessageCount to:', this.lastMessageCount);
                    
                    // Check if the last message is from assistant - if so, check for completion
                    const lastMessage = newMessages[newMessages.length - 1];
                    if (lastMessage && lastMessage.role === 'assistant') {
                        console.log('✅ Assistant response received');
                        
                        // Check if the message indicates code changes completion
                        console.log('🔍 Checking message for completion indicators:', lastMessage.content.substring(0, 100));
                        
                        if (this.messageIndicatesCodeChanges(lastMessage.content)) {
                            console.log('🎉 Code modification completed, stopping polling and triggering reload');
                            this.hideProcessingIndicator();
                            this.stopConditionalPolling();
                            this.triggerFlutterReload();
                            
                            // Clear any fallback timeouts
                            if (this.currentRequestTimeout) {
                                console.log('✅ Clearing fallback timeout');
                                clearTimeout(this.currentRequestTimeout);
                                this.currentRequestTimeout = null;
                            }
                        } else if (this.messageIndicatesError(lastMessage.content)) {
                            console.log('❌ Code modification failed, stopping polling');
                            this.hideProcessingIndicator();
                            this.stopConditionalPolling();
                            
                            // Clear any fallback timeouts
                            if (this.currentRequestTimeout) {
                                console.log('✅ Clearing fallback timeout after error');
                                clearTimeout(this.currentRequestTimeout);
                                this.currentRequestTimeout = null;
                            }
                        } else {
                            console.log('⏳ Message does not indicate completion, continuing to poll...');
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
        // Check if the assistant message indicates that code was modified successfully
        const codeChangeIndicators = [
            '🎉 Code modification completed',
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
            'Flutter project updated',
            'hot reload triggered - changes are live',
            '🔄 Hot reload'
        ];
        
        console.log('🔍 Checking completion indicators against:', content.substring(0, 200));
        console.log('🔍 Available indicators:', codeChangeIndicators);
        
        const found = codeChangeIndicators.some(indicator => {
            const match = content.toLowerCase().includes(indicator.toLowerCase());
            if (match) {
                console.log('✅ Found completion indicator:', indicator);
            }
            return match;
        });
        
        console.log('🔍 Completion check result:', found);
        return found;
    }
    
    messageIndicatesError(content) {
        // Check if the assistant message indicates that code modification failed
        const errorIndicators = [
            '❌ Code modification failed',
            '❌ Code modification encountered issues',
            'modification encountered issues',
            'code modification failed',
            'failed to modify',
            'failed to create',
            'failed to update',
            'error occurred',
            'compilation failed',
            'build failed'
        ];
        
        return errorIndicators.some(indicator => content.toLowerCase().includes(indicator.toLowerCase()));
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
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
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