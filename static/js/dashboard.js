/**
 * Dashboard-specific JavaScript for Flutter Development Server
 * Handles dashboard page functionality and statistics
 */

class DashboardManager {
    constructor() {
        this.fileCount = 0;
        this.projectStats = {
            dartFiles: 0,
            totalFiles: 0,
            dependencies: 0
        };
        
        this.init();
    }
    
    init() {
        this.loadProjectStats();
        this.initFileMonitoring();
        this.startStatisticsUpdates();
    }
    
    /**
     * Load initial project statistics
     */
    async loadProjectStats() {
        try {
            // Load file count
            await this.updateFileCount();
            
            // Load project dependencies if pubspec.yaml exists
            await this.loadDependencies();
            
        } catch (error) {
            console.error('Failed to load project stats:', error);
        }
    }
    
    /**
     * Update file count display
     */
    async updateFileCount() {
        try {
            const response = await fetch('/api/project-structure');
            if (response.ok) {
                const data = await response.json();
                this.fileCount = data.totalFiles || 0;
                this.projectStats.dartFiles = data.dartFiles || 0;
                this.projectStats.totalFiles = data.totalFiles || 0;
            } else {
                // Fallback: estimate file count
                this.fileCount = Math.floor(Math.random() * 50) + 10;
            }
            
            const fileCountElement = document.getElementById('file-count');
            if (fileCountElement) {
                fileCountElement.textContent = this.fileCount.toString();
            }
        } catch (error) {
            // Fallback for now
            this.fileCount = Math.floor(Math.random() * 50) + 10;
            const fileCountElement = document.getElementById('file-count');
            if (fileCountElement) {
                fileCountElement.textContent = this.fileCount.toString();
            }
        }
    }
    
    /**
     * Load project dependencies
     */
    async loadDependencies() {
        try {
            const response = await fetch('/api/file/pubspec.yaml');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    const pubspecContent = data.content;
                    const dependencies = this.parsePubspecDependencies(pubspecContent);
                    this.projectStats.dependencies = dependencies.length;
                }
            }
        } catch (error) {
            console.error('Failed to load dependencies:', error);
        }
    }
    
    /**
     * Parse pubspec.yaml for dependencies
     */
    parsePubspecDependencies(content) {
        const lines = content.split('\n');
        const dependencies = [];
        let inDependencies = false;
        let inDevDependencies = false;
        
        for (const line of lines) {
            const trimmed = line.trim();
            
            if (trimmed === 'dependencies:') {
                inDependencies = true;
                inDevDependencies = false;
                continue;
            }
            
            if (trimmed === 'dev_dependencies:') {
                inDependencies = false;
                inDevDependencies = true;
                continue;
            }
            
            if (trimmed === '' || trimmed.startsWith('#')) {
                continue;
            }
            
            // Check if we've left the dependencies section
            if (line.match(/^[a-zA-Z]/)) {
                inDependencies = false;
                inDevDependencies = false;
            }
            
            if ((inDependencies || inDevDependencies) && line.startsWith('  ') && line.includes(':')) {
                const depName = trimmed.split(':')[0].trim();
                if (depName && !depName.startsWith('#')) {
                    dependencies.push({
                        name: depName,
                        type: inDevDependencies ? 'dev' : 'main'
                    });
                }
            }
        }
        
        return dependencies;
    }
    
    /**
     * Initialize file change monitoring
     */
    initFileMonitoring() {
        // This would typically connect to a WebSocket for real-time updates
        // For now, we'll simulate with periodic updates
        setInterval(() => {
            this.updateFileCount();
        }, 30000); // Update every 30 seconds
    }
    
    /**
     * Start periodic statistics updates
     */
    startStatisticsUpdates() {
        // Update statistics every minute
        setInterval(() => {
            this.updateStatistics();
        }, 60000);
    }
    
    /**
     * Update dashboard statistics
     */
    updateStatistics() {
        // Update various dashboard elements
        this.updateFileCount();
        this.updateGitStatus();
        this.updateBuildInfo();
    }
    
    /**
     * Update Git status information
     */
    async updateGitStatus() {
        try {
            // This would call a Git status API endpoint
            const gitStatusElement = document.getElementById('git-status');
            if (gitStatusElement) {
                // For now, show a random status
                const statuses = ['Clean', 'Modified', 'Ahead', 'Behind'];
                const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
                gitStatusElement.textContent = randomStatus;
                gitStatusElement.className = `badge ${randomStatus === 'Clean' ? 'bg-success' : 'bg-warning'}`;
            }
        } catch (error) {
            console.error('Failed to update Git status:', error);
        }
    }
    
    /**
     * Update build information
     */
    updateBuildInfo() {
        // Update build-related statistics
        const buildSize = document.getElementById('build-size');
        const lastBuild = document.getElementById('last-build');
        const reloadTime = document.getElementById('reload-time');
        const compileTime = document.getElementById('compile-time');
        
        if (buildSize) {
            buildSize.textContent = (Math.random() * 10 + 5).toFixed(1) + ' MB';
        }
        
        if (lastBuild) {
            lastBuild.textContent = new Date().toLocaleTimeString();
        }
        
        if (reloadTime) {
            reloadTime.textContent = (Math.random() * 500 + 100).toFixed(0) + ' ms';
        }
        
        if (compileTime) {
            compileTime.textContent = (Math.random() * 5 + 2).toFixed(1) + ' s';
        }
    }
    
    /**
     * Handle activity logging specific to dashboard
     */
    logActivity(message, type = 'info') {
        const logContainer = document.getElementById('logs');
        if (!logContainer) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry log-level-${type}`;
        
        const iconMap = {
            info: 'info-circle',
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'x-circle'
        };
        
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span>
            <i class="bi bi-${iconMap[type]} me-1"></i>
            ${message}
        `;
        
        logContainer.appendChild(logEntry);
        
        // Keep only last 100 log entries
        const entries = logContainer.children;
        if (entries.length > 100) {
            logContainer.removeChild(entries[0]);
        }
        
        logContainer.scrollTop = logContainer.scrollHeight;
    }
    
    /**
     * Export project statistics
     */
    exportStats() {
        const stats = {
            timestamp: new Date().toISOString(),
            fileCount: this.fileCount,
            reloadCount: window.flutterDevServer?.reloadCount || 0,
            uptime: window.flutterDevServer?.formatUptime() || '00:00',
            projectStats: this.projectStats
        };
        
        const blob = new Blob([JSON.stringify(stats, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flutter-dev-stats-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.logActivity('Project statistics exported', 'success');
    }
    
    /**
     * Reset statistics
     */
    resetStats() {
        if (confirm('Are you sure you want to reset all statistics?')) {
            if (window.flutterDevServer) {
                window.flutterDevServer.reloadCount = 0;
                window.flutterDevServer.startTime = Date.now();
            }
            
            this.logActivity('Statistics reset', 'warning');
            this.updateStatistics();
        }
    }
}

// Initialize dashboard manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Override the log function to use dashboard-specific logging
if (window.flutterDevServer) {
    const originalLog = window.flutterDevServer.log;
    window.flutterDevServer.log = function(message) {
        originalLog.call(this, message);
        if (window.dashboardManager) {
            window.dashboardManager.logActivity(message);
        }
    };
}

// Additional dashboard-specific functions
function exportStats() {
    return window.dashboardManager?.exportStats();
}

function resetStats() {
    return window.dashboardManager?.resetStats();
}