/**
 * Main application JavaScript for Flutter Development Server
 * Handles common functionality across all pages
 */

class FlutterDevServer {
    constructor() {
        this.apiBase = '/api';
        this.statusUpdateInterval = null;
        this.reloadCount = 0;
        this.startTime = Date.now();
        
        this.init();
    }
    
    init() {
        this.initStatusUpdates();
        this.initToasts();
        this.bindGlobalEvents();
        this.loadChatActivity();
    }
    
    /**
     * Initialize periodic status updates
     */
    initStatusUpdates() {
        this.updateStatus();
        this.statusUpdateInterval = setInterval(() => {
            this.updateStatus();
        }, 10000); // Update every 10 seconds
    }
    
    /**
     * Initialize toast notifications
     */
    initToasts() {
        this.toastContainer = document.getElementById('toast-container');
    }
    
    /**
     * Bind global event handlers
     */
    bindGlobalEvents() {
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 's':
                        e.preventDefault();
                        if (typeof saveFile === 'function') {
                            saveFile();
                        }
                        break;
                    case 'r':
                        e.preventDefault();
                        this.hotReload();
                        break;
                }
            }
        });
        
        // Handle beforeunload for unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges && this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = '';
            }
        });
    }
    
    /**
     * Update Flutter status in navigation
     */
    async updateStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            const statusElement = document.getElementById('flutter-status');
            const statusTextElement = document.getElementById('status-text');
            const statusIcon = statusElement.querySelector('.bi-circle-fill');
            
            if (data.running && data.ready) {
                statusIcon.className = 'bi bi-circle-fill text-success';
                statusTextElement.textContent = 'Running';
            } else if (data.running && !data.ready) {
                statusIcon.className = 'bi bi-circle-fill text-warning';
                statusTextElement.textContent = 'Starting...';
            } else {
                statusIcon.className = 'bi bi-circle-fill text-secondary';
                statusTextElement.textContent = 'Stopped';
            }
            
            // Update dashboard status if elements exist
            this.updateDashboardStatus(data);
            
        } catch (error) {
            console.error('Failed to update status:', error);
            const statusIcon = document.querySelector('#flutter-status .bi-circle-fill');
            if (statusIcon) {
                statusIcon.className = 'bi bi-circle-fill text-danger';
            }
            const statusText = document.getElementById('status-text');
            if (statusText) {
                statusText.textContent = 'Error';
            }
        }
    }
    
    /**
     * Update dashboard-specific status elements
     */
    updateDashboardStatus(data) {
        const elements = {
            'flutter-status-text': data.running ? (data.ready ? 'Running & Ready' : 'Starting...') : 'Stopped',
            'reload-count': this.reloadCount.toString(),
            'uptime': this.formatUptime()
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }
    
    /**
     * Format uptime display
     */
    formatUptime() {
        const now = Date.now();
        const diff = Math.floor((now - this.startTime) / 1000);
        const hours = Math.floor(diff / 3600);
        const minutes = Math.floor((diff % 3600) / 60);
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}`;
    }
    
    /**
     * Start Flutter development server
     */
    async startFlutter() {
        try {
            this.showToast('Starting Flutter...', 'info');
            const response = await fetch(`${this.apiBase}/start`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.error) {
                this.showToast(`Error: ${data.error}`, 'danger');
            } else {
                this.showToast('Flutter is starting, please wait 30-60 seconds...', 'success');
                this.log('Flutter start response: ' + JSON.stringify(data));
                
                // Refresh app preview after delay
                setTimeout(() => {
                    this.refreshApp();
                    this.updateStatus();
                }, 30000);
            }
        } catch (error) {
            this.showToast('Failed to start Flutter', 'danger');
            this.log('Error starting Flutter: ' + error.message);
        }
    }
    
    /**
     * Trigger hot reload
     */
    async hotReload() {
        try {
            this.showToast('Triggering hot reload...', 'info');
            const response = await fetch(`${this.apiBase}/hot-reload`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.error) {
                this.showToast(`Error: ${data.error}`, 'danger');
            } else {
                this.reloadCount++;
                this.showToast('Hot reload completed', 'success');
                this.log('Hot reload response: ' + JSON.stringify(data));
                
                // Refresh app preview
                setTimeout(() => {
                    this.refreshApp();
                }, 1000);
            }
        } catch (error) {
            this.showToast('Failed to hot reload', 'danger');
            this.log('Error during hot reload: ' + error.message);
        }
    }
    
    /**
     * Check Flutter status
     */
    async checkStatus() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            this.log('Status: ' + JSON.stringify(data));
            this.updateDashboardStatus(data);
        } catch (error) {
            this.showToast('Failed to check status', 'danger');
            this.log('Error checking status: ' + error.message);
        }
    }
    
    /**
     * Get Flutter logs
     */
    async getLogs() {
        try {
            this.showToast('Fetching Flutter logs...', 'info');
            const response = await fetch(`${this.apiBase}/logs`);
            const data = await response.json();
            
            this.log('=== FLUTTER LOGS ===');
            data.logs.forEach(line => this.log('Flutter: ' + line));
            this.log('=== END LOGS ===');
            this.log(`Process info: running=${data.running}, ready=${data.ready}, alive=${data.process_alive}`);
        } catch (error) {
            this.showToast('Failed to fetch logs', 'danger');
            this.log('Error fetching logs: ' + error.message);
        }
    }
    
    /**
     * Update counter demo
     */
    async updateCounter(message = null) {
        try {
            const messageInput = document.getElementById('messageInput');
            const msg = message || (messageInput ? messageInput.value : 'Hello from Hot Reload!');
            
            this.showToast(`Updating counter with message: ${msg}`, 'info');
            
            const response = await fetch(`${this.apiBase}/demo/update-counter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg })
            });
            const data = await response.json();
            
            this.log('Update response: ' + JSON.stringify(data));
            this.showToast('Counter updated successfully', 'success');
            
            // Refresh app preview
            setTimeout(() => {
                this.refreshApp();
            }, 1000);
        } catch (error) {
            this.showToast('Failed to update counter', 'danger');
            this.log('Error updating counter: ' + error.message);
        }
    }
    
    /**
     * Refresh Flutter app preview
     */
    refreshApp() {
        const iframe = document.getElementById('flutter-app');
        if (iframe) {
            iframe.src = '/app?' + Date.now();
        }
    }
    
    /**
     * Test Flutter connection
     */
    async testFlutter() {
        try {
            this.showToast('Testing Flutter connection...', 'info');
            const response = await fetch(`${this.apiBase}/test-flutter`);
            const data = await response.json();
            
            this.log('Flutter test result: ' + JSON.stringify(data));
            
            if (data.flutter_reachable) {
                this.showToast(`✅ Flutter is reachable! Status: ${data.status_code}`, 'success');
            } else {
                this.showToast(`❌ Flutter not reachable: ${data.error}`, 'danger');
            }
        } catch (error) {
            this.showToast('Failed to test Flutter connection', 'danger');
            this.log('Error testing Flutter: ' + error.message);
        }
    }
    
    /**
     * Show toast notification
     */
    showToast(message, type = 'info', duration = 5000) {
        if (!this.toastContainer) return;
        
        const toastId = 'toast-' + Date.now();
        const iconMap = {
            success: 'check-circle-fill',
            danger: 'x-circle-fill',
            warning: 'exclamation-triangle-fill',
            info: 'info-circle-fill'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast show align-items-center text-bg-${type} border-0`;
        toast.id = toastId;
        toast.setAttribute('role', 'alert');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi bi-${iconMap[type]} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" 
                        data-bs-dismiss="toast"></button>
            </div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Auto-remove after duration
        setTimeout(() => {
            const toastElement = document.getElementById(toastId);
            if (toastElement) {
                toastElement.remove();
            }
        }, duration);
    }
    
    /**
     * Log message to console (can be overridden by pages)
     */
    log(message) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] ${message}`);
        
        // Try to log to page-specific log container
        const logContainer = document.getElementById('logs');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';
            logEntry.innerHTML = `
                <span class="log-timestamp">[${timestamp}]</span> ${message}
            `;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }
    
    /**
     * Clear logs
     */
    clearLogs() {
        const logContainer = document.getElementById('logs');
        if (logContainer) {
            logContainer.innerHTML = '<div class="text-muted">Logs cleared...</div>';
        }
    }
    
    /**
     * Load chat activity for dashboard
     */
    async loadChatActivity() {
        const chatActivityContainer = document.getElementById('chat-activity');
        if (!chatActivityContainer) return;
        
        try {
            const response = await fetch('/api/chat/conversations');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderChatActivity(data.conversations, data.stats);
            } else {
                throw new Error(data.error || 'Failed to load chat activity');
            }
        } catch (error) {
            console.error('Failed to load chat activity:', error);
            chatActivityContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-chat-dots-fill text-muted"></i>
                    <p class="small mt-2">Start your first AI conversation!</p>
                    <a href="/chat" class="btn btn-sm btn-primary">Open Chat</a>
                </div>
            `;
        }
    }
    
    /**
     * Render chat activity in dashboard
     */
    renderChatActivity(conversations, stats) {
        const chatActivityContainer = document.getElementById('chat-activity');
        if (!chatActivityContainer) return;
        
        if (conversations.length === 0) {
            chatActivityContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="bi bi-chat-dots display-4 text-primary"></i>
                    <h6 class="mt-2">Start Your First AI Conversation</h6>
                    <p class="small">Ask me to help with your Flutter development!</p>
                    <a href="/chat" class="btn btn-sm btn-primary">
                        <i class="bi bi-chat-dots"></i>
                        Open AI Chat
                    </a>
                </div>
            `;
            return;
        }
        
        // Show recent conversations
        const recentConversations = conversations.slice(0, 3);
        const conversationHtml = recentConversations.map(conv => `
            <div class="d-flex align-items-start mb-2 p-2 border rounded hover-bg-light" 
                 style="cursor: pointer;" 
                 onclick="window.open('/chat', '_blank')">
                <div class="me-2">
                    <i class="bi bi-chat-left-text text-primary"></i>
                </div>
                <div class="flex-grow-1 text-truncate">
                    <div class="small fw-medium text-truncate">${this.escapeHtml(conv.title)}</div>
                    <div class="text-muted small text-truncate">${this.escapeHtml(conv.last_message)}</div>
                </div>
                <div class="text-end">
                    <small class="text-muted">${conv.formatted_time}</small>
                </div>
            </div>
        `).join('');
        
        chatActivityContainer.innerHTML = `
            <div class="mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">Recent Conversations</small>
                    <span class="badge bg-primary">${stats.total_conversations}</span>
                </div>
            </div>
            ${conversationHtml}
            ${conversations.length > 3 ? `
                <div class="text-center mt-2">
                    <a href="/chat" class="btn btn-sm btn-outline-primary">
                        View All ${conversations.length} Conversations
                    </a>
                </div>
            ` : ''}
        `;
    }
    
    /**
     * Escape HTML for safe rendering
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
    
    /**
     * Cleanup on page unload
     */
    destroy() {
        if (this.statusUpdateInterval) {
            clearInterval(this.statusUpdateInterval);
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.flutterDevServer = new FlutterDevServer();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.flutterDevServer) {
        window.flutterDevServer.destroy();
    }
});

// Global functions for backward compatibility and template usage
function startFlutter() {
    return window.flutterDevServer?.startFlutter();
}

function hotReload() {
    return window.flutterDevServer?.hotReload();
}

function checkStatus() {
    return window.flutterDevServer?.checkStatus();
}

function getLogs() {
    return window.flutterDevServer?.getLogs();
}

function updateCounter() {
    return window.flutterDevServer?.updateCounter();
}

function refreshApp() {
    return window.flutterDevServer?.refreshApp();
}

function testFlutter() {
    return window.flutterDevServer?.testFlutter();
}

function clearLogs() {
    return window.flutterDevServer?.clearLogs();
}

function quickChatMessage(message) {
    // Open chat page with pre-filled message
    const chatUrl = `/chat?message=${encodeURIComponent(message)}`;
    window.open(chatUrl, '_blank');
}