"""Code cleanup and optimization utilities for AgroMap."""
import os
import ast
import re
import sys
import importlib
import subprocess
import tempfile
from typing import Set, List, Dict, Optional, Tuple, Any
import logging
from flask import Flask
import mccabe
from radon.complexity import cc_visit
from radon.metrics import mi_visit

# Set up logger
logger = logging.getLogger('code_optimizer')
handler = logging.FileHandler('logs/code_optimization.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class CodeOptimizer:
    """Code optimization and cleanup utilities."""

    def __init__(self, root_dir: str, app: Optional[Flask] = None):
        self.root_dir = root_dir
        self.app = app
        self.used_imports: Set[str] = set()
        self.unused_imports: Set[str] = set()
        self.dead_code: List[Dict] = []
        self.complexity_threshold = 10  # McCabe complexity threshold
        self.maintainability_threshold = 65  # Maintainability index threshold

        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        self.app = app

        # Register commands
        @app.cli.command("optimize-code")
        def optimize_code_command():
            """Optimize and clean up code."""
            results = self.clean_project()
            print(f"Optimized {results['files_cleaned']} files")
            print(f"Removed {results['removed_imports']} unused imports")
            print(f"Removed {results['removed_dead_code']} dead code blocks")
            if results['errors']:
                print(f"Errors in {len(results['errors'])} files")

        @app.cli.command("analyze-complexity")
        def analyze_complexity_command():
            """Analyze code complexity."""
            results = self.analyze_project_complexity()
            print(f"Analyzed {results['files_analyzed']} files")
            print(f"Found {len(results['complex_functions'])} complex functions")
            for func in results['complex_functions'][:5]:  # Show top 5
                print(f"  {func['file']}:{func['line']} - {func['name']} (Complexity: {func['complexity']})")
            if len(results['complex_functions']) > 5:
                print(f"  ... and {len(results['complex_functions']) - 5} more")

        @app.cli.command("format-code")
        def format_code_command():
            """Format code using black."""
            results = self.format_project()
            print(f"Formatted {results['files_formatted']} files")
            if results['errors']:
                print(f"Errors in {len(results['errors'])} files")

    def analyze_imports(self, file_path: str) -> Set[str]:
        """Analyze imports in a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.add(name.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for name in node.names:
                    imports.add(f"{module}.{name.name}" if module else name.name)

        return imports

    def find_used_symbols(self, file_path: str) -> Set[str]:
        """Find actually used symbols in a Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        used = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)

        return used

    def find_dead_code(self, file_path: str) -> List[Dict]:
        """Find unused functions and classes."""
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        defined = {}
        used = set()

        # First pass: collect defined functions and classes
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                defined[node.name] = {
                    'type': type(node).__name__,
                    'name': node.name,
                    'lineno': node.lineno,
                    'file': file_path
                }

        # Second pass: collect used names
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in defined:
                    used.add(node.id)

        # Return unused definitions
        return [info for name, info in defined.items() if name not in used]

    def optimize_imports(self, file_path: str) -> str:
        """Generate optimized imports for a file."""
        imports = self.analyze_imports(file_path)
        used_symbols = self.find_used_symbols(file_path)

        optimized = []
        for imp in sorted(imports):
            try:
                module = importlib.import_module(imp.split('.')[0])
                if any(symbol in used_symbols for symbol in dir(module)):
                    optimized.append(f"import {imp}")
            except ImportError:
                # Keep import if we can't verify it
                optimized.append(f"import {imp}")

        return '\n'.join(optimized)

    def scan_directory(self):
        """Scan directory for code issues."""
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)

                    # Analyze imports
                    current_imports = self.analyze_imports(file_path)
                    self.used_imports.update(current_imports)

                    # Find dead code
                    dead = self.find_dead_code(file_path)
                    if dead:
                        self.dead_code.extend(dead)

        return {
            'unused_imports': self.unused_imports,
            'dead_code': self.dead_code
        }

    def clean_file(self, file_path: str) -> bool:
        """Clean up a single file."""
        try:
            # Optimize imports
            optimized_imports = self.optimize_imports(file_path)

            # Read original file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Create backup
            backup_path = f"{file_path}.bak"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Parse and clean the code
            tree = ast.parse(content)

            # Remove unused imports and dead code
            cleaned = []
            for node in ast.walk(tree):
                if not (isinstance(node, (ast.Import, ast.ImportFrom)) or
                       isinstance(node, (ast.FunctionDef, ast.ClassDef)) and
                       node.name in [d['name'] for d in self.dead_code]):
                    cleaned.append(node)

            # Write cleaned file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(optimized_imports + '\n\n' + ast.unparse(ast.Module(body=cleaned)))

            return True

        except Exception as e:
            logger.error(f"Error cleaning file {file_path}: {str(e)}")
            return False

    def analyze_complexity(self, file_path: str) -> List[Dict]:
        """Analyze code complexity of a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            # Use radon to analyze complexity
            complexity_results = cc_visit(code)

            # Filter for complex functions
            complex_functions = []
            for func in complexity_results:
                if func.complexity > self.complexity_threshold:
                    complex_functions.append({
                        'name': func.name,
                        'complexity': func.complexity,
                        'line': func.lineno,
                        'file': file_path
                    })

            # Calculate maintainability index
            mi_result = mi_visit(code, multi=True)
            maintainability = mi_result.mi

            if maintainability < self.maintainability_threshold:
                logger.warning(f"Low maintainability index in {file_path}: {maintainability:.2f}")

            return complex_functions

        except Exception as e:
            logger.error(f"Error analyzing complexity of {file_path}: {str(e)}")
            return []

    def analyze_project_complexity(self) -> Dict:
        """Analyze complexity of the entire project."""
        results = {
            'files_analyzed': 0,
            'complex_functions': [],
            'low_maintainability_files': []
        }

        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    complex_funcs = self.analyze_complexity(file_path)
                    results['files_analyzed'] += 1
                    results['complex_functions'].extend(complex_funcs)

        # Sort by complexity
        results['complex_functions'] = sorted(
            results['complex_functions'],
            key=lambda x: x['complexity'],
            reverse=True
        )

        return results

    def format_file(self, file_path: str) -> bool:
        """Format a Python file using black."""
        try:
            # Create backup
            backup_path = f"{file_path}.bak"
            with open(file_path, 'r', encoding='utf-8') as src, open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())

            # Run black on the file
            result = subprocess.run(
                ["black", "--quiet", file_path],
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode == 0:
                logger.info(f"Formatted {file_path}")
                return True
            else:
                logger.error(f"Error formatting {file_path}: {result.stderr}")
                # Restore from backup
                with open(backup_path, 'r', encoding='utf-8') as src, open(file_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
                return False

        except Exception as e:
            logger.error(f"Error formatting {file_path}: {str(e)}")
            return False

    def format_project(self) -> Dict:
        """Format all Python files in the project using black."""
        results = {
            'files_formatted': 0,
            'errors': []
        }

        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if self.format_file(file_path):
                        results['files_formatted'] += 1
                    else:
                        results['errors'].append(file_path)

        return results

    def clean_project(self) -> Dict:
        """Clean the entire project."""
        results = {
            'files_cleaned': 0,
            'errors': [],
            'removed_imports': 0,
            'removed_dead_code': 0
        }

        # First scan to collect info
        self.scan_directory()

        # Clean each file
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    if self.clean_file(file_path):
                        results['files_cleaned'] += 1
                    else:
                        results['errors'].append(file_path)

        results['removed_imports'] = len(self.unused_imports)
        results['removed_dead_code'] = len(self.dead_code)

        return results


# Initialize code optimizer
def init_code_optimizer(app: Optional[Flask] = None, root_dir: Optional[str] = None) -> CodeOptimizer:
    """Initialize code optimizer."""
    if root_dir is None:
        # Use the app's root directory if available, otherwise current directory
        root_dir = os.path.dirname(app.root_path) if app else os.getcwd()

    optimizer = CodeOptimizer(root_dir, app)
    logger.info(f"Code optimizer initialized for {root_dir}")
    return optimizer
