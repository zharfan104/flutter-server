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
                this.showToast('Hot reload completed - refreshing Flutter app', 'success');
                this.log('Hot reload response: ' + JSON.stringify(data));
                
                // Refresh app preview immediately after successful hot reload
                setTimeout(() => {
                    this.refreshApp();
                    this.showToast('Flutter app preview refreshed', 'info');
                }, 500);
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
     * Trigger Flutter hot reload with multiple methods
     */
    triggerFlutterHotReload(reason = 'Code changes detected') {
        console.log(`${reason} - triggering Flutter hot reload...`);
        
        // Method 1: Refresh the Flutter iframe
        const flutterFrame = document.getElementById('flutter-app');
        if (flutterFrame) {
            // Add a small delay to ensure backend changes are applied
            setTimeout(() => {
                flutterFrame.src = flutterFrame.src;
                this.showToast('Flutter app refreshed: ' + reason, 'info');
            }, 1000);
        }
        
        // Method 2: Try to trigger hot reload via API (as backup)
        setTimeout(() => {
            fetch('/api/hot-reload', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                console.log('Hot reload API response:', response.status);
            }).catch(error => {
                console.log('Hot reload API call failed (this is normal):', error);
            });
        }, 500);
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
     * Enhanced log function with categorization and filtering
     */
    logAdvanced(level, category, message, context = {}) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] [${level.toUpperCase()}] [${category}] ${message}`, context);
        
        // Add to system logs tab
        const logContainer = document.getElementById('logs');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${level.toLowerCase()}`;
            logEntry.dataset.level = level.toLowerCase();
            logEntry.dataset.category = category.toLowerCase();
            logEntry.innerHTML = `
                <span class="log-timestamp text-secondary">[${timestamp}]</span>
                <span class="badge badge-sm bg-${this.getLevelColor(level)} me-1">${level.toUpperCase()}</span>
                <span class="badge badge-sm bg-secondary me-2">${category}</span>
                <span class="text-dark">${message}</span>
            `;
            
            // Apply current filters
            const levelFilter = document.getElementById('log-level-filter')?.value || 'all';
            const categoryFilter = document.getElementById('log-category-filter')?.value || 'all';
            const searchFilter = document.getElementById('log-search')?.value || '';
            
            const shouldShow = (levelFilter === 'all' || level.toLowerCase() === levelFilter) &&
                             (categoryFilter === 'all' || category.toLowerCase() === categoryFilter) &&
                             (searchFilter === '' || message.toLowerCase().includes(searchFilter.toLowerCase()));
            
            logEntry.style.display = shouldShow ? 'block' : 'none';
            
            logContainer.appendChild(logEntry);
            if (shouldShow) {
                logContainer.scrollTop = logContainer.scrollHeight;
            }
            
            // Keep only recent entries
            const entries = logContainer.querySelectorAll('.log-entry');
            if (entries.length > 1000) {
                entries[0].remove();
            }
        }
    }

    /**
     * Get color for log level
     */
    getLevelColor(level) {
        const colors = {
            'error': 'danger',
            'warn': 'warning',
            'info': 'info',
            'debug': 'secondary'
        };
        return colors[level.toLowerCase()] || 'secondary';
    }

    /**
     * Update pipeline progress
     */
    updatePipelineProgress(step, progress, status = 'running') {
        const statusIndicator = document.getElementById('pipeline-status-indicator');
        const statusText = document.getElementById('pipeline-status-text');
        const progressBar = document.getElementById('pipeline-progress');
        const stepText = document.getElementById('pipeline-step');
        const percentText = document.getElementById('pipeline-percent');
        
        if (statusIndicator) {
            statusIndicator.className = `status-indicator bg-${status === 'running' ? 'warning' : status === 'completed' ? 'success' : 'danger'}`;
        }
        
        if (statusText) {
            statusText.textContent = status === 'running' ? 'Pipeline Active' : 
                                   status === 'completed' ? 'Pipeline Completed' : 'Pipeline Failed';
        }
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
            progressBar.className = `progress-bar ${status === 'completed' ? 'bg-success' : status === 'failed' ? 'bg-danger' : 'bg-primary'}`;
        }
        
        if (stepText) stepText.textContent = step;
        if (percentText) percentText.textContent = `${Math.round(progress)}%`;
    }

    /**
     * Add pipeline step
     */
    addPipelineStep(stepName, status = 'pending', details = '') {
        const stepsContainer = document.getElementById('pipeline-steps');
        if (!stepsContainer) return;
        
        // Clear welcome message if present
        if (stepsContainer.querySelector('.text-center')) {
            stepsContainer.innerHTML = '';
        }
        
        const stepElement = document.createElement('div');
        stepElement.className = `step-item ${status}`;
        stepElement.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${stepName}</strong>
                    ${details ? `<div class="small text-muted">${details}</div>` : ''}
                </div>
                <div class="small text-muted">
                    ${status === 'completed' ? '✓' : status === 'failed' ? '✗' : status === 'active' ? '⟳' : '○'}
                </div>
            </div>
        `;
        
        stepsContainer.appendChild(stepElement);
        stepsContainer.scrollTop = stepsContainer.scrollHeight;
    }

    /**
     * Clear all monitoring data
     */
    clearAllLogs() {
        this.clearLogs();
        const stepsContainer = document.getElementById('pipeline-steps');
        if (stepsContainer) {
            stepsContainer.innerHTML = `
                <div class="text-center text-muted py-4">
                    <i class="bi bi-play-circle display-6 text-secondary"></i>
                    <p class="mt-2">Pipeline steps will appear here when active</p>
                </div>
            `;
        }
        
        // Reset pipeline progress
        this.updatePipelineProgress('Waiting for request...', 0, 'idle');
        
        const debugInfo = document.getElementById('debug-info');
        if (debugInfo) {
            debugInfo.innerHTML = '<div class="text-muted">Debug information cleared...</div>';
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
    
    // Initialize monitoring systems
    initializeAdvancedLogging();
    initializePerformanceMonitoring();
    monitorChatRequests();
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

function triggerFlutterHotReload(reason) {
    return window.flutterDevServer?.triggerFlutterHotReload(reason);
}

function clearLogs() {
    return window.flutterDevServer?.clearLogs();
}

function quickChatMessage(message) {
    // Open chat page with pre-filled message
    const chatUrl = `/chat?message=${encodeURIComponent(message)}`;
    window.open(chatUrl, '_blank');
}

// Global functions for monitoring dashboard
function toggleMonitoringCollapse() {
    const content = document.getElementById('monitoring-content');
    const collapseBtn = document.getElementById('collapse-btn');
    const icon = collapseBtn.querySelector('i');
    
    if (content.classList.contains('collapsed')) {
        content.classList.remove('collapsed');
        icon.className = 'bi bi-chevron-up';
    } else {
        content.classList.add('collapsed');
        icon.className = 'bi bi-chevron-down';
    }
}

function clearAllLogs() {
    return window.flutterDevServer?.clearAllLogs();
}

function loadDebugInfo() {
    const debugInfo = document.getElementById('debug-info');
    if (!debugInfo) return;
    
    // Gather system information
    const systemInfo = {
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        online: navigator.onLine,
        cookieEnabled: navigator.cookieEnabled,
        windowSize: `${window.innerWidth}x${window.innerHeight}`,
        screenSize: `${screen.width}x${screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        localStorageAvailable: typeof(Storage) !== "undefined"
    };
    
    // Get Flutter server status
    const flutterStatus = {
        reloadCount: window.flutterDevServer?.reloadCount || 0,
        uptime: window.flutterDevServer?.formatUptime() || '00:00',
        startTime: window.flutterDevServer?.startTime || Date.now()
    };
    
    // Format debug information
    debugInfo.innerHTML = `
        <div class="mb-2">
            <strong>System Information</strong>
            <div class="small">
                <div>Timestamp: ${systemInfo.timestamp}</div>
                <div>Platform: ${systemInfo.platform}</div>
                <div>Language: ${systemInfo.language}</div>
                <div>Online: ${systemInfo.online ? 'Yes' : 'No'}</div>
                <div>Window: ${systemInfo.windowSize}</div>
                <div>Screen: ${systemInfo.screenSize}</div>
                <div>Timezone: ${systemInfo.timezone}</div>
                <div>Local Storage: ${systemInfo.localStorageAvailable ? 'Available' : 'Not Available'}</div>
            </div>
        </div>
        <div class="mb-2">
            <strong>Flutter Server Status</strong>
            <div class="small">
                <div>Hot Reloads: ${flutterStatus.reloadCount}</div>
                <div>Uptime: ${flutterStatus.uptime}</div>
                <div>Started: ${new Date(flutterStatus.startTime).toLocaleString()}</div>
            </div>
        </div>
        <div class="mb-2">
            <strong>Browser Console Logs</strong>
            <div class="small text-muted">Check browser console for detailed logs</div>
        </div>
    `;
}

