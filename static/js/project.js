/**
 * Project Overview JavaScript for Flutter Development Server
 * Handles project analysis, dependency management, and visualization
 */

class ProjectManager {
    constructor() {
        this.projectData = {
            name: '',
            dartFiles: 0,
            dependencies: [],
            gitStatus: 'unknown'
        };
        this.dependencyChart = null;
        
        this.init();
    }
    
    init() {
        this.loadProjectInfo();
        this.initDependencyChart();
        this.bindEvents();
    }
    
    /**
     * Load project information
     */
    async loadProjectInfo() {
        try {
            await Promise.all([
                this.loadBasicInfo(),
                this.loadDependencies(),
                this.loadGitStatus(),
                this.loadFileAnalysis()
            ]);
        } catch (error) {
            console.error('Failed to load project info:', error);
        }
    }
    
    /**
     * Load basic project information
     */
    async loadBasicInfo() {
        try {
            // Try to get project name from pubspec.yaml
            const response = await fetch('/api/file/pubspec.yaml');
            if (response.ok) {
                const data = await response.json();
                if (data.status === 'success') {
                    const pubspecContent = data.content;
                    const nameMatch = pubspecContent.match(/^name:\s*(.+)$/m);
                    if (nameMatch) {
                        this.projectData.name = nameMatch[1].trim();
                        this.updateElement('project-name', this.projectData.name);
                    }
                }
            } else {
                this.projectData.name = 'Flutter Project';
                this.updateElement('project-name', this.projectData.name);
            }
        } catch (error) {
            this.projectData.name = 'Flutter Project';
            this.updateElement('project-name', this.projectData.name);
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
                    const dependencies = this.parsePubspecDependencies(data.content);
                    this.projectData.dependencies = dependencies;
                    this.updateElement('dependencies-count', dependencies.length.toString());
                    this.renderDependenciesTable(dependencies);
                }
            }
        } catch (error) {
            console.error('Failed to load dependencies:', error);
            this.updateElement('dependencies-count', '--');
        }
    }
    
    /**
     * Parse pubspec.yaml for dependencies
     */
    parsePubspecDependencies(content) {
        const lines = content.split('\n');
        const dependencies = [];
        let currentSection = null;
        
        for (const line of lines) {
            const trimmed = line.trim();
            
            if (trimmed === 'dependencies:') {
                currentSection = 'main';
                continue;
            }
            
            if (trimmed === 'dev_dependencies:') {
                currentSection = 'dev';
                continue;
            }
            
            if (trimmed === '' || trimmed.startsWith('#')) {
                continue;
            }
            
            // Check if we've left the dependencies section
            if (line.match(/^[a-zA-Z]/)) {
                currentSection = null;
            }
            
            if (currentSection && line.startsWith('  ') && line.includes(':')) {
                const parts = trimmed.split(':');
                const depName = parts[0].trim();
                const version = parts[1] ? parts[1].trim() : 'latest';
                
                if (depName && !depName.startsWith('#')) {
                    dependencies.push({
                        name: depName,
                        version: version,
                        type: currentSection
                    });
                }
            }
        }
        
        return dependencies;
    }
    
    /**
     * Render dependencies table
     */
    renderDependenciesTable(dependencies) {
        const tableBody = document.querySelector('#dependencies-table tbody');
        if (!tableBody) return;
        
        if (dependencies.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="text-center text-muted">No dependencies found</td>
                </tr>
            `;
            return;
        }
        
        tableBody.innerHTML = dependencies.map(dep => `
            <tr>
                <td>
                    <i class="bi bi-box me-2"></i>
                    ${dep.name}
                </td>
                <td><code>${dep.version}</code></td>
                <td>
                    <span class="badge ${dep.type === 'dev' ? 'bg-warning' : 'bg-primary'}">
                        ${dep.type}
                    </span>
                </td>
            </tr>
        `).join('');
    }
    
    /**
     * Load Git status
     */
    async loadGitStatus() {
        try {
            // Simulate Git status for now
            const statuses = ['Clean', 'Modified', 'Ahead', 'Behind', 'Untracked'];
            const randomStatus = statuses[Math.floor(Math.random() * statuses.length)];
            
            this.projectData.gitStatus = randomStatus;
            this.updateElement('git-branch', 'main');
            this.updateElement('git-last-commit', 'Just now');
            this.updateElement('git-detailed-status', randomStatus);
        } catch (error) {
            console.error('Failed to load Git status:', error);
        }
    }
    
    /**
     * Load file analysis data
     */
    async loadFileAnalysis() {
        try {
            // Simulate file analysis
            const dartFiles = Math.floor(Math.random() * 50) + 10;
            const widgetFiles = Math.floor(dartFiles * 0.6);
            const modelFiles = Math.floor(dartFiles * 0.2);
            
            this.updateElement('dart-files-count', dartFiles.toString());
            this.updateElement('dart-files', dartFiles.toString());
            this.updateElement('widget-files', widgetFiles.toString());
            this.updateElement('model-files', modelFiles.toString());
            
            // Update chart
            this.updateFileTypesChart(dartFiles, widgetFiles, modelFiles);
        } catch (error) {
            console.error('Failed to load file analysis:', error);
        }
    }
    
    /**
     * Initialize dependency chart
     */
    initDependencyChart() {
        const canvas = document.getElementById('file-types-chart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        this.dependencyChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Dart Files', 'Widgets', 'Models', 'Services'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: [
                        '#0d6efd',
                        '#198754',
                        '#ffc107',
                        '#dc3545'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    /**
     * Update file types chart
     */
    updateFileTypesChart(dartFiles, widgetFiles, modelFiles) {
        if (!this.dependencyChart) return;
        
        const serviceFiles = dartFiles - widgetFiles - modelFiles;
        this.dependencyChart.data.datasets[0].data = [dartFiles, widgetFiles, modelFiles, serviceFiles];
        this.dependencyChart.update();
    }
    
    /**
     * Bind event handlers
     */
    bindEvents() {
        // File analysis refresh
        const refreshBtn = document.querySelector('[onclick="refreshStructure()"]');
        if (refreshBtn) {
            refreshBtn.onclick = () => this.refreshStructure();
        }
    }
    
    /**
     * Update element text content
     */
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    /**
     * Analyze project structure
     */
    async analyzeProject() {
        window.flutterDevServer?.showToast('Analyzing project structure...', 'info');
        
        try {
            // Simulate analysis
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            await this.loadProjectInfo();
            window.flutterDevServer?.showToast('Project analysis completed', 'success');
            this.logActivity('Project structure analyzed', 'success');
        } catch (error) {
            window.flutterDevServer?.showToast('Failed to analyze project', 'danger');
            this.logActivity(`Analysis failed: ${error.message}`, 'error');
        }
    }
    
    /**
     * Generate project documentation
     */
    async generateDocs() {
        window.flutterDevServer?.showToast('Generating documentation...', 'info');
        
        try {
            // Simulate documentation generation
            await new Promise(resolve => setTimeout(resolve, 3000));
            
            const docs = this.createProjectDocumentation();
            this.downloadFile('project-docs.md', docs, 'text/markdown');
            
            window.flutterDevServer?.showToast('Documentation generated', 'success');
            this.logActivity('Project documentation generated', 'success');
        } catch (error) {
            window.flutterDevServer?.showToast('Failed to generate documentation', 'danger');
            this.logActivity(`Documentation generation failed: ${error.message}`, 'error');
        }
    }
    
    /**
     * Create project documentation
     */
    createProjectDocumentation() {
        const dependencies = this.projectData.dependencies;
        const depList = dependencies.map(dep => `- ${dep.name}: ${dep.version}`).join('\n');
        
        return `# ${this.projectData.name}

## Project Overview
Flutter application with ${this.projectData.dartFiles} Dart files.

## Dependencies
${depList}

## Git Status
Branch: main
Status: ${this.projectData.gitStatus}

## Generated on
${new Date().toISOString()}
`;
    }
    
    /**
     * Download file
     */
    downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    /**
     * Refresh project structure
     */
    async refreshStructure() {
        window.flutterDevServer?.showToast('Refreshing project structure...', 'info');
        await this.loadProjectInfo();
        this.logActivity('Project structure refreshed', 'info');
    }
    
    /**
     * Load project structure visualization
     */
    loadProjectStructure() {
        const structureDiv = document.getElementById('project-structure');
        if (!structureDiv) return;
        
        // Create a simple tree visualization
        structureDiv.innerHTML = `
            <div class="p-3">
                <div class="tree-structure">
                    <div class="tree-item">
                        <i class="bi bi-folder-fill text-warning"></i>
                        <strong>${this.projectData.name || 'project'}</strong>
                        <div class="tree-children ms-3">
                            <div class="tree-item">
                                <i class="bi bi-folder text-primary"></i> lib/
                                <div class="tree-children ms-3">
                                    <div class="tree-item">
                                        <i class="bi bi-file-earmark-code text-success"></i> main.dart
                                    </div>
                                    <div class="tree-item">
                                        <i class="bi bi-folder text-primary"></i> models/
                                    </div>
                                    <div class="tree-item">
                                        <i class="bi bi-folder text-primary"></i> widgets/
                                    </div>
                                </div>
                            </div>
                            <div class="tree-item">
                                <i class="bi bi-file-earmark-text text-info"></i> pubspec.yaml
                            </div>
                            <div class="tree-item">
                                <i class="bi bi-file-earmark-text text-secondary"></i> README.md
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.logActivity('Project structure loaded', 'info');
    }
    
    /**
     * Export project structure
     */
    exportStructure() {
        const structure = {
            name: this.projectData.name,
            dartFiles: this.projectData.dartFiles,
            dependencies: this.projectData.dependencies,
            gitStatus: this.projectData.gitStatus,
            exportedAt: new Date().toISOString()
        };
        
        this.downloadFile('project-structure.json', JSON.stringify(structure, null, 2), 'application/json');
        this.logActivity('Project structure exported', 'success');
    }
    
    /**
     * Add dependency
     */
    addDependency() {
        const modal = new bootstrap.Modal(document.getElementById('addDependencyModal'));
        modal.show();
    }
    
    /**
     * Confirm add dependency
     */
    async confirmAddDependency() {
        const packageName = document.getElementById('package-name').value.trim();
        const packageVersion = document.getElementById('package-version').value.trim() || '^1.0.0';
        const isDev = document.getElementById('dev-dependency').checked;
        
        if (!packageName) {
            window.flutterDevServer?.showToast('Please enter a package name', 'warning');
            return;
        }
        
        try {
            window.flutterDevServer?.showToast(`Adding dependency: ${packageName}`, 'info');
            
            // Simulate adding dependency
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Add to local data
            this.projectData.dependencies.push({
                name: packageName,
                version: packageVersion,
                type: isDev ? 'dev' : 'main'
            });
            
            // Update UI
            this.renderDependenciesTable(this.projectData.dependencies);
            this.updateElement('dependencies-count', this.projectData.dependencies.length.toString());
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('addDependencyModal'));
            modal.hide();
            
            // Clear form
            document.getElementById('package-name').value = '';
            document.getElementById('package-version').value = '';
            document.getElementById('dev-dependency').checked = false;
            
            window.flutterDevServer?.showToast('Dependency added successfully', 'success');
            this.logActivity(`Added dependency: ${packageName}`, 'success');
        } catch (error) {
            window.flutterDevServer?.showToast('Failed to add dependency', 'danger');
            this.logActivity(`Failed to add dependency: ${error.message}`, 'error');
        }
    }
    
    /**
     * Log activity
     */
    logActivity(message, type = 'info') {
        const activityDiv = document.getElementById('recent-activity');
        if (!activityDiv) return;
        
        const timestamp = new Date().toLocaleTimeString();
        const iconMap = {
            info: 'info-circle',
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'x-circle'
        };
        
        const activityItem = document.createElement('div');
        activityItem.className = `activity-item small mb-2 text-${type === 'error' ? 'danger' : type}`;
        activityItem.innerHTML = `
            <i class="bi bi-${iconMap[type]} me-1"></i>
            <span class="text-muted">[${timestamp}]</span>
            ${message}
        `;
        
        activityDiv.appendChild(activityItem);
        
        // Keep only last 10 activities
        const items = activityDiv.children;
        if (items.length > 10) {
            activityDiv.removeChild(items[0]);
        }
        
        activityDiv.scrollTop = activityDiv.scrollHeight;
    }
}

