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
        this.flutterLoadingDelay = 15000; // 15 seconds default loading delay
        this.flutterReadinessInterval = null;
        this.flutterTimerInterval = null;
        this.flutterLoadingTimeout = null;
        
        this.init();
    }
    
    init() {
        this.initStatusUpdates();
        this.initToasts();
        this.bindGlobalEvents();
        this.loadChatActivity();
        this.initFlutterLoadingHandlers();
        this.ensureFlutterIsRunning();
    }
    
    /**
     * Initialize periodic status updates
     */
    initStatusUpdates() {
        this.updateStatus(); // Initial update only
        console.log('Status polling disabled - manual refresh only');
        // this.statusUpdateInterval = setInterval(() => {
        //     this.updateStatus();
        // }, 10000); // Update every 10 seconds
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
     * Initialize Flutter app loading handlers
     */
    initFlutterLoadingHandlers() {
        const flutterFrame = document.getElementById('flutter-app');
        if (flutterFrame) {
            // Show loading initially
            this.showFlutterLoading();
            
            // Check immediately if Flutter is already ready
            setTimeout(() => {
                if (this.isFlutterReady()) {
                    console.log('✅ Flutter already ready on page load!');
                    this.hideFlutterLoading();
                } else {
                    // Start periodic checking for Flutter readiness
                    this.startFlutterReadinessCheck();
                }
            }, 1000);
            
            // Hide loading when iframe finishes loading (basic fallback)
            flutterFrame.addEventListener('load', () => {
                console.log('🎯 Flutter iframe HTML loaded, waiting for Flutter to initialize...');
                // Don't hide immediately, let the readiness check handle it
            });
            
            // Handle load errors
            flutterFrame.addEventListener('error', () => {
                console.log('❌ Flutter iframe load error');
                this.hideFlutterLoading();
                this.showToast('Failed to load Flutter app', 'danger');
            });
            
            // Additional check: if iframe src changes, show loading
            const originalSrc = flutterFrame.src;
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'src') {
                        if (flutterFrame.src !== originalSrc) {
                            console.log('🔄 Flutter iframe src changed, showing loading');
                            this.showFlutterLoading();
                            this.startFlutterReadinessCheck();
                        }
                    }
                });
            });
            observer.observe(flutterFrame, { attributes: true });
        }
    }
    
    /**
     * Start checking for Flutter app readiness
     */
    startFlutterReadinessCheck() {
        // Clear any existing check
        if (this.flutterReadinessInterval) {
            clearInterval(this.flutterReadinessInterval);
        }
        
        // Simple approach: configurable delay as primary method
        console.log(`⏱️ Starting ${this.flutterLoadingDelay/1000}-second Flutter loading delay...`);
        this.flutterLoadingTimeout = setTimeout(() => {
            console.log(`✅ ${this.flutterLoadingDelay/1000}-second delay complete, hiding loading overlay`);
            this.hideFlutterLoading();
        }, this.flutterLoadingDelay);
        
        // Still do smart detection as a backup to hide earlier if possible
        let attempts = 0;
        const maxAttempts = this.flutterLoadingDelay / 500; // Match the delay timing
        
        this.flutterReadinessInterval = setInterval(() => {
            attempts++;
            
            if (this.isFlutterReady()) {
                console.log('✅ Flutter app ready early! Hiding loading overlay');
                this.hideFlutterLoading();
                clearInterval(this.flutterReadinessInterval);
                this.flutterReadinessInterval = null;
            } else if (attempts >= maxAttempts) {
                // This will be reached at the same time as the setTimeout above
                clearInterval(this.flutterReadinessInterval);
                this.flutterReadinessInterval = null;
            }
        }, 500);
    }
    
    /**
     * Check if Flutter app is ready by multiple methods
     */
    isFlutterReady() {
        const flutterFrame = document.getElementById('flutter-app');
        if (!flutterFrame) return false;
        
        try {
            // Method 1: Check for Flutter-specific elements in iframe
            const iframeDoc = flutterFrame.contentDocument || flutterFrame.contentWindow.document;
            if (iframeDoc) {
                // Look for Flutter canvas or flt-* elements
                const flutterCanvas = iframeDoc.querySelector('flt-scene-host, flt-platform-view, canvas[flt-rendering], .flt-semantics-host');
                if (flutterCanvas) {
                    console.log('🎯 Flutter canvas/elements detected');
                    return true;
                }
                
                // Check for Flutter app div with content
                const flutterApp = iframeDoc.querySelector('#app, [data-flutter-main], .flutter-view');
                if (flutterApp && flutterApp.children.length > 0) {
                    console.log('🎯 Flutter app container with content detected');
                    return true;
                }
                
                // Check if body has substantial content (not just loading screen)
                if (iframeDoc.body && iframeDoc.body.innerHTML.trim().length > 1000) {
                    console.log('🎯 Substantial content detected in iframe');
                    return true;
                }
            }
        } catch (e) {
            // Cross-origin restrictions, fallback to other methods
            console.log('🔒 Cross-origin iframe, using alternate detection');
        }
        
        // Method 2: Check Flutter server status via API
        // this.checkFlutterServerStatus();
        
        return false;
    }
    
    /**
     * Check Flutter server status as fallback
     */
    async checkFlutterServerStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            
            if (data.running && data.ready) {
                console.log('✅ Flutter server reports ready status');
                return true;
            }
        } catch (e) {
            console.log('❌ Flutter status check failed:', e);
        }
        return false;
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
     * Show Flutter loading overlay
     */
    showFlutterLoading() {
        const loadingOverlay = document.getElementById('flutter-loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.remove('d-none');
            this.startLoadingTimer();
            console.log('✨ Showing Flutter loading overlay with timer');
        }
    }
    
    /**
     * Hide Flutter loading overlay
     */
    hideFlutterLoading() {
        const loadingOverlay = document.getElementById('flutter-loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.add('d-none');
            this.stopLoadingTimer();
            
            // Clear the timeout as well
            if (this.flutterLoadingTimeout) {
                clearTimeout(this.flutterLoadingTimeout);
                this.flutterLoadingTimeout = null;
            }
            
            // Clear readiness check interval
            if (this.flutterReadinessInterval) {
                clearInterval(this.flutterReadinessInterval);
                this.flutterReadinessInterval = null;
            }
            
            console.log('✅ Hiding Flutter loading overlay');
        }
    }
    
    /**
     * Start the loading timer countdown
     */
    startLoadingTimer() {
        this.stopLoadingTimer(); // Clear any existing timer
        
        const maxTime = this.flutterLoadingDelay / 1000; // Convert to seconds
        let remainingTime = maxTime;
        
        console.log(`🕐 Starting loading timer: ${remainingTime} seconds`);
        
        // Update immediately
        this.updateLoadingDisplay(remainingTime, maxTime);
        
        this.flutterTimerInterval = setInterval(() => {
            remainingTime--;
            console.log(`⏳ Timer countdown: ${remainingTime}s remaining`);
            this.updateLoadingDisplay(remainingTime, maxTime);
            
            if (remainingTime <= 0) {
                console.log('⏰ Timer reached zero, stopping timer');
                this.stopLoadingTimer();
                // Also hide the loading overlay when timer completes
                this.hideFlutterLoading();
            }
        }, 1000);
    }
    
    /**
     * Stop the loading timer
     */
    stopLoadingTimer() {
        if (this.flutterTimerInterval) {
            clearInterval(this.flutterTimerInterval);
            this.flutterTimerInterval = null;
        }
    }
    
    /**
     * Update loading display with timer and progress
     */
    updateLoadingDisplay(remainingTime, maxTime) {
        const timerElement = document.getElementById('flutter-loading-timer');
        const progressElement = document.getElementById('flutter-loading-progress');
        
        if (timerElement) {
            timerElement.textContent = `${remainingTime}s`;
            
            // Change color as time progresses
            if (remainingTime <= 5) {
                timerElement.className = 'badge bg-warning fs-6 px-3 py-2';
            } else if (remainingTime <= 10) {
                timerElement.className = 'badge bg-primary fs-6 px-3 py-2';
            } else {
                timerElement.className = 'badge bg-info fs-6 px-3 py-2';
            }
        }
        
        if (progressElement) {
            const progressPercent = ((maxTime - remainingTime) / maxTime) * 100;
            progressElement.style.width = `${progressPercent}%`;
            
            // Change progress bar color as time progresses
            if (remainingTime <= 5) {
                progressElement.className = 'progress-bar bg-success';
            } else if (remainingTime <= 10) {
                progressElement.className = 'progress-bar bg-primary';
            } else {
                progressElement.className = 'progress-bar bg-info';
            }
        }
        
        // Update status message
        const statusMessage = document.querySelector('#flutter-loading-overlay small');
        if (statusMessage) {
            const messages = [
                'Initializing Flutter runtime...',
                'Loading Dart VM...',
                'Compiling widgets...',
                'Setting up rendering engine...',
                'Preparing UI components...',
                'Loading application assets...',
                'Finalizing startup sequence...',
                'Almost ready...'
            ];
            
            const messageIndex = Math.floor(((maxTime - remainingTime) / maxTime) * messages.length);
            statusMessage.textContent = messages[Math.min(messageIndex, messages.length - 1)];
        }
    }
    
    /**
     * Refresh Flutter app preview
     */
    refreshApp() {
        const iframe = document.getElementById('flutter-app');
        if (iframe) {
            this.showFlutterLoading();
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
            this.showFlutterLoading();
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
     * Refresh logs immediately
     */
    async refreshLogs() {
        const logContainer = document.getElementById('logs');
        if (logContainer) {
            // Show loading indicator
            logContainer.innerHTML = '<div class="text-muted"><i class="bi bi-arrow-clockwise"></i> Refreshing logs...</div>';
        }
        
        try {
            // Force an immediate update of logs by calling the global function
            if (typeof updateAdvancedLogs === 'function') {
                await updateAdvancedLogs();
                console.log('✅ Logs refreshed successfully');
            } else {
                // Fallback: fetch logs directly
                const response = await fetch('/api/logs');
                const data = await response.json();
                
                // Reset counters to force refresh of all logs
                window.lastFlutterLogCount = 0;
                window.lastMonitoringLogCount = 0;
                
                // Clear the log container first
                if (logContainer) {
                    logContainer.innerHTML = '';
                }
                
                // Process all logs as new logs
                if (data.flutter_logs) {
                    data.flutter_logs.forEach(logLine => {
                        if (logLine.trim()) {
                            let level = 'info';
                            if (logLine.toLowerCase().includes('error') || logLine.toLowerCase().includes('failed')) {
                                level = 'error';
                            } else if (logLine.toLowerCase().includes('warn') || logLine.toLowerCase().includes('warning')) {
                                level = 'warn';
                            } else if (logLine.toLowerCase().includes('debug')) {
                                level = 'debug';
                            }
                            this.logAdvanced(level, 'flutter', logLine);
                        }
                    });
                    window.lastFlutterLogCount = data.flutter_logs.length;
                }
                
                // Process monitoring logs
                if (data.monitoring_logs) {
                    data.monitoring_logs.forEach(logEntry => {
                        if (logEntry.message) {
                            const level = logEntry.level.toLowerCase();
                            const category = logEntry.category.toLowerCase();
                            let message = logEntry.message;
                            
                            if (logEntry.context && Object.keys(logEntry.context).length > 0) {
                                const contextStr = Object.entries(logEntry.context)
                                    .map(([key, value]) => `${key}=${value}`)
                                    .join(', ');
                                message += ` (${contextStr})`;
                            }
                            
                            if (logEntry.duration_ms) {
                                message += ` [${logEntry.duration_ms}ms]`;
                            }
                            
                            this.logAdvanced(level, category, message);
                        }
                    });
                    window.lastMonitoringLogCount = data.monitoring_logs.length;
                }
                
                console.log('✅ Logs refreshed successfully (fallback method)');
            }
        } catch (error) {
            console.error('❌ Failed to refresh logs:', error);
            if (logContainer) {
                logContainer.innerHTML = '<div class="text-danger">Failed to refresh logs: ' + error.message + '</div>';
            }
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
     * Clear all monitoring data
     */
    clearAllLogs() {
        this.clearLogs();
        
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
     * Ensure Flutter is running when page loads
     */
    async ensureFlutterIsRunning() {
        try {
            const response = await fetch(`${this.apiBase}/status`);
            const data = await response.json();
            
            // If Flutter is not running, start it
            if (!data.running) {
                console.log('Flutter not running, starting automatically...');
                this.showToast('Starting Flutter development server...', 'info');
                await this.startFlutter();
            } else if (!data.ready) {
                console.log('Flutter starting up, waiting for ready state...');
                this.showToast('Flutter is starting up...', 'info');
                // Wait a bit and check again
                setTimeout(() => this.ensureFlutterIsRunning(), 3000);
            } else {
                console.log('Flutter is already running and ready');
            }
        } catch (error) {
            console.error('Failed to check Flutter status:', error);
            // Try starting Flutter anyway
            console.log('Starting Flutter due to status check failure...');
            await this.startFlutter();
        }
    }
    
    /**
     * Start Flutter development server
     */
    async startFlutter() {
        try {
            const response = await fetch(`${this.apiBase}/start`, {
                method: 'POST'
            });
            
            if (response.ok) {
                console.log('Flutter start command sent successfully');
                this.showToast('Flutter development server starting...', 'success');
                // Show loading for Flutter app
                this.showFlutterLoading();
            } else {
                console.error('Failed to start Flutter:', response.status);
                this.showToast('Failed to start Flutter development server', 'danger');
            }
        } catch (error) {
            console.error('Error starting Flutter:', error);
            this.showToast('Error starting Flutter development server', 'danger');
        }
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

function showFlutterLoading() {
    return window.flutterDevServer?.showFlutterLoading();
}

function hideFlutterLoading() {
    return window.flutterDevServer?.hideFlutterLoading();
}

function clearLogs() {
    return window.flutterDevServer?.clearLogs();
}

function refreshLogs() {
    return window.flutterDevServer?.refreshLogs();
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
    // Disabled auto-polling for logs - now refresh-only
    console.log('Log polling disabled - refresh manually to update');
    // setInterval(async () => {
    //     try {
    //         await updateAdvancedLogs();
    //     } catch (error) {
    //         console.error('Failed to update advanced logs:', error);
    //     }
    // }, 5000); // Update every 5 seconds
}

async function updateAdvancedLogs() {
    try {
        // Get comprehensive logs (both Flutter and monitoring)
        const response = await fetch('/api/logs');
        const data = await response.json();
        
        if (!window.lastFlutterLogCount) {
            window.lastFlutterLogCount = 0;
        }
        if (!window.lastMonitoringLogCount) {
            window.lastMonitoringLogCount = 0;
        }
        
        // Process Flutter development server logs
        if (data.flutter_logs && data.flutter_logs.length > window.lastFlutterLogCount) {
            const newFlutterLogs = data.flutter_logs.slice(window.lastFlutterLogCount);
            window.lastFlutterLogCount = data.flutter_logs.length;
            
            newFlutterLogs.forEach(logLine => {
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
        
        // Process advanced monitoring logs
        if (data.monitoring_logs && data.monitoring_logs.length > window.lastMonitoringLogCount) {
            const newMonitoringLogs = data.monitoring_logs.slice(window.lastMonitoringLogCount);
            window.lastMonitoringLogCount = data.monitoring_logs.length;
            
            newMonitoringLogs.forEach(logEntry => {
                if (window.flutterDevServer && logEntry.message) {
                    // Use the structured log data directly
                    const level = logEntry.level.toLowerCase();
                    const category = logEntry.category.toLowerCase();
                    let message = logEntry.message;
                    
                    // Add context information if available
                    if (logEntry.context && Object.keys(logEntry.context).length > 0) {
                        const contextStr = Object.entries(logEntry.context)
                            .map(([key, value]) => `${key}=${value}`)
                            .join(', ');
                        message += ` (${contextStr})`;
                    }
                    
                    // Add timing information if available
                    if (logEntry.duration_ms) {
                        message += ` [${logEntry.duration_ms}ms]`;
                    }
                    
                    window.flutterDevServer.logAdvanced(level, category, message);
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
    // Disabled auto-polling for performance metrics - manual refresh only
    console.log('Performance metrics polling disabled - manual refresh only');
    // setInterval(updatePerformanceMetrics, 3000);
    
    // Initial update only
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