function exportLogs() {
    const logs = document.getElementById('logs');
    const debugInfo = document.getElementById('debug-info');
    const pipelineSteps = document.getElementById('pipeline-steps');
    
    if (!logs) return;
    
    // Gather all log data
    const exportData = {
        timestamp: new Date().toISOString(),
        systemLogs: Array.from(logs.querySelectorAll('.log-entry')).map(entry => ({
            timestamp: entry.querySelector('.log-timestamp')?.textContent || '',
            level: entry.dataset.level || 'info',
            category: entry.dataset.category || 'system',
            message: entry.textContent.replace(/^\[[^\]]+\]/, '').trim()
        })),
        pipelineSteps: Array.from(pipelineSteps?.querySelectorAll('.step-item') || []).map(step => ({
            name: step.querySelector('strong')?.textContent || '',
            status: step.className.includes('completed') ? 'completed' : 
                   step.className.includes('failed') ? 'failed' :
                   step.className.includes('active') ? 'active' : 'pending',
            details: step.querySelector('.text-muted')?.textContent || ''
        })),
        debugInfo: debugInfo?.textContent || '',
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString()
    };
    
    // Create and download file
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `flutter-dev-logs-${new Date().toISOString().slice(0, 19)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    // Show success message
    if (window.flutterDevServer) {
        window.flutterDevServer.showToast('Logs exported successfully', 'success');
    }
}

// Initialize log filtering when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for log filters
    const levelFilter = document.getElementById('log-level-filter');
    const categoryFilter = document.getElementById('log-category-filter');
    const searchFilter = document.getElementById('log-search');
    
    if (levelFilter) {
        levelFilter.addEventListener('change', filterLogs);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterLogs);
    }
    
    if (searchFilter) {
        searchFilter.addEventListener('input', filterLogs);
    }
});

function filterLogs() {
    const levelFilter = document.getElementById('log-level-filter')?.value || 'all';
    const categoryFilter = document.getElementById('log-category-filter')?.value || 'all';
    const searchFilter = document.getElementById('log-search')?.value.toLowerCase() || '';
    
    const logEntries = document.querySelectorAll('#logs .log-entry');
    
    logEntries.forEach(entry => {
        const level = entry.dataset.level || 'info';
        const category = entry.dataset.category || 'system';
        const message = entry.textContent.toLowerCase();
        
        const levelMatch = levelFilter === 'all' || level === levelFilter;
        const categoryMatch = categoryFilter === 'all' || category === categoryFilter;
        const searchMatch = searchFilter === '' || message.includes(searchFilter);
        
        const shouldShow = levelMatch && categoryMatch && searchMatch;
        entry.style.display = shouldShow ? 'block' : 'none';
    });
}

// Enhanced logging integration with backend
function initializeAdvancedLogging() {
    // Periodically fetch advanced logs from backend
    setInterval(async () => {
        try {
            await updateAdvancedLogs();
        } catch (error) {
            console.error('Failed to update advanced logs:', error);
        }
    }, 5000); // Update every 5 seconds
}

async function updateAdvancedLogs() {
    try {
        // Get system logs
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        if (data.logs && data.logs.length > 0) {
            // Track previously seen logs to avoid duplicates
            if (!window.lastLogCount) {
                window.lastLogCount = 0;
            }
            
            // Only add new logs
            const newLogs = data.logs.slice(window.lastLogCount);
            window.lastLogCount = data.logs.length;
            
            newLogs.forEach(logLine => {
                if (window.flutterDevServer && logLine.trim()) {
                    // Determine log level based on content
                    let level = 'info';
                    if (logLine.toLowerCase().includes('error') || logLine.toLowerCase().includes('failed')) {
                        level = 'error';
                    } else if (logLine.toLowerCase().includes('warn') || logLine.toLowerCase().includes('warning')) {
                        level = 'warn';
                    } else if (logLine.toLowerCase().includes('debug')) {
                        level = 'debug';
                    }
                    
                    window.flutterDevServer.logAdvanced(level, 'flutter', logLine);
                }
            });
        }
    } catch (error) {
        console.error('Failed to fetch logs:', error);
        if (window.flutterDevServer) {
            window.flutterDevServer.logAdvanced('error', 'system', `Failed to fetch logs: ${error.message}`);
        }
    }
}

async function updatePipelineStatus(requestId) {
    if (!requestId) return;
    
    try {
        // Get pipeline status
        const statusResponse = await fetch(`/api/pipeline-status/${requestId}`);
        const statusData = await statusResponse.json();
        
        if (statusData.status) {
            // Update pipeline progress
            const progress = Math.round((statusData.current_step / statusData.total_steps) * 100);
            
            if (window.flutterDevServer) {
                window.flutterDevServer.updatePipelineProgress(
                    statusData.current_operation || 'Processing...',
                    progress,
                    statusData.status === 'completed' ? 'completed' :
                    statusData.status === 'failed' ? 'failed' : 'running'
                );
                
                // Add pipeline step if not already added
                if (statusData.current_operation) {
                    window.flutterDevServer.addPipelineStep(
                        statusData.current_operation,
                        statusData.status === 'completed' ? 'completed' :
                        statusData.status === 'failed' ? 'failed' : 'active'
                    );
                }
            }
        }
        
        // Get detailed debug info if available
        try {
            const debugResponse = await fetch(`/api/debug/pipeline/${requestId}`);
            const debugData = await debugResponse.json();
            
            if (debugData.logs) {
                debugData.logs.forEach(log => {
                    if (window.flutterDevServer) {
                        window.flutterDevServer.logAdvanced(
                            log.level.toLowerCase(),
                            log.category.toLowerCase(),
                            log.message,
                            log.context || {}
                        );
                    }
                });
            }
        } catch (debugError) {
            // Debug endpoint might not be available for all requests
            console.debug('Debug info not available for request:', requestId);
        }
        
    } catch (error) {
        console.error('Failed to update pipeline status:', error);
    }
}

// Monitor chat requests for pipeline tracking
function monitorChatRequests() {
    // Override the global chat sending function to track requests
    const originalFetch = window.fetch;
    window.fetch = async function(...args) {
        const [url, options] = args;
        
        // Track chat modification requests and code modification requests
        if ((url.includes('/api/chat/send') || url.includes('/api/modify-code') || url.includes('/api/ai-pipeline')) && options?.method === 'POST') {
            try {
                const response = await originalFetch.apply(this, arguments);
                const clonedResponse = response.clone();
                const data = await clonedResponse.json();
                
                if (data.request_id) {
                    // Start monitoring this pipeline
                    window.currentPipelineRequestId = data.request_id;
                    
                    // Show pipeline as active
                    if (window.flutterDevServer) {
                        window.flutterDevServer.updatePipelineProgress('Starting AI pipeline...', 5, 'running');
                        window.flutterDevServer.logAdvanced('info', 'pipeline', `Started pipeline with ID: ${data.request_id}`);
                        
                        // Clear previous steps
                        const stepsContainer = document.getElementById('pipeline-steps');
                        if (stepsContainer) {
                            stepsContainer.innerHTML = '';
                        }
                        
                        // Add initial step
                        window.flutterDevServer.addPipelineStep('Pipeline initiated', 'active', 'Processing request...');
                    }
                    
                    // Start monitoring
                    monitorPipelineProgress(data.request_id);
                }
                
                return response;
            } catch (error) {
                console.error('Error monitoring chat request:', error);
                if (window.flutterDevServer) {
                    window.flutterDevServer.logAdvanced('error', 'pipeline', `Failed to monitor request: ${error.message}`);
                }
                return originalFetch.apply(this, arguments);
            }
        }
        
        return originalFetch.apply(this, arguments);
    };
}

function monitorPipelineProgress(requestId) {
    let attempts = 0;
    const maxAttempts = 150; // 5 minutes with 2-second intervals
    
    const interval = setInterval(async () => {
        attempts++;
        
        try {
            await updatePipelineStatus(requestId);
            
            // Check if pipeline is complete
            const response = await fetch(`/api/pipeline-status/${requestId}`);
            
            if (!response.ok) {
                if (window.flutterDevServer) {
                    window.flutterDevServer.logAdvanced('warn', 'pipeline', `Status check failed: ${response.status} ${response.statusText}`);
                }
                
                // If we get a 404, the request might not exist yet, continue checking
                if (response.status === 404 && attempts < 30) {
                    return; // Continue checking
                }
                
                // For other errors, stop after a few attempts
                if (attempts > 10) {
                    clearInterval(interval);
                    const errorMsg = `Pipeline monitoring failed after ${attempts} attempts (${response.status} ${response.statusText})`;
                    if (window.flutterDevServer) {
                        window.flutterDevServer.updatePipelineProgress('Pipeline status unknown', 0, 'failed');
                        window.flutterDevServer.logAdvanced('error', 'pipeline', errorMsg);
                    }
                    showCriticalError(errorMsg);
                    return;
                }
                return; // Continue checking
            }
            
            const data = await response.json();
            
            if (data.status === 'completed' || data.status === 'failed') {
                clearInterval(interval);
                
                if (window.flutterDevServer) {
                    const finalProgress = data.status === 'completed' ? 100 : 
                                        data.current_step && data.total_steps ? 
                                        Math.round((data.current_step / data.total_steps) * 100) : 50;
                    
                    window.flutterDevServer.updatePipelineProgress(
                        data.current_operation || (data.status === 'completed' ? 'Pipeline completed' : 'Pipeline failed'),
                        finalProgress,
                        data.status
                    );
                    
                    window.flutterDevServer.logAdvanced(
                        data.status === 'completed' ? 'info' : 'error',
                        'pipeline',
                        `Pipeline ${data.status}: ${data.summary || data.error || 'No details available'}`
                    );
                    
                    // Add final step
                    window.flutterDevServer.addPipelineStep(
                        data.status === 'completed' ? 'Pipeline completed successfully' : 'Pipeline failed',
                        data.status,
                        data.summary || data.error || ''
                    );
                    
                    // Trigger hot reload if pipeline completed successfully
                    if (data.status === 'completed') {
                        setTimeout(() => {
                            window.flutterDevServer.triggerFlutterHotReload('AI pipeline completed successfully');
                        }, 2000); // Wait 2 seconds for file system changes to settle
                    }
                }
                return;
            }
            
            // Reset error counter on successful response
            if (attempts > 10) {
                attempts = 10; // Keep some buffer for future errors
            }
            
        } catch (error) {
            console.error('Error checking pipeline status:', error);
            
            if (window.flutterDevServer) {
                window.flutterDevServer.logAdvanced('error', 'pipeline', `Monitoring error: ${error.message}`);
            }
            
            // Stop after too many failures
            if (attempts > 30) {
                clearInterval(interval);
                const errorMsg = `Pipeline monitoring stopped due to repeated errors: ${error.message}`;
                if (window.flutterDevServer) {
                    window.flutterDevServer.updatePipelineProgress('Monitoring failed', 0, 'failed');
                    window.flutterDevServer.logAdvanced('error', 'pipeline', errorMsg);
                }
                showCriticalError(errorMsg);
                return;
            }
        }
        
        // Stop monitoring after max attempts (5 minutes)
        if (attempts >= maxAttempts) {
            clearInterval(interval);
            if (window.flutterDevServer) {
                window.flutterDevServer.updatePipelineProgress('Monitoring timeout', 50, 'failed');
                window.flutterDevServer.logAdvanced('warn', 'pipeline', 'Stopped monitoring after 5 minutes timeout');
            }
        }
    }, 2000); // Check every 2 seconds
}

// Performance monitoring functions
function updatePerformanceMetrics() {
    // Simulate system resource usage (in a real environment, this would come from backend)
    const cpuUsage = Math.random() * 60 + 20; // 20-80%
    const memoryUsage = Math.random() * 40 + 30; // 30-70%
    
    const cpuBar = document.getElementById('cpu-usage');
    const memoryBar = document.getElementById('memory-usage');
    const cpuPercentage = document.getElementById('cpu-percentage');
    const memoryPercentage = document.getElementById('memory-percentage');
    
    if (cpuBar) {
        cpuBar.style.width = `${cpuUsage}%`;
    }
    
    if (cpuPercentage) {
        cpuPercentage.textContent = `${Math.round(cpuUsage)}%`;
    }
    
    if (memoryBar) {
        memoryBar.style.width = `${memoryUsage}%`;
    }
    
    if (memoryPercentage) {
        memoryPercentage.textContent = `${Math.round(memoryUsage)}%`;
    }
    
    // Add performance metric to the log
    const metricsContainer = document.getElementById('performance-metrics');
    if (metricsContainer) {
        const timestamp = new Date().toLocaleTimeString();
        const metricEntry = document.createElement('div');
        metricEntry.className = 'small text-muted mb-1';
        metricEntry.innerHTML = `
            <div class="d-flex justify-content-between">
                <span>${timestamp}</span>
                <span>CPU: ${Math.round(cpuUsage)}% | RAM: ${Math.round(memoryUsage)}%</span>
            </div>
        `;
        
        metricsContainer.appendChild(metricEntry);
        
        // Keep only recent entries
        const entries = metricsContainer.querySelectorAll('div.small');
        if (entries.length > 20) {
            entries[0].remove();
        }
        
        // Auto-scroll to bottom
        metricsContainer.scrollTop = metricsContainer.scrollHeight;
    }
}

function initializePerformanceMonitoring() {
    // Update performance metrics every 3 seconds
    setInterval(updatePerformanceMetrics, 3000);
    
    // Initial update
    updatePerformanceMetrics();
}

// Critical error display
function showCriticalError(message) {
    const alertElement = document.getElementById('critical-error-alert');
    const messageElement = document.getElementById('critical-error-message');
    
    if (alertElement && messageElement) {
        messageElement.textContent = message;
        alertElement.style.display = 'block';
        alertElement.classList.add('show');
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            alertElement.classList.remove('show');
            setTimeout(() => {
                alertElement.style.display = 'none';
            }, 150);
        }, 10000);
    }
    
    // Also log to console and monitoring
    console.error('CRITICAL:', message);
    if (window.flutterDevServer) {
        window.flutterDevServer.logAdvanced('error', 'system', `CRITICAL: ${message}`);
    }
}