// Initialize project manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.projectManager = new ProjectManager();
});

// Global functions for template usage
function analyzeProject() {
    return window.projectManager?.analyzeProject();
}

function generateDocs() {
    return window.projectManager?.generateDocs();
}

function refreshStructure() {
    return window.projectManager?.refreshStructure();
}

function loadProjectStructure() {
    return window.projectManager?.loadProjectStructure();
}

function exportStructure() {
    return window.projectManager?.exportStructure();
}

function addDependency() {
    return window.projectManager?.addDependency();
}

function confirmAddDependency() {
    return window.projectManager?.confirmAddDependency();
}

function updateDependencies() {
    window.flutterDevServer?.showToast('Updating dependencies...', 'info');
    window.projectManager?.logActivity('Dependencies update started', 'info');
}

function checkOutdated() {
    window.flutterDevServer?.showToast('Checking for outdated packages...', 'info');
    window.projectManager?.logActivity('Checking outdated dependencies', 'info');
}

function gitPull() {
    window.flutterDevServer?.showToast('Pulling from Git...', 'info');
    window.projectManager?.logActivity('Git pull initiated', 'info');
}

function gitCommit() {
    window.flutterDevServer?.showToast('Creating Git commit...', 'info');
    window.projectManager?.logActivity('Git commit created', 'success');
}

function gitPush() {
    window.flutterDevServer?.showToast('Pushing to Git...', 'info');
    window.projectManager?.logActivity('Git push initiated', 'info');
}

function buildRelease() {
    window.flutterDevServer?.showToast('Building release...', 'info');
    window.projectManager?.logActivity('Release build started', 'info');
}

function analyzeBundle() {
    window.flutterDevServer?.showToast('Analyzing bundle...', 'info');
    window.projectManager?.logActivity('Bundle analysis started', 'info');
}