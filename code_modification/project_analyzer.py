"""
Flutter Project Analyzer
Analyzes Flutter projects to understand structure, dependencies, and patterns
"""

import os
import re
import yaml
import time
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel
    from utils.performance_monitor import performance_monitor, TimingContext
    from utils.error_analyzer import error_analyzer
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Empty context manager for backward compatibility
class EmptyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@dataclass
class DartFile:
    """Represents a Dart file in the project"""
    path: str
    name: str
    content: str = ""
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    widgets: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    is_widget: bool = False
    is_model: bool = False
    is_service: bool = False


@dataclass
class Dependency:
    """Represents a project dependency"""
    name: str
    version: str
    is_dev: bool = False
    description: str = ""


@dataclass
class ProjectStructure:
    """Represents the complete project structure"""
    name: str
    description: str = ""
    dart_files: List[DartFile] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)
    total_files: int = 0
    lib_structure: Dict[str, List[str]] = field(default_factory=dict)
    directories: Dict[str, int] = field(default_factory=dict)
    patterns_detected: List[str] = field(default_factory=list)
    architecture_pattern: str = "unknown"


class FlutterProjectAnalyzer:
    """
    Analyzes Flutter projects to understand their structure and patterns
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.pubspec_path = self.project_path / "pubspec.yaml"
        self.lib_path = self.project_path / "lib"
        
        # Common Flutter patterns
        self.widget_patterns = [
            r'class\s+(\w+)\s+extends\s+StatelessWidget',
            r'class\s+(\w+)\s+extends\s+StatefulWidget',
            r'class\s+(\w+)\s+extends\s+Widget',
            r'class\s+(\w+)\s+extends\s+.*Widget',
        ]
        
        self.model_patterns = [
            r'class\s+(\w+)\s*{',  # Simple class
            r'class\s+(\w+)\s+extends\s+\w*Model',
            r'class\s+(\w+)\s+with\s+.*Model',
        ]
        
        self.service_patterns = [
            r'class\s+(\w+)Service',
            r'class\s+(\w+)Repository',
            r'class\s+(\w+)Provider',
            r'class\s+(\w+)Client',
        ]
    
    def analyze(self) -> ProjectStructure:
        """
        Perform complete project analysis
        
        Returns:
            ProjectStructure containing all analyzed data
        """
        start_time = time.time()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.PROJECT_ANALYSIS, "Starting Flutter project analysis", 
                       context={
                           "project_path": str(self.project_path),
                           "pubspec_exists": self.pubspec_path.exists(),
                           "lib_exists": self.lib_path.exists()
                       })
        
        print(f"Analyzing Flutter project at: {self.project_path}")
        
        try:
            # Initialize project structure
            project_structure = ProjectStructure(name="Unknown Project")
            
            # Analyze pubspec.yaml
            self._analyze_pubspec(project_structure)
            
            # Analyze Dart files
            self._analyze_dart_files(project_structure)
            
            # Analyze project structure
            self._analyze_lib_structure(project_structure)
            
            # Detect architecture pattern
            self._detect_architecture_pattern(project_structure)
            
            # Enhanced completion logging
            analysis_duration = time.time() - start_time
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.PROJECT_ANALYSIS, "Project analysis completed successfully",
                           context={
                               "project_name": project_structure.name,
                               "dart_files_count": len(project_structure.dart_files),
                               "dependencies_count": len(project_structure.dependencies),
                               "total_files": project_structure.total_files,
                               "architecture_pattern": project_structure.architecture_pattern,
                               "patterns_detected": project_structure.patterns_detected,
                               "lib_structure": project_structure.lib_structure,
                               "analysis_duration_seconds": round(analysis_duration, 2)
                           })
            
            print(f"Analysis complete: {len(project_structure.dart_files)} Dart files, {len(project_structure.dependencies)} dependencies")
            return project_structure
            
        except Exception as e:
            error_message = str(e)
            
            analysis_duration = time.time() - start_time
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.PROJECT_ANALYSIS, f"Project analysis failed: {error_message}",
                           context={
                               "project_path": str(self.project_path),
                               "analysis_duration_seconds": round(analysis_duration, 2),
                               "error_type": type(e).__name__
                           })
            
            print(f"Error during project analysis: {error_message}")
            raise
    
    def _analyze_pubspec(self, structure: ProjectStructure):
        """Analyze pubspec.yaml file"""
        if not self.pubspec_path.exists():
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.PROJECT_ANALYSIS, "pubspec.yaml not found in project")
            print("pubspec.yaml not found")
            return
        
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.PROJECT_ANALYSIS, "Analyzing pubspec.yaml")
        
        try:
            with open(self.pubspec_path, 'r', encoding='utf-8') as f:
                pubspec_data = yaml.safe_load(f)
            
            # Extract basic info
            structure.name = pubspec_data.get('name', 'Unknown Project')
            structure.description = pubspec_data.get('description', '')
            
            # Extract dependencies
            deps = pubspec_data.get('dependencies', {})
            dev_deps = pubspec_data.get('dev_dependencies', {})
            
            for name, version in deps.items():
                if name != 'flutter':  # Skip flutter SDK
                    structure.dependencies.append(Dependency(
                        name=name,
                        version=str(version),
                        is_dev=False
                    ))
            
            for name, version in dev_deps.items():
                structure.dependencies.append(Dependency(
                    name=name,
                    version=str(version),
                    is_dev=True
                ))
            
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.PROJECT_ANALYSIS, f"Pubspec analysis completed",
                           context={
                               "project_name": structure.name,
                               "dependencies_count": len([d for d in structure.dependencies if not d.is_dev]),
                               "dev_dependencies_count": len([d for d in structure.dependencies if d.is_dev]),
                               "total_dependencies": len(structure.dependencies),
                               "flutter_version": deps.get('flutter'),
                               "dart_version": pubspec_data.get('environment', {}).get('sdk')
                           })
            
            print(f"Found {len(structure.dependencies)} dependencies")
            
        except Exception as e:
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.PROJECT_ANALYSIS, f"Error analyzing pubspec.yaml: {str(e)}")
            print(f"Error analyzing pubspec.yaml: {e}")
    
    def _analyze_dart_files(self, structure: ProjectStructure):
        """Analyze all Dart files in the project"""
        if not self.lib_path.exists():
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.PROJECT_ANALYSIS, "lib directory not found in project")
            print("lib directory not found")
            return
        
        if MONITORING_AVAILABLE:
            logger.debug(LogCategory.PROJECT_ANALYSIS, "Starting Dart files analysis")
        
        dart_files = list(self.lib_path.rglob("*.dart"))
        structure.total_files = len(dart_files)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.PROJECT_ANALYSIS, f"Found {len(dart_files)} Dart files to analyze")
        
        print(f"Found {len(dart_files)} Dart files")
        
        for file_path in dart_files:
            try:
                dart_file = self._analyze_dart_file(file_path)
                structure.dart_files.append(dart_file)
            except Exception as e:
                print(f"Error analyzing {file_path}: {e}")
    
    def _analyze_dart_file(self, file_path: Path) -> DartFile:
        """Analyze a single Dart file"""
        relative_path = file_path.relative_to(self.project_path)
        
        dart_file = DartFile(
            path=str(relative_path),
            name=file_path.name
        )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                dart_file.content = content
            
            # Analyze imports and exports
            dart_file.imports = self._extract_imports(content)
            dart_file.exports = self._extract_exports(content)
            
            # Analyze classes, widgets, functions
            dart_file.classes = self._extract_classes(content)
            dart_file.widgets = self._extract_widgets(content)
            dart_file.functions = self._extract_functions(content)
            
            # Classify file type
            dart_file.is_widget = len(dart_file.widgets) > 0 or any(
                pattern in content for pattern in ['Widget', 'StatelessWidget', 'StatefulWidget']
            )
            
            dart_file.is_model = (
                'models/' in str(relative_path) or 
                any(re.search(pattern, content) for pattern in self.model_patterns)
            ) and not dart_file.is_widget
            
            dart_file.is_service = (
                any(keyword in str(relative_path) for keyword in ['service', 'repository', 'provider']) or
                any(re.search(pattern, content) for pattern in self.service_patterns)
            ) and not dart_file.is_widget
            
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
        
        return dart_file
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Dart content"""
        import_pattern = r"import\s+['\"]([^'\"]+)['\"]"
        return re.findall(import_pattern, content)
    
    def _extract_exports(self, content: str) -> List[str]:
        """Extract export statements from Dart content"""
        export_pattern = r"export\s+['\"]([^'\"]+)['\"]"
        return re.findall(export_pattern, content)
    
    def _extract_classes(self, content: str) -> List[str]:
        """Extract class names from Dart content"""
        class_pattern = r"class\s+(\w+)"
        return re.findall(class_pattern, content)
    
    def _extract_widgets(self, content: str) -> List[str]:
        """Extract widget class names from Dart content"""
        widgets = []
        for pattern in self.widget_patterns:
            widgets.extend(re.findall(pattern, content))
        return widgets
    
    def _extract_functions(self, content: str) -> List[str]:
        """Extract function names from Dart content"""
        # Match top-level functions and methods
        function_patterns = [
            r"^\s*(\w+)\s+(\w+)\s*\([^)]*\)\s*{",  # returnType functionName(params)
            r"^\s*(\w+)\s*\([^)]*\)\s*{",  # functionName(params)
        ]
        
        functions = []
        for pattern in function_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            if pattern.count('(') == 2:  # Two capture groups
                functions.extend([match[1] for match in matches if match[1] not in ['class', 'enum', 'mixin']])
            else:  # One capture group
                functions.extend([match for match in matches if match not in ['class', 'enum', 'mixin']])
        
        return functions
    
    def _analyze_lib_structure(self, structure: ProjectStructure):
        """Analyze the lib directory structure"""
        if not self.lib_path.exists():
            print("lib directory not found")
            return
        
        structure.lib_structure = {}
        structure.directories = {}
        
        # Walk through lib directory
        for root, dirs, files in os.walk(self.lib_path):
            relative_root = Path(root).relative_to(self.lib_path)
            dart_files = [f for f in files if f.endswith('.dart')]
            
            if dart_files:
                structure.lib_structure[str(relative_root)] = dart_files
                
            # Count files in each directory for the directories attribute
            structure.directories[str(relative_root)] = len(dart_files)
        
        print(f"Lib structure: {len(structure.lib_structure)} directories")
    
    def _detect_architecture_pattern(self, structure: ProjectStructure):
        """Detect the architecture pattern used in the project"""
        directories = set()
        for dart_file in structure.dart_files:
            dir_parts = Path(dart_file.path).parent.parts
            if dir_parts:
                directories.update(dir_parts)
        
        # Initialize patterns_detected list
        structure.patterns_detected = []
        
        # Common architecture patterns
        if 'bloc' in directories or any('bloc' in dep.name for dep in structure.dependencies):
            structure.architecture_pattern = 'BLoC'
            structure.patterns_detected.append('bloc')
        elif 'provider' in directories or any('provider' in dep.name for dep in structure.dependencies):
            structure.architecture_pattern = 'Provider'
            structure.patterns_detected.append('provider')
        elif 'riverpod' in directories or any('riverpod' in dep.name for dep in structure.dependencies):
            structure.architecture_pattern = 'Riverpod'
            structure.patterns_detected.append('riverpod')
        elif 'cubit' in directories:
            structure.architecture_pattern = 'Cubit'
            structure.patterns_detected.append('cubit')
        elif any(keyword in directories for keyword in ['mvvm', 'view_model']):
            structure.architecture_pattern = 'MVVM'
            structure.patterns_detected.append('mvvm')
        elif any(keyword in directories for keyword in ['mvc', 'controller']):
            structure.architecture_pattern = 'MVC'
            structure.patterns_detected.append('mvc')
        elif any(keyword in directories for keyword in ['feature', 'features']):
            structure.architecture_pattern = 'Feature-based'
            structure.patterns_detected.append('feature_based')
        else:
            structure.architecture_pattern = 'Standard'
            structure.patterns_detected.append('standard')
        
        print(f"Detected architecture pattern: {structure.architecture_pattern}")
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """
        Get dependencies for a specific file
        
        Args:
            file_path: Path to the Dart file
            
        Returns:
            List of file paths that this file depends on
        """
        dart_file = None
        for df in self.analyze().dart_files:
            if df.path == file_path:
                dart_file = df
                break
        
        if not dart_file:
            return []
        
        dependencies = []
        for import_path in dart_file.imports:
            if import_path.startswith('package:'):
                # External package dependency
                continue
            elif import_path.startswith('./') or import_path.startswith('../'):
                # Relative import - resolve to absolute path
                resolved_path = self._resolve_relative_import(file_path, import_path)
                if resolved_path:
                    dependencies.append(resolved_path)
            else:
                # Absolute import within project
                dependencies.append(import_path)
        
        return dependencies
    
    def _resolve_relative_import(self, current_file: str, import_path: str) -> Optional[str]:
        """Resolve relative import to absolute path"""
        try:
            current_dir = Path(current_file).parent
            resolved = (current_dir / import_path).resolve()
            project_relative = resolved.relative_to(self.project_path)
            return str(project_relative)
        except (ValueError, OSError):
            return None
    
    def get_files_that_depend_on(self, target_file: str) -> List[str]:
        """
        Get files that depend on the target file
        
        Args:
            target_file: Path to the target file
            
        Returns:
            List of file paths that depend on the target file
        """
        dependent_files = []
        project_structure = self.analyze()
        
        for dart_file in project_structure.dart_files:
            dependencies = self.get_file_dependencies(dart_file.path)
            if target_file in dependencies:
                dependent_files.append(dart_file.path)
        
        return dependent_files
    
    def suggest_files_for_modification(self, change_description: str) -> List[str]:
        """
        Suggest files that might need modification based on change description
        
        Args:
            change_description: Description of the desired changes
            
        Returns:
            List of file paths that might need modification
        """
        suggested_files = []
        project_structure = self.analyze()
        
        # Simple keyword-based suggestions
        keywords = change_description.lower().split()
        
        for dart_file in project_structure.dart_files:
            file_score = 0
            
            # Score based on file path
            for keyword in keywords:
                if keyword in dart_file.path.lower():
                    file_score += 2
                if keyword in dart_file.name.lower():
                    file_score += 3
            
            # Score based on content
            content_lower = dart_file.content.lower()
            for keyword in keywords:
                file_score += content_lower.count(keyword)
            
            # Boost score for specific file types based on keywords
            if any(widget_kw in keywords for widget_kw in ['widget', 'ui', 'screen', 'page']):
                if dart_file.is_widget:
                    file_score += 5
            
            if any(model_kw in keywords for model_kw in ['model', 'data', 'entity']):
                if dart_file.is_model:
                    file_score += 5
            
            if any(service_kw in keywords for service_kw in ['service', 'api', 'repository']):
                if dart_file.is_service:
                    file_score += 5
            
            if file_score > 0:
                suggested_files.append((dart_file.path, file_score))
        
        # Sort by score and return top suggestions
        suggested_files.sort(key=lambda x: x[1], reverse=True)
        return [file_path for file_path, _ in suggested_files[:10]]
    
    def generate_project_summary(self) -> Dict:
        """Generate a summary of the project for LLM context"""
        structure = self.analyze()
        
        summary = {
            "name": structure.name,
            "description": structure.description,
            "total_dart_files": len(structure.dart_files),
            "architecture_pattern": structure.architecture_pattern,
            "dependencies": [
                {"name": dep.name, "version": dep.version, "is_dev": dep.is_dev}
                for dep in structure.dependencies
            ],
            "file_structure": structure.lib_structure,
            "widgets": [
                {"path": df.path, "widgets": df.widgets}
                for df in structure.dart_files if df.is_widget
            ],
            "models": [
                {"path": df.path, "classes": df.classes}
                for df in structure.dart_files if df.is_model
            ],
            "services": [
                {"path": df.path, "classes": df.classes}
                for df in structure.dart_files if df.is_service
            ]
        }
        
        return